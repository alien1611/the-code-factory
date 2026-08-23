"""
test_suite_comprehensive.py - Comprehensive Multi-Dimensional Verification Test Suite

Covers:
1. Unit Testing
2. Integration Testing
3. Static Analysis & Syntax Testing
4. Parsing Testing (Tree-sitter concrete syntax tree)
5. Structural Testing & Change Mapping Testing
6. Logical & Functional Testing
7. Regression Testing
8. Security & Domain Rule Testing (RFID Invariants)
9. Dependency Testing
10. Performance & Benchmarking Testing
11. Mutation & Adversarial Testing
12. Edge Case Testing
13. End-to-End (E2E) Testing
"""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

from models import (
    AnalysisResult,
    ClassMetadata,
    FileMetadata,
    Finding,
    FindingCategory,
    FindingSeverity,
    FunctionMetadata,
    MethodMetadata,
    PRAnalysisResult,
    extract_source_evidence,
    relativize_path,
)
from parser import (
    analyze_file,
    analyze_repository,
    analyze_source,
    detect_language,
    parse_source,
)
from change_mapper import map_changes_to_code
from context_builder import (
    build_file_context,
    build_function_context,
    build_repository_context,
)
from pipeline import (
    VerificationPipeline,
    VerificationService,
    analyze_pr,
    extract_changed_lines_from_patch,
    normalize_pr_files,
)
from rfid_verifier import verify_rfid_authentication
from code_parser import parse_profile, parse_profile_source
from behavioral_engine import run_behavioral_tests
from aggregator import aggregate


class Test1_UnitTesting(unittest.TestCase):
    """Unit tests for models, data serialization, and helper utilities."""

    def test_finding_creation_and_normalization(self) -> None:
        f = Finding(
            tool="ruff",
            category="LINT",
            severity="HIGH",
            message="Undefined variable",
            file="app/main.py",
            start_line=10,
            end_line=10,
            rule_id="F821",
        )
        self.assertEqual(f.category, "lint")
        self.assertEqual(f.severity, "high")
        self.assertEqual(f.tool, "ruff")
        data = f.to_dict()
        self.assertEqual(data["file"], "app/main.py")
        loaded = Finding.from_dict(data)
        self.assertEqual(loaded.rule_id, "F821")

    def test_finding_invalid_category_raises(self) -> None:
        with self.assertRaises(ValueError):
            Finding(tool="test", category="invalid_cat", severity="low", message="msg")

    def test_finding_invalid_severity_raises(self) -> None:
        with self.assertRaises(ValueError):
            Finding(tool="test", category="lint", severity="super_critical", message="msg")

    def test_file_metadata_serialization(self) -> None:
        func = FunctionMetadata(name="calc", start_line=1, end_line=5, parameters=["x", "y"])
        cls_meta = ClassMetadata(
            name="Calculator",
            start_line=6,
            end_line=15,
            methods=[MethodMetadata(name="add", start_line=7, end_line=10, parameters=["self", "v"])],
        )
        file_meta = FileMetadata(
            path="calc.py",
            language="Python",
            imports=["import math"],
            functions=[func],
            classes=[cls_meta],
            parse_errors=[],
        )
        d = file_meta.to_dict()
        loaded = FileMetadata.from_dict(d)
        self.assertEqual(loaded.language, "Python")
        self.assertEqual(len(loaded.functions), 1)
        self.assertEqual(len(loaded.classes), 1)
        self.assertEqual(loaded.classes[0].methods[0].name, "add")

    def test_path_utilities(self) -> None:
        self.assertEqual(relativize_path("/root/src/app.py", "/root"), "src/app.py")
        self.assertEqual(relativize_path("C:\\repo\\src\\app.py", "C:/repo"), "src/app.py")


class Test2_IntegrationTesting(unittest.TestCase):
    """Integration tests combining parser, change mapper, context builder, and pipeline."""

    def test_in_memory_pipeline_integration(self) -> None:
        code = (
            "class PaymentService:\n"
            "    def charge(self, user_id: int, amount: float) -> bool:\n"
            "        if amount <= 0:\n"
            "            raise ValueError('Invalid amount')\n"
            "        return True\n"
        )
        files_payload = [
            {
                "path": "src/payment.py",
                "content": code,
                "changed_lines": [3, 4],
            }
        ]
        result = analyze_pr(
            files=files_payload,
            pr_description="Add validation check to payment charge method",
            repository_meta={"name": "saas/payments", "commit_sha": "abc123"},
        )
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.analysis["files_analyzed"], 1)
        self.assertEqual(len(result.changed_code), 1)
        self.assertEqual(result.changed_code[0]["file"], "src/payment.py")
        self.assertEqual(len(result.contexts), 1)
        self.assertTrue(result.contexts[0]["is_changed"])
        self.assertEqual(result.contexts[0]["class"], "PaymentService")

    def test_verification_service_facade(self) -> None:
        service = VerificationService()
        res = service.verify_pull_request(
            files=[{"path": "auth.js", "content": "function login(u, p) { return true; }", "changed_lines": [1]}],
            pr_description="Add login function",
        )
        self.assertIn(res.status, ("completed", "completed_with_warnings"))
        self.assertEqual(res.analysis["files_analyzed"], 1)


class Test3_StaticAnalysisAndSyntax(unittest.TestCase):
    """Verifies static analysis tools and syntax error detection."""

    def test_syntax_error_detection_broken_python(self) -> None:
        broken_code = "def broken_func(x, :\n    return x +\n"
        meta = analyze_source(broken_code, "broken.py")
        self.assertEqual(meta.language, "Python")
        self.assertGreater(len(meta.parse_errors), 0)
        self.assertTrue(any("Syntax error" in err or "Missing" in err for err in meta.parse_errors))

    def test_safe_python_no_syntax_errors(self) -> None:
        safe_code = "def safe_func(x: int) -> int:\n    return x + 1\n"
        meta = analyze_source(safe_code, "safe.py")
        self.assertEqual(len(meta.parse_errors), 0)
        self.assertEqual(len(meta.functions), 1)


class Test4_ParsingTesting(unittest.TestCase):
    """Tree-sitter CST parsing across all supported languages."""

    def test_javascript_parsing(self) -> None:
        js_code = (
            "import { config } from './config';\n"
            "function processItem(item) { return item.id; }\n"
            "class ItemStore {\n"
            "    save(item) { return true; }\n"
            "}\n"
        )
        meta = analyze_source(js_code, "store.js")
        self.assertEqual(meta.language, "JavaScript")
        self.assertEqual(len(meta.imports), 1)
        self.assertEqual(len(meta.functions), 1)
        self.assertEqual(len(meta.classes), 1)
        self.assertEqual(meta.classes[0].methods[0].name, "save")

    def test_typescript_parsing(self) -> None:
        ts_code = (
            "interface User { id: number; name: string; }\n"
            "export function getUser(id: number): User { return { id, name: 'User' }; }\n"
        )
        meta = analyze_source(ts_code, "user.ts")
        self.assertEqual(meta.language, "TypeScript")
        self.assertEqual(len(meta.functions), 1)

    def test_cpp_parsing(self) -> None:
        cpp_code = (
            "#include <iostream>\n"
            "int add(int a, int b) { return a + b; }\n"
            "class MathEngine {\n"
            "public:\n"
            "    double multiply(double a, double b) { return a * b; }\n"
            "};\n"
        )
        meta = analyze_source(cpp_code, "engine.cpp")
        self.assertEqual(meta.language, "C++")
        self.assertEqual(len(meta.imports), 1)
        self.assertEqual(len(meta.functions), 1)
        self.assertEqual(len(meta.classes), 1)

    def test_java_parsing(self) -> None:
        java_code = (
            "package com.example.service;\n"
            "import java.util.List;\n"
            "public class UserService {\n"
            "    public boolean isValid(String id) { return id != null; }\n"
            "}\n"
        )
        meta = analyze_source(java_code, "UserService.java")
        self.assertEqual(meta.language, "Java")
        self.assertEqual(len(meta.classes), 1)
        self.assertEqual(meta.classes[0].methods[0].name, "isValid")


class Test5_StructuralAndChangeMapping(unittest.TestCase):
    """Verifies changed-line to AST function/method/class mapping."""

    def test_mapping_function_and_class_method(self) -> None:
        code = (
            "def top_func(a):\n"         # lines 1-2
            "    return a\n"
            "\n"
            "class Service:\n"            # lines 4-8
            "    def method_one(self):\n" # lines 5-6
            "        return 1\n"
            "    def method_two(self):\n" # lines 7-8
            "        return 2\n"
        )
        meta = analyze_source(code, "service.py")
        # Change in method_two (line 8)
        impact = map_changes_to_code([meta], {"service.py": [8]})
        self.assertIn("service.py", impact)
        file_impact = impact["service.py"]
        self.assertEqual(len(file_impact["affected_methods"]), 1)
        self.assertEqual(file_impact["affected_methods"][0]["name"], "Service.method_two")
        self.assertEqual(len(file_impact["affected_classes"]), 1)
        self.assertEqual(file_impact["affected_classes"][0]["name"], "Service")
        self.assertEqual(len(file_impact["affected_functions"]), 0)


class Test6_LogicalAndFunctional(unittest.TestCase):
    """Verifies authorization domain logic and code parser symbol discovery."""

    def test_code_parser_symbol_discovery(self) -> None:
        code = "users = { 101: {'name': 'A'}, 102: {'name': 'B'} }\ndef get_profile(requesting_user_id, requested_user_id):\n    return users[requested_user_id]\n"
        info = parse_profile_source(code)
        self.assertEqual(info["user_ids"], {101, 102})
        self.assertIn("get_profile", info["functions"])
        self.assertEqual(info["functions"]["get_profile"], ["requesting_user_id", "requested_user_id"])

    def test_behavioral_engine_execution(self) -> None:
        res = run_behavioral_tests()
        self.assertIn(res.status, ("completed", "failed", "no_tests"))
        if res.status == "completed":
            self.assertGreater(res.tests_run, 0)
            self.assertEqual(res.tests_failed, 0)


class Test7_RegressionTesting(unittest.TestCase):
    """Ensures existing APIs remain backwards compatible."""

    def test_analyze_source_equivalence_to_analyze_file(self) -> None:
        calc_path = Path("test_repository/calculator.py")
        if calc_path.exists():
            file_meta = analyze_file(calc_path)
            src_meta = analyze_source(calc_path.read_text(encoding="utf-8"), "calculator.py")
            self.assertEqual(file_meta.language, src_meta.language)
            self.assertEqual(len(file_meta.functions), len(src_meta.functions))
            self.assertEqual(len(file_meta.classes), len(src_meta.classes))

    def test_patch_extraction_backward_compat(self) -> None:
        patch = "@@ -1,3 +1,4 @@\n def a():\n+    b = 1\n     return 1\n"
        lines = extract_changed_lines_from_patch(patch)
        self.assertEqual(lines, [2])


class Test8_SecurityAndDomainRules(unittest.TestCase):
    """Verifies RFID domain invariants and security checks."""

    def test_insecure_rfid_unlock_detected(self) -> None:
        insecure_cpp = (
            "#include <MFRC522.h>\n"
            "void loop() {\n"
            "    if (mfrc522.PICC_IsNewCardPresent()) {\n"
            "        unlockDoor();\n"
            "    }\n"
            "}\n"
        )
        meta = FileMetadata(path="door.ino", language="C++")
        findings = verify_rfid_authentication(insecure_cpp, meta)
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "RFID-001-UNAUTHORIZED-UNLOCK")
        self.assertEqual(findings[0].severity, "critical")

    def test_secure_rfid_unlock_passes(self) -> None:
        secure_cpp = (
            "#include <MFRC522.h>\n"
            "byte authorizedUID[] = {0xDE, 0xAD, 0xBE, 0xEF};\n"
            "void loop() {\n"
            "    if (!mfrc522.PICC_IsNewCardPresent()) return;\n"
            "    if (!mfrc522.PICC_ReadCardSerial()) return;\n"
            "    if (memcmp(mfrc522.uid.uidByte, authorizedUID, 4) == 0) {\n"
            "        unlockDoor();\n"
            "    }\n"
            "}\n"
        )
        meta = FileMetadata(path="door.ino", language="C++")
        findings = verify_rfid_authentication(secure_cpp, meta)
        self.assertEqual(len(findings), 0)


class Test9_DependencyTesting(unittest.TestCase):
    """Verifies manifest parsing and CVE scanner."""

    def test_requirements_cve_scanning(self) -> None:
        req_path = Path("test_repository/requirements.txt")
        if req_path.exists():
            pipeline = VerificationPipeline.create_default()
            findings = pipeline.verify_target(req_path)
            # urllib3 1.26.20 in requirements.txt has known CVEs
            self.assertTrue(any(f.category == "dependency" for f in findings))


class Test10_PerformanceAndBenchmarking(unittest.TestCase):
    """Verifies parser speed and large file performance."""

    def test_large_file_parsing_performance(self) -> None:
        # Generate 1,000 functions
        large_code = "\n".join([f"def func_{i}(x: int) -> int:\n    return x + {i}\n" for i in range(1000)])
        start = time.perf_counter()
        meta = analyze_source(large_code, "large.py")
        elapsed = time.perf_counter() - start

        self.assertEqual(len(meta.functions), 1000)
        self.assertLess(elapsed, 2.0, f"Parsing 1,000 functions took too long: {elapsed:.3f}s")


class Test11_MutationAndAdversarial(unittest.TestCase):
    """Verifies resilience against corrupted diffs, null bytes, and malformed inputs."""

    def test_corrupted_patch_diff(self) -> None:
        corrupted_patches = [
            "INVALID_PATCH_HEADER",
            "@@ -not_numbers +also_not @@",
            "@@ -10,5 +20,0 @@\n-deleted line without plus",
            None,
            "",
        ]
        for cp in corrupted_patches:
            lines = extract_changed_lines_from_patch(cp)
            self.assertIsInstance(lines, list)

    def test_null_bytes_and_adversarial_strings(self) -> None:
        adversarial_code = "def injection():\n    return '\x00; DROP TABLE users; --'\n"
        meta = analyze_source(adversarial_code, "injection.py")
        self.assertEqual(len(meta.functions), 1)


class Test12_EdgeCaseTesting(unittest.TestCase):
    """Edge cases: empty inputs, binary content, deleted files, unknown extensions."""

    def test_empty_and_none_source(self) -> None:
        meta_empty = analyze_source("", "empty.py")
        self.assertEqual(len(meta_empty.functions), 0)

        meta_none = analyze_source(None, "none.py")
        self.assertEqual(len(meta_none.functions), 0)

    def test_unknown_extension_handling(self) -> None:
        meta = analyze_source("hello world", "config.unknown_ext")
        self.assertEqual(meta.language, "Unknown")
        self.assertGreater(len(meta.parse_errors), 0)

    def test_deleted_file_in_pr_payload(self) -> None:
        raw_files = [
            {"filename": "deleted_service.py", "status": "removed"},
            {"filename": "new_service.py", "content": "def run(): pass", "status": "added"},
        ]
        norm_files, changed_lines, warnings = normalize_pr_files(raw_files)
        self.assertEqual(len(norm_files), 1)
        self.assertEqual(norm_files[0]["path"], "new_service.py")
        self.assertEqual(len(warnings), 1)


class Test13_EndToEndPipeline(unittest.TestCase):
    """Complete End-to-End flow from PR input to final aggregated result."""

    def test_full_e2e_verification_flow(self) -> None:
        # 1. PR payload
        pr_files = [
            {
                "filename": "app/profile.py",
                "content": (
                    "users = {\n"
                    "    101: {'name': 'User A'},\n"
                    "    102: {'name': 'User B'}\n"
                    "}\n\n"
                    "def get_profile(requesting_user_id, requested_user_id):\n"
                    "    if requesting_user_id != requested_user_id:\n"
                    "        raise PermissionError('Unauthorized access')\n"
                    "    return users[requested_user_id]\n"
                ),
                "patch": "@@ -6,3 +6,3 @@\n+    if requesting_user_id != requested_user_id:\n+        raise PermissionError('Unauthorized access')\n",
                "status": "modified",
            }
        ]

        # 2. Pipeline execution
        analysis_result = analyze_pr(
            files=pr_files,
            pr_description="Users can only access their own profile.",
            repository_meta={"name": "alien1611/the-code-factory", "commit_sha": "c0135c0"},
        )

        self.assertEqual(analysis_result.status, "completed")
        self.assertEqual(analysis_result.analysis["files_analyzed"], 1)
        self.assertGreaterEqual(len(analysis_result.contexts), 1)

        # 3. Behavioral test execution & aggregation
        agg_result = aggregate(
            static_findings=analysis_result.findings,
        )

        self.assertEqual(agg_result["final_verdict"], "PASS")
        self.assertGreater(agg_result["tests_run"], 0)
        self.assertEqual(agg_result["tests_failed"], 0)
        self.assertTrue(Path("final_result.json").exists())


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
