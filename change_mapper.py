"""
change_mapper.py - Pull Request Code Impact Mapping Layer for AI Code Verification SaaS

Maps modified or added lines from a GitHub PR diff to the specific functions, methods,
and classes identified by parser.py (using Tree-sitter AST ranges).

Enables delta-risk scoring, targeted verification, and focused LLM prompt construction
by isolating only the exact affected AST code structures.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import sys
from typing import Any, Optional
import unittest

from models import ClassMetadata, FileMetadata, FunctionMetadata, MethodMetadata


# ==============================================================================
# 1. IMPACT DATA STRUCTURES
# ==============================================================================

@dataclass
class CodeStructureRange:
    """
    Identifies an affected function, method, or class with its exact line boundaries.

    Attributes:
        name: Name of the code entity (e.g. 'calculate_tax' or 'PaymentProcessor.process_payment').
        start_line: 1-indexed starting line number.
        end_line: 1-indexed ending line number.
    """
    name: str
    start_line: int
    end_line: int

    def to_dict(self) -> dict[str, Any]:
        """Converts to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class FileChangeImpact:
    """
    Structured impact analysis for a single modified source file.

    Attributes:
        file: Path to the target file.
        changed_lines: Sorted, deduplicated list of changed line numbers.
        affected_functions: Functions directly containing changed lines.
        affected_methods: Class methods directly containing changed lines.
        affected_classes: Classes containing changed lines (either method-level or class-level).
    """
    file: str
    changed_lines: list[int] = field(default_factory=list)
    affected_functions: list[dict[str, Any]] = field(default_factory=list)
    affected_methods: list[dict[str, Any]] = field(default_factory=list)
    affected_classes: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Converts impact result to a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileChangeImpact:
        """Constructs an instance from a dictionary."""
        return cls(
            file=data["file"],
            changed_lines=list(data.get("changed_lines", [])),
            affected_functions=list(data.get("affected_functions", [])),
            affected_methods=list(data.get("affected_methods", [])),
            affected_classes=list(data.get("affected_classes", [])),
        )


# ==============================================================================
# 2. CORE CHANGE MAPPING LOGIC
# ==============================================================================

def _normalize_path(path_str: str) -> str:
    """Normalizes file paths into standard POSIX lower-case format for cross-platform matching."""
    return Path(path_str).as_posix().lower()


def map_changes_to_code(
    file_metadata: list[FileMetadata],
    changed_lines: dict[str, list[int]],
) -> dict[str, dict[str, Any]]:
    """
    Maps modified lines from a PR diff to AST functions, methods, and classes.

    Parameters:
        file_metadata: List of FileMetadata objects extracted from repository files by parser.py.
        changed_lines: Mapping from file path to list of 1-indexed changed line numbers.
                       Example: {
                           "src/payment.py": [42, 43, 44, 45, 46],
                           "src/auth.py": [10, 11, 12]
                       }

    Returns:
        Structured dictionary matching:
        {
            "src/payment.py": {
                "file": "src/payment.py",
                "changed_lines": [42, 43, 44],
                "affected_functions": [...],
                "affected_methods": [
                    {"name": "PaymentProcessor.process_payment", "start_line": 40, "end_line": 55}
                ],
                "affected_classes": [
                    {"name": "PaymentProcessor", "start_line": 32, "end_line": 60}
                ]
            }
        }
    """
    if not changed_lines:
        return {}

    # Build lookup indices for fast and flexible path resolution
    meta_by_full_path: dict[str, FileMetadata] = {}
    meta_by_filename: dict[str, list[FileMetadata]] = {}

    for meta in file_metadata:
        norm_path = _normalize_path(meta.path)
        meta_by_full_path[norm_path] = meta
        fname = Path(meta.path).name.lower()
        meta_by_filename.setdefault(fname, []).append(meta)

    def _resolve_metadata(query_path_str: str) -> Optional[FileMetadata]:
        q_norm = _normalize_path(query_path_str)

        # 1. Exact path match
        if q_norm in meta_by_full_path:
            return meta_by_full_path[q_norm]

        # 2. Suffix / Subpath match (e.g. relative 'src/payment.py' matching 'C:/repo/src/payment.py')
        for full_p, m in meta_by_full_path.items():
            if full_p.endswith(q_norm) or q_norm.endswith(full_p):
                return m

        # 3. Base filename match (if unique in the repository)
        q_name = Path(query_path_str).name.lower()
        if q_name in meta_by_filename and len(meta_by_filename[q_name]) == 1:
            return meta_by_filename[q_name][0]

        return None

    results: dict[str, dict[str, Any]] = {}

    for file_key, raw_lines in changed_lines.items():
        # Clean, deduplicate, and sort changed line numbers
        sorted_lines = sorted(list({line for line in raw_lines if isinstance(line, int) and line >= 1}))
        meta = _resolve_metadata(file_key)

        # Handle deleted files, unparsed files, or empty diffs
        if not meta or not sorted_lines:
            results[file_key] = FileChangeImpact(
                file=file_key,
                changed_lines=sorted_lines,
                affected_functions=[],
                affected_classes=[],
                affected_methods=[],
            ).to_dict()
            continue

        affected_functions: list[dict[str, Any]] = []
        affected_classes: list[dict[str, Any]] = []
        affected_methods: list[dict[str, Any]] = []

        seen_funcs: set[str] = set()
        seen_classes: set[str] = set()
        seen_methods: set[str] = set()

        for line in sorted_lines:
            # 1. Standalone / Top-level Functions
            for func in meta.functions:
                if func.start_line <= line <= func.end_line:
                    if func.name not in seen_funcs:
                        seen_funcs.add(func.name)
                        affected_functions.append(
                            CodeStructureRange(
                                name=func.name,
                                start_line=func.start_line,
                                end_line=func.end_line,
                            ).to_dict()
                        )

            # 2. Classes and Class Methods
            for cls in meta.classes:
                if cls.start_line <= line <= cls.end_line:
                    # Associate containing class
                    if cls.name not in seen_classes:
                        seen_classes.add(cls.name)
                        affected_classes.append(
                            CodeStructureRange(
                                name=cls.name,
                                start_line=cls.start_line,
                                end_line=cls.end_line,
                            ).to_dict()
                        )

                    # Associate specific method if line falls inside a method definition
                    for method in cls.methods:
                        if method.start_line <= line <= method.end_line:
                            qual_name = f"{cls.name}.{method.name}"
                            if qual_name not in seen_methods:
                                seen_methods.add(qual_name)
                                affected_methods.append(
                                    CodeStructureRange(
                                        name=qual_name,
                                        start_line=method.start_line,
                                        end_line=method.end_line,
                                    ).to_dict()
                                )

        results[file_key] = FileChangeImpact(
            file=file_key,
            changed_lines=sorted_lines,
            affected_functions=affected_functions,
            affected_classes=affected_classes,
            affected_methods=affected_methods,
        ).to_dict()

    return results


# ==============================================================================
# 3. UNIT TESTS
# ==============================================================================

class TestChangeMapper(unittest.TestCase):
    """Unit test suite verifying all required change mapping scenarios."""

    def setUp(self) -> None:
        # Sample FileMetadata representing a parsed payment.py module
        self.func_calc_tax = FunctionMetadata(
            name="calculate_tax",
            start_line=10,
            end_line=15,
            parameters=["amount", "rate"],
        )
        self.func_validate_iban = FunctionMetadata(
            name="validate_iban",
            start_line=20,
            end_line=28,
            parameters=["iban"],
        )

        self.method_init = MethodMetadata(
            name="__init__",
            start_line=35,
            end_line=38,
            parameters=["self", "api_key"],
        )
        self.method_process = MethodMetadata(
            name="process_payment",
            start_line=40,
            end_line=55,
            parameters=["self", "account_id", "amount"],
        )

        self.class_payment_proc = ClassMetadata(
            name="PaymentProcessor",
            start_line=32,
            end_line=60,
            methods=[self.method_init, self.method_process],
        )

        self.payment_meta = FileMetadata(
            path="src/payment.py",
            language="Python",
            imports=["import math"],
            functions=[self.func_calc_tax, self.func_validate_iban],
            classes=[self.class_payment_proc],
            parse_errors=[],
        )

        # Sample FileMetadata representing an auth.py module
        self.func_login = FunctionMetadata(
            name="login_user",
            start_line=10,
            end_line=20,
            parameters=["credentials"],
        )
        self.auth_meta = FileMetadata(
            path="src/auth.py",
            language="Python",
            imports=["import jwt"],
            functions=[self.func_login],
            classes=[],
            parse_errors=[],
        )

    def test_standalone_function_change(self) -> None:
        """1. Standalone function change: maps to function and line ranges."""
        diff = {"src/payment.py": [12, 13, 14]}
        res = map_changes_to_code([self.payment_meta, self.auth_meta], diff)

        self.assertIn("src/payment.py", res)
        item = res["src/payment.py"]
        self.assertEqual(item["file"], "src/payment.py")
        self.assertEqual(item["changed_lines"], [12, 13, 14])
        self.assertEqual(len(item["affected_functions"]), 1)
        self.assertEqual(item["affected_functions"][0]["name"], "calculate_tax")
        self.assertEqual(item["affected_functions"][0]["start_line"], 10)
        self.assertEqual(item["affected_functions"][0]["end_line"], 15)
        self.assertEqual(item["affected_methods"], [])
        self.assertEqual(item["affected_classes"], [])

    def test_class_method_change(self) -> None:
        """2. Class method change: maps to method, parent class, and containing file with ranges."""
        diff = {"src/payment.py": [42, 43, 44, 45, 46]}
        res = map_changes_to_code([self.payment_meta, self.auth_meta], diff)

        self.assertIn("src/payment.py", res)
        item = res["src/payment.py"]
        self.assertEqual(item["file"], "src/payment.py")
        self.assertEqual(item["changed_lines"], [42, 43, 44, 45, 46])

        # Parent class mapping
        self.assertEqual(len(item["affected_classes"]), 1)
        self.assertEqual(item["affected_classes"][0]["name"], "PaymentProcessor")
        self.assertEqual(item["affected_classes"][0]["start_line"], 32)
        self.assertEqual(item["affected_classes"][0]["end_line"], 60)

        # Method mapping
        self.assertEqual(len(item["affected_methods"]), 1)
        self.assertEqual(item["affected_methods"][0]["name"], "PaymentProcessor.process_payment")
        self.assertEqual(item["affected_methods"][0]["start_line"], 40)
        self.assertEqual(item["affected_methods"][0]["end_line"], 55)
        self.assertEqual(item["affected_functions"], [])

    def test_multiple_functions_changed(self) -> None:
        """3. Multiple functions changed in a single file."""
        diff = {"src/payment.py": [11, 22, 25]}
        res = map_changes_to_code([self.payment_meta, self.auth_meta], diff)

        item = res["src/payment.py"]
        self.assertEqual(len(item["affected_functions"]), 2)
        names = [f["name"] for f in item["affected_functions"]]
        self.assertEqual(names, ["calculate_tax", "validate_iban"])
        self.assertEqual(item["affected_classes"], [])
        self.assertEqual(item["affected_methods"], [])

    def test_class_level_change(self) -> None:
        """4. Class-level change (e.g. class attribute/docstring) outside methods."""
        diff = {"src/payment.py": [33]}
        res = map_changes_to_code([self.payment_meta, self.auth_meta], diff)

        item = res["src/payment.py"]
        self.assertEqual(len(item["affected_classes"]), 1)
        self.assertEqual(item["affected_classes"][0]["name"], "PaymentProcessor")
        self.assertEqual(item["affected_methods"], [])
        self.assertEqual(item["affected_functions"], [])

    def test_unknown_unmapped_lines(self) -> None:
        """5. Unknown / unmapped lines (e.g. top-of-file imports or comments at line 1-3)."""
        diff = {"src/payment.py": [1, 2, 3]}
        res = map_changes_to_code([self.payment_meta, self.auth_meta], diff)

        item = res["src/payment.py"]
        self.assertEqual(item["changed_lines"], [1, 2, 3])
        self.assertEqual(item["affected_functions"], [])
        self.assertEqual(item["affected_classes"], [])
        self.assertEqual(item["affected_methods"], [])

    def test_multiple_files(self) -> None:
        """6. Multiple files changed in the same PR diff."""
        diff = {
            "src/payment.py": [42, 43, 44, 45, 46],
            "src/auth.py": [10, 11, 12],
        }
        res = map_changes_to_code([self.payment_meta, self.auth_meta], diff)

        self.assertIn("src/payment.py", res)
        self.assertIn("src/auth.py", res)
        self.assertEqual(len(res["src/payment.py"]["affected_methods"]), 1)
        self.assertEqual(len(res["src/auth.py"]["affected_functions"]), 1)
        self.assertEqual(res["src/auth.py"]["affected_functions"][0]["name"], "login_user")


# ==============================================================================
# 4. CLI DEMONSTRATION RUNNER
# ==============================================================================

if __name__ == "__main__":
    parser_cli = argparse.ArgumentParser(
        description="Map GitHub PR changed lines to functions, methods, and classes."
    )
    parser_cli.add_argument(
        "--test",
        action="store_true",
        help="Execute the unit test suite",
    )
    parser_cli.add_argument(
        "--diff-json",
        type=str,
        help="JSON string of changed lines (e.g. '{\"src/payment.py\": [42, 43]}')",
    )

    args = parser_cli.parse_args()

    if args.test or (len(sys.argv) == 1 and not args.diff_json):
        print("[+] Executing ChangeMapper test suite...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestChangeMapper)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)

        print("\n" + "=" * 50)
        print("[+] PR Impact Mapping Demonstration:")
        print("=" * 50)

        try:
            from parser import analyze_repository

            repo_meta = analyze_repository("./test_repository")
            sample_pr_changes = {
                "calculator.py": [4, 5, 11],
                "service.js": [4, 15, 19],
                "PaymentProcessor.java": [13, 14],
                "broken_syntax.py": [1],
                "deleted_module.py": [100, 101],
            }

            impact_map = map_changes_to_code(repo_meta, sample_pr_changes)
            print(json.dumps(impact_map, indent=2))
        except Exception as e:
            print(f"Demo notice: {e}")

    elif args.diff_json:
        try:
            from parser import analyze_repository

            repo_meta = analyze_repository("./")
            changes_dict = json.loads(args.diff_json)
            result = map_changes_to_code(repo_meta, changes_dict)
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error processing diff JSON: {e}", file=sys.stderr)
            sys.exit(1)
