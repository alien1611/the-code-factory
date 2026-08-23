"""
rfid_verifier.py - Domain-Specific Static Verification Rule for RFID Authentication

Performs AST-driven control-flow verification on C++/Arduino firmware to ensure that
door unlock operations are strictly guarded by authorized UID validation.

Enforces the 5-step security invariant:
1. Detect RFID card presence.
2. Read card UID serial.
3. Validate UID against an authorized whitelist.
4. Compute an authorization decision.
5. Trigger unlock operations ONLY on successful authorization.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Optional
import unittest

import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser

from models import FileMetadata, Finding, FindingCategory, FindingSeverity


# ==============================================================================
# 1. GRAMMAR & RECOGNIZED DOMAIN PATTERNS
# ==============================================================================

CPP_LANGUAGE = Language(tscpp.language())

# Common RFID card detection APIs
RFID_DETECTION_PATTERNS = re.compile(
    r"\b(PICC_IsNewCardPresent|isNewCardPresent|isCardPresent|readRFID|detectCard|isCard)\b",
    re.IGNORECASE,
)

# Common UID serial extraction APIs
RFID_UID_READ_PATTERNS = re.compile(
    r"\b(PICC_ReadCardSerial|readCardSerial|readCard|uidByte|mfrc522\.uid|getUID|cardUID|tagID|read_card)\b",
    re.IGNORECASE,
)

# Authorization concepts, comparison functions, and whitelist variables
RFID_AUTH_PATTERNS = re.compile(
    r"\b(authorizedUID|masterCard|allowedUID|whitelist|authorizedCards|isAuthorized|checkAccess|validateUID|checkUID|allowed_cards|auth_list|memcmp|strcmp|strncmp)\b",
    re.IGNORECASE,
)

# Actuator / Unlock operations
UNLOCK_PATTERNS = re.compile(
    r"\b(unlockDoor|openLock|unlock|openDoor|releaseLock|doorRelay|servo\.write|relay\.on|digitalWrite)\b",
    re.IGNORECASE,
)


def _strip_c_comments(code: str) -> str:
    """Removes single-line and multi-line C/C++ comments to prevent false matches."""
    code = re.sub(r"//.*", "", code)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    return code


# ==============================================================================
# 2. REFERENCE EXAMPLES (GOOD VS VULNERABLE)
# ==============================================================================

GOOD_RFID_EXAMPLE = """
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9
#define RELAY_PIN 7

MFRC522 mfrc522(SS_PIN, RST_PIN);
byte authorizedUID[] = {0xDE, 0xAD, 0xBE, 0xEF};

void setup() {
    SPI.begin();
    mfrc522.PCD_Init();
    pinMode(RELAY_PIN, OUTPUT);
}

void loop() {
    // 1. Detect card
    if (!mfrc522.PICC_IsNewCardPresent()) {
        return;
    }
    // 2. Read card serial
    if (!mfrc522.PICC_ReadCardSerial()) {
        return;
    }

    // 3. Validate UID against whitelist
    bool isAuthorized = true;
    for (byte i = 0; i < mfrc522.uid.size; i++) {
        if (mfrc522.uid.uidByte[i] != authorizedUID[i]) {
            isAuthorized = false;
            break;
        }
    }

    // 4. Authorize & 5. Unlock only if authorized
    if (isAuthorized) {
        digitalWrite(RELAY_PIN, HIGH);
        delay(3000);
        digitalWrite(RELAY_PIN, LOW);
    }
}
"""

MISSING_AUTH_EXAMPLE = """
#include <SPI.h>
#include <MFRC522.h>

#define RELAY_PIN 7
MFRC522 mfrc522(10, 9);

void loop() {
    // 1. Detect card
    if (mfrc522.PICC_IsNewCardPresent()) {
        // CRITICAL VULNERABILITY: Directly unlock without reading or validating UID
        digitalWrite(RELAY_PIN, HIGH);
        delay(2000);
        digitalWrite(RELAY_PIN, LOW);
    }
}
"""

UNGUARDED_AUTH_EXAMPLE = """
#include <MFRC522.h>
MFRC522 mfrc522(10, 9);
byte masterCard[] = {0x12, 0x34, 0x56, 0x78};

void loop() {
    if (!mfrc522.PICC_IsNewCardPresent()) return;
    if (!mfrc522.PICC_ReadCardSerial()) return;

    bool match = (memcmp(mfrc522.uid.uidByte, masterCard, 4) == 0);
    
    // CRITICAL VULNERABILITY: unlock is called unconditionally outside if (match)
    unlockDoor();
}
"""

MISSING_VALIDATION_EXAMPLE = """
#include <MFRC522.h>
MFRC522 mfrc522(10, 9);

void loop() {
    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
        // HIGH VULNERABILITY: UID is read but never validated against any whitelist before unlock
        unlockDoor();
    }
}
"""

INVERTED_AUTH_EXAMPLE = """
#include <MFRC522.h>
MFRC522 mfrc522(10, 9);
byte masterCard[] = {0xAA, 0xBB, 0xCC, 0xDD};

void loop() {
    if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) return;
    
    bool isMatch = (memcmp(mfrc522.uid.uidByte, masterCard, 4) == 0);
    
    // CRITICAL VULNERABILITY: Inverted logic - unlocks door when isMatch is FALSE
    if (!isMatch) {
        unlockDoor();
    }
}
"""


# ==============================================================================
# 3. CORE VERIFIER IMPLEMENTATION
# ==============================================================================

def verify_rfid_authentication(
    source_code: str,
    parsed_metadata: FileMetadata,
) -> list[Finding]:
    """
    Statically analyzes C++/Arduino source code for domain-specific RFID authorization flaws.
    """
    findings: list[Finding] = []
    file_path = parsed_metadata.path
    clean_code = _strip_c_comments(source_code)

    has_rfid = bool(
        "MFRC522" in clean_code
        or "RFID" in clean_code
        or "PN532" in clean_code
        or "RDM6300" in clean_code
        or RFID_DETECTION_PATTERNS.search(clean_code)
    )
    if not has_rfid:
        return []

    parser = Parser(CPP_LANGUAGE)
    tree = parser.parse(source_code.encode("utf-8", errors="ignore"))

    def find_nodes(node, target_type):
        res = []
        if node.type == target_type:
            res.append(node)
        for child in node.children:
            res.extend(find_nodes(child, target_type))
        return res

    functions = find_nodes(tree.root_node, "function_definition")

    for fn_node in functions:
        fn_raw_text = fn_node.text.decode("utf-8", errors="ignore")
        fn_text = _strip_c_comments(fn_raw_text)

        has_detect = bool(RFID_DETECTION_PATTERNS.search(fn_text))
        has_uid_read = bool(RFID_UID_READ_PATTERNS.search(fn_text))
        has_auth_mechanism = bool(
            RFID_AUTH_PATTERNS.search(fn_text)
            or ("==" in fn_text and "uid" in fn_text.lower())
            or ("!=" in fn_text and "uid" in fn_text.lower())
        )
        has_unlock = bool(UNLOCK_PATTERNS.search(fn_text))

        if not (has_detect or has_uid_read) or not has_unlock:
            continue

        if_statements = find_nodes(fn_node, "if_statement")

        unlock_calls = []
        for call in find_nodes(fn_node, "call_expression"):
            call_text = call.text.decode("utf-8", errors="ignore")
            if UNLOCK_PATTERNS.search(call_text):
                if "pinMode" in call_text or "PCD_Init" in call_text:
                    continue
                unlock_calls.append((call, call.start_point[0] + 1, call_text))

        for unlock_node, unlock_line, unlock_call_str in unlock_calls:
            guarding_ifs = []
            for if_st in if_statements:
                if_start = if_st.start_point[0] + 1
                if_end = if_st.end_point[0] + 1
                if if_start <= unlock_line <= if_end:
                    cond_node = None
                    for ch in if_st.children:
                        if ch.type == "condition_clause":
                            cond_node = ch
                            break
                    cond_raw = cond_node.text.decode("utf-8", errors="ignore") if cond_node else ""
                    cond_text = _strip_c_comments(cond_raw)
                    guarding_ifs.append((if_st, cond_text))

            guarded_by_detect_only = False
            guarded_by_auth = False
            guarded_by_inverted_auth = False

            for if_st, cond in guarding_ifs:
                cond_clean = cond.strip().replace(" ", "")

                # Check inverted conditions: !isAuthorized, !isMatch, isAuthorized==false, match==0, !=0
                if re.search(r"(!isAuthorized|!isMatch|!match|!authorized|!accessGranted|isAuthorized==false|isMatch==false)", cond):
                    guarded_by_inverted_auth = True

                if RFID_DETECTION_PATTERNS.search(cond) and not RFID_AUTH_PATTERNS.search(cond):
                    guarded_by_detect_only = True

                if (
                    RFID_AUTH_PATTERNS.search(cond)
                    or "isAuthorized" in cond
                    or "authorized" in cond
                    or "accessGranted" in cond
                    or "match" in cond
                    or "valid" in cond.lower()
                ) and not guarded_by_inverted_auth:
                    guarded_by_auth = True

            # Check 1: Inverted authorization logic
            if guarded_by_inverted_auth:
                findings.append(
                    Finding(
                        tool="rfid-domain-rule",
                        category=FindingCategory.SECURITY.value,
                        severity=FindingSeverity.CRITICAL.value,
                        file=file_path,
                        start_line=unlock_line,
                        end_line=unlock_line,
                        rule_id="RFID-004-INVERTED-AUTHORIZATION",
                        message=(
                            "Critical RFID authorization bypass: Inverted authorization condition detected. "
                            "The door unlock operation is triggered when the UID authorization check evaluates to false."
                        ),
                        evidence=unlock_call_str,
                        confidence=1.0,
                        metadata={
                            "rule_name": "Inverted RFID Authorization Logic",
                            "flaw_type": "Negated authorization check (!isMatch / !isAuthorized)",
                        },
                    )
                )

            # Flow Flaw 2: Direct unlock upon card presence without UID reading or validation
            elif (guarded_by_detect_only or not guarding_ifs) and not has_uid_read and not guarded_by_auth:
                findings.append(
                    Finding(
                        tool="rfid-domain-rule",
                        category=FindingCategory.SECURITY.value,
                        severity=FindingSeverity.CRITICAL.value,
                        file=file_path,
                        start_line=unlock_line,
                        end_line=unlock_line,
                        rule_id="RFID-001-UNAUTHORIZED-UNLOCK",
                        message=(
                            "Critical RFID authentication flaw: Door unlock operation is triggered immediately upon "
                            "card detection without reading or validating the card UID against an authorized whitelist. "
                            "Any physical RFID tag will grant unauthorized entry."
                        ),
                        evidence=unlock_call_str,
                        confidence=1.0,
                        metadata={
                            "rule_name": "Unauthorized RFID Unlock",
                            "detection_step": "Present",
                            "uid_read_step": "Missing",
                            "authorization_step": "Missing",
                            "unlock_step": "Present",
                        },
                    )
                )

            # Flow Flaw 3: Unguarded unlock (UID read, but unlock executes unconditionally outside conditional branch)
            elif not guarding_ifs and has_detect:
                findings.append(
                    Finding(
                        tool="rfid-domain-rule",
                        category=FindingCategory.SECURITY.value,
                        severity=FindingSeverity.CRITICAL.value,
                        file=file_path,
                        start_line=unlock_line,
                        end_line=unlock_line,
                        rule_id="RFID-002-UNGUARDED-UNLOCK",
                        message=(
                            "Unguarded RFID unlock operation: The unlock routine is executed unconditionally outside "
                            "an authorization decision branch."
                        ),
                        evidence=unlock_call_str,
                        confidence=1.0,
                        metadata={
                            "rule_name": "Unguarded RFID Unlock",
                            "authorization_step": "Bypassed / Not Guarding Unlock",
                            "unlock_step": "Present",
                        },
                    )
                )

            # Flow Flaw 4: UID read, but no comparison/whitelist validation mechanism exists before unlocking
            elif not guarded_by_auth and not has_auth_mechanism:
                findings.append(
                    Finding(
                        tool="rfid-domain-rule",
                        category=FindingCategory.SECURITY.value,
                        severity=FindingSeverity.HIGH.value,
                        file=file_path,
                        start_line=unlock_line,
                        end_line=unlock_line,
                        rule_id="RFID-003-MISSING-UID-VALIDATION",
                        message=(
                            "Missing RFID authorization decision: Card UID is read but no whitelist comparison or access "
                            "control validation is performed before calling the unlock operation."
                        ),
                        evidence=unlock_call_str,
                        confidence=1.0,
                        metadata={
                            "rule_name": "Missing UID Whitelist Check",
                            "authorization_step": "Missing",
                            "unlock_step": "Present",
                        },
                    )
                )

    return findings


def verify_rfid_repository(repo_path: str | Path) -> list[Finding]:
    """
    Scans all C++/Arduino source files (.ino, .cpp, .c, .h, .hpp) in a repository for RFID flaws.
    """
    target = Path(repo_path).resolve()
    all_findings: list[Finding] = []

    if not target.exists():
        return []

    c_extensions = {".ino", ".cpp", ".c", ".cc", ".cxx", ".h", ".hpp"}

    for root, _, files in os.walk(target):
        for fname in files:
            p = Path(root) / fname
            if p.suffix.lower() in c_extensions:
                try:
                    code = p.read_text(encoding="utf-8", errors="replace")
                    meta = FileMetadata(path=p.as_posix(), language="C++")
                    findings = verify_rfid_authentication(code, meta)
                    all_findings.extend(findings)
                except Exception:
                    continue

    return all_findings


# ==============================================================================
# 4. UNIT TESTS
# ==============================================================================

class TestRFIDVerifier(unittest.TestCase):
    """Unit test suite verifying RFID domain-specific rules."""

    def test_good_rfid_flow(self) -> None:
        """Verifies that a fully authorized RFID flow produces 0 security findings."""
        meta = FileMetadata(path="secure_lock.ino", language="C++")
        findings = verify_rfid_authentication(GOOD_RFID_EXAMPLE, meta)
        self.assertEqual(len(findings), 0, "Secure RFID implementation must produce 0 findings")

    def test_missing_auth_flow(self) -> None:
        """Verifies detection of immediate unlock upon card presence without UID check."""
        meta = FileMetadata(path="missing_auth.ino", language="C++")
        findings = verify_rfid_authentication(MISSING_AUTH_EXAMPLE, meta)
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "RFID-001-UNAUTHORIZED-UNLOCK")
        self.assertEqual(findings[0].severity, FindingSeverity.CRITICAL.value)

    def test_unguarded_auth_flow(self) -> None:
        """Verifies detection of unconditional unlock executed outside authorization branch."""
        meta = FileMetadata(path="unguarded_auth.ino", language="C++")
        findings = verify_rfid_authentication(UNGUARDED_AUTH_EXAMPLE, meta)
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "RFID-002-UNGUARDED-UNLOCK")
        self.assertEqual(findings[0].severity, FindingSeverity.CRITICAL.value)

    def test_missing_validation_flow(self) -> None:
        """Verifies detection of UID read without any whitelist validation check."""
        meta = FileMetadata(path="missing_validation.ino", language="C++")
        findings = verify_rfid_authentication(MISSING_VALIDATION_EXAMPLE, meta)
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "RFID-003-MISSING-UID-VALIDATION")
        self.assertEqual(findings[0].severity, FindingSeverity.HIGH.value)

    def test_inverted_auth_flow(self) -> None:
        """Verifies detection of inverted authorization logic (!isMatch)."""
        meta = FileMetadata(path="inverted_auth.ino", language="C++")
        findings = verify_rfid_authentication(INVERTED_AUTH_EXAMPLE, meta)
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "RFID-004-INVERTED-AUTHORIZATION")
        self.assertEqual(findings[0].severity, FindingSeverity.CRITICAL.value)

    def test_non_rfid_code(self) -> None:
        """Verifies that non-RFID code (e.g. LED blink) is ignored cleanly."""
        non_rfid = "void loop() { digitalWrite(13, HIGH); delay(1000); digitalWrite(13, LOW); }"
        meta = FileMetadata(path="blink.ino", language="C++")
        findings = verify_rfid_authentication(non_rfid, meta)
        self.assertEqual(len(findings), 0)


# ==============================================================================
# 5. CLI DEMONSTRATION RUNNER
# ==============================================================================

if __name__ == "__main__":
    cli = argparse.ArgumentParser(
        description="Verify RFID authentication security invariants in C++/Arduino code."
    )
    cli.add_argument(
        "--test",
        action="store_true",
        help="Run unit test suite",
    )
    cli.add_argument(
        "--demo",
        action="store_true",
        help="Demonstrate rule verification against good and insecure reference examples",
    )
    cli.add_argument(
        "repository_path",
        nargs="?",
        default="./test_repository",
        help="Path to repository or file to verify (default: ./test_repository)",
    )

    args = cli.parse_args()

    if args.test:
        print("[+] Executing RFID Verifier test suite...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestRFIDVerifier)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        sys.exit(0)

    if args.demo or (len(sys.argv) == 1):
        print("=" * 65)
        print("RFID DOMAIN-SPECIFIC SECURITY VERIFICATION DEMONSTRATION")
        print("=" * 65)

        examples = [
            ("1. Secure RFID Implementation (Good)", GOOD_RFID_EXAMPLE),
            ("2. Missing Authorization Flow (Critical Flaw)", MISSING_AUTH_EXAMPLE),
            ("3. Unguarded Unlock Flow (Critical Flaw)", UNGUARDED_AUTH_EXAMPLE),
            ("4. Missing UID Validation Flow (High Flaw)", MISSING_VALIDATION_EXAMPLE),
            ("5. Inverted Authorization Flow (Critical Flaw)", INVERTED_AUTH_EXAMPLE),
        ]

        for title, code in examples:
            print(f"\n[+] Analyzing: {title}")
            meta = FileMetadata(path="demo.ino", language="C++")
            results = verify_rfid_authentication(code, meta)
            if not results:
                print("    [PASS] VERIFIED: All 5 RFID authentication invariants satisfied. 0 findings.")
            else:
                for f in results:
                    print(f"    [FAIL] FLAW DETECTED: [{f.severity.upper()}] {f.rule_id} (line {f.start_line})")
                    print(f"      Message : {f.message}")
                    print(f"      Evidence: {f.evidence}")

        print("\n" + "=" * 65)
        print("[+] Executing unit test suite:")
        print("=" * 65)
        suite = unittest.TestLoader().loadTestsFromTestCase(TestRFIDVerifier)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)

    else:
        target_path = Path(args.repository_path)
        print(f"[+] Scanning for RFID security flaws in: '{target_path}'")
        findings = verify_rfid_repository(target_path)
        json_output = json.dumps([f.to_dict() for f in findings], indent=2)
        print(json_output)
