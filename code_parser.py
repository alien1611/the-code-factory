"""
code_parser.py

Wrapper around the shared Tree-sitter based `parser.py` module.
Extracts, for the AI Code Verifier prototype:

  - valid user IDs (from the `users = { ... }` dict literal)
  - valid function names + parameter names

Keeps the same public interface as before (parse_profile -> dict with
"user_ids" and "functions") so test_generator.py does not need to change.
"""

from pathlib import Path

import parser as cst_parser  # friend's Tree-sitter based parser.py


def _extract_user_ids_from_tree(root_node) -> set[int]:
    """
    Walk the Tree-sitter CST looking for a top-level assignment:

        users = {
            101: {...},
            102: {...}
        }

    and collect the dict keys as integers.
    """

    user_ids: set[int] = set()

    def walk(node):
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")

            if (
                left is not None
                and cst_parser.get_node_text(left) == "users"
                and right is not None
                and right.type == "dictionary"
            ):
                for child in right.children:
                    if child.type == "pair":
                        key_node = child.child_by_field_name("key")
                        if key_node is not None:
                            key_text = cst_parser.get_node_text(key_node)
                            if key_text.isdigit():
                                user_ids.add(int(key_text))

        for child in node.children:
            walk(child)

    walk(root_node)
    return user_ids


def parse_profile_source(source_code: str, filename: str = "profile.py") -> dict:
    """
    Parse in-memory source code using the shared Tree-sitter parser to discover:
      - valid user IDs
      - valid function names and their parameter names
    """
    tree, source_bytes, errors = cst_parser.parse_source(source_code, filename)

    if tree is None:
        raise ValueError(
            f"Failed to parse in-memory source for {filename}: {errors}"
        )

    file_metadata = cst_parser.analyze_source(source_code, filename)

    functions = {
        func.name: func.parameters
        for func in file_metadata.functions
    }

    user_ids = _extract_user_ids_from_tree(tree.root_node)

    return {
        "user_ids": user_ids,
        "functions": functions,
    }


def parse_profile(profile_path: Path | str) -> dict:
    """
    Parse app/profile.py using the shared Tree-sitter parser to discover:
      - valid user IDs
      - valid function names and their parameter names
    """
    path = Path(profile_path)
    if not path.is_file():
        raise FileNotFoundError(f"Profile file not found: {path}")

    source_code = path.read_text(encoding="utf-8", errors="replace")
    return parse_profile_source(source_code, path.name)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent
    result = parse_profile(BASE_DIR / "app" / "profile.py")
    print(result)