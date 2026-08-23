"""
parser.py - Repository Code Parser Layer for AI Code Verification SaaS

This module scans a codebase repository, identifies source files across supported
languages (Python, JavaScript, C++, Java), parses the concrete syntax tree using
Tree-sitter, and extracts normalized structured metadata (imports, functions,
classes, methods, parameters, line numbers, and syntax parse errors).

Designed to feed downstream RAG and LLM verification pipelines.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
from typing import Callable, Optional

# Tree-sitter core bindings
import tree_sitter
from tree_sitter import Language, Parser

# Language grammars (Tree-sitter 0.22+ / 0.24+ / 0.26+ compatible)
try:
    import tree_sitter_python
except ImportError:
    tree_sitter_python = None

try:
    import tree_sitter_javascript
except ImportError:
    tree_sitter_javascript = None

try:
    import tree_sitter_cpp
except ImportError:
    tree_sitter_cpp = None

try:
    import tree_sitter_java
except ImportError:
    tree_sitter_java = None

# Import common data models
try:
    from models import (
        ClassMetadata,
        FileMetadata,
        FunctionMetadata,
        MethodMetadata,
    )
except ImportError:
    # Fallback to local definitions if models.py is not in pythonpath
    from dataclasses import dataclass, field

    @dataclass
    class FunctionMetadata:
        name: str
        start_line: int
        end_line: int
        parameters: list[str] = field(default_factory=list)

    @dataclass
    class MethodMetadata:
        name: str
        start_line: int
        end_line: int
        parameters: list[str] = field(default_factory=list)

    @dataclass
    class ClassMetadata:
        name: str
        start_line: int
        end_line: int
        methods: list[MethodMetadata] = field(default_factory=list)

    @dataclass
    class FileMetadata:
        path: str
        language: str
        imports: list[str] = field(default_factory=list)
        functions: list[FunctionMetadata] = field(default_factory=list)
        classes: list[ClassMetadata] = field(default_factory=list)
        parse_errors: list[str] = field(default_factory=list)

        def to_dict(self) -> dict:
            return asdict(self)


# ==============================================================================
# 1. FILE SCANNING & IGNORE CONFIGURATION
# ==============================================================================

DEFAULT_IGNORE_DIRS: set[str] = {
    ".git",
    ".github",
    ".gitlab",
    ".svn",
    ".hg",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    "out",
    "target",
    "bin",
    "obj",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    "coverage",
    ".turbo",
}

DEFAULT_IGNORE_EXTENSIONS: set[str] = {
    # Binaries & Compiled
    ".exe", ".dll", ".so", ".dylib", ".o", ".obj", ".bin", ".class",
    ".pyc", ".pyo", ".pyd", ".whl", ".jar", ".war", ".aar",
    # Images & Icons
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp", ".tiff", ".psd",
    # Videos & Audio
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a",
    # Documents & Data
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".sqlite", ".sqlite3", ".db", ".mdb", ".parquet", ".csv",
    # Archives
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz", ".tgz",
    # Fonts
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    # Minified / Lockfiles
    ".min.js", ".min.css", ".lock",
}


# ==============================================================================
# 2. TREE-SITTER HELPER UTILITIES
# ==============================================================================

def get_node_text(node: tree_sitter.Node) -> str:
    """Extracts and decodes UTF-8 text represented by an AST node."""
    if not node or not node.text:
        return ""
    return node.text.decode("utf-8", errors="replace").strip()


def extract_parse_errors(root_node: tree_sitter.Node) -> list[str]:
    """Traverses the syntax tree to collect syntax errors and missing tokens."""
    errors: list[str] = []

    def traverse(node: tree_sitter.Node) -> None:
        if node.is_error or node.type == "ERROR":
            err_snippet = get_node_text(node).replace("\n", " ")
            if len(err_snippet) > 40:
                err_snippet = err_snippet[:37] + "..."
            line_no = node.start_point[0] + 1
            col_no = node.start_point[1]
            errors.append(f"Syntax error at line {line_no}:{col_no}: '{err_snippet}'")
        elif node.is_missing:
            line_no = node.start_point[0] + 1
            col_no = node.start_point[1]
            errors.append(f"Missing token expected at line {line_no}:{col_no}")

        for child in node.children:
            traverse(child)

    traverse(root_node)
    return errors


# ==============================================================================
# 3. LANGUAGE-SPECIFIC AST EXTRACTORS
# ==============================================================================

# ------------------------------------------------------------------------------
# Python Extractor
# ------------------------------------------------------------------------------
def extract_python(
    root_node: tree_sitter.Node,
) -> tuple[list[str], list[FunctionMetadata], list[ClassMetadata]]:
    """Extracts imports, functions, and classes from a Python AST."""
    imports: list[str] = []
    functions: list[FunctionMetadata] = []
    classes: list[ClassMetadata] = []

    def parse_python_params(params_node: Optional[tree_sitter.Node]) -> list[str]:
        if not params_node:
            return []
        params = []
        for child in params_node.children:
            if child.type in (
                "identifier",
                "typed_parameter",
                "default_parameter",
                "typed_default_parameter",
                "list_splat_pattern",
                "dictionary_splat_pattern",
            ):
                params.append(get_node_text(child))
        return params

    def parse_python_func(func_node: tree_sitter.Node) -> FunctionMetadata:
        name_node = func_node.child_by_field_name("name")
        func_name = get_node_text(name_node) if name_node else "<anonymous>"
        params_node = func_node.child_by_field_name("parameters")
        return FunctionMetadata(
            name=func_name,
            start_line=func_node.start_point[0] + 1,
            end_line=func_node.end_point[0] + 1,
            parameters=parse_python_params(params_node),
        )

    def parse_python_method(func_node: tree_sitter.Node) -> MethodMetadata:
        name_node = func_node.child_by_field_name("name")
        func_name = get_node_text(name_node) if name_node else "<anonymous>"
        params_node = func_node.child_by_field_name("parameters")
        return MethodMetadata(
            name=func_name,
            start_line=func_node.start_point[0] + 1,
            end_line=func_node.end_point[0] + 1,
            parameters=parse_python_params(params_node),
        )

    def parse_python_class(class_node: tree_sitter.Node) -> ClassMetadata:
        name_node = class_node.child_by_field_name("name")
        class_name = get_node_text(name_node) if name_node else "<anonymous>"
        body_node = class_node.child_by_field_name("body")
        methods: list[MethodMetadata] = []

        if body_node:
            for child in body_node.children:
                if child.type == "function_definition":
                    methods.append(parse_python_method(child))
                elif child.type == "decorated_definition":
                    for sub in child.children:
                        if sub.type == "function_definition":
                            methods.append(parse_python_method(sub))

        return ClassMetadata(
            name=class_name,
            start_line=class_node.start_point[0] + 1,
            end_line=class_node.end_point[0] + 1,
            methods=methods,
        )

    for child in root_node.children:
        if child.type in ("import_statement", "import_from_statement"):
            imports.append(get_node_text(child))
        elif child.type == "function_definition":
            functions.append(parse_python_func(child))
        elif child.type == "class_definition":
            classes.append(parse_python_class(child))
        elif child.type == "decorated_definition":
            for sub in child.children:
                if sub.type == "function_definition":
                    functions.append(parse_python_func(sub))
                elif sub.type == "class_definition":
                    classes.append(parse_python_class(sub))

    return imports, functions, classes


# ------------------------------------------------------------------------------
# JavaScript Extractor
# ------------------------------------------------------------------------------
def extract_javascript(
    root_node: tree_sitter.Node,
) -> tuple[list[str], list[FunctionMetadata], list[ClassMetadata]]:
    """Extracts imports, functions, and classes from a JavaScript AST."""
    imports: list[str] = []
    functions: list[FunctionMetadata] = []
    classes: list[ClassMetadata] = []

    def parse_js_params(params_node: Optional[tree_sitter.Node]) -> list[str]:
        if not params_node:
            return []
        params = []
        for child in params_node.children:
            if child.type in (
                "identifier",
                "assignment_pattern",
                "rest_pattern",
                "object_pattern",
                "array_pattern",
                "formal_parameter",
            ):
                params.append(get_node_text(child))
        return params

    def parse_js_func_node(
        node: tree_sitter.Node, default_name: str = ""
    ) -> FunctionMetadata:
        name_node = node.child_by_field_name("name")
        func_name = get_node_text(name_node) if name_node else default_name or "<anonymous>"
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            for child in node.children:
                if child.type == "formal_parameters":
                    params_node = child
                    break
        return FunctionMetadata(
            name=func_name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parse_js_params(params_node),
        )

    def parse_js_class(class_node: tree_sitter.Node) -> ClassMetadata:
        name_node = class_node.child_by_field_name("name")
        class_name = get_node_text(name_node) if name_node else "<anonymous>"
        body_node = class_node.child_by_field_name("body")
        methods: list[MethodMetadata] = []

        if body_node:
            for child in body_node.children:
                if child.type == "method_definition":
                    name_n = child.child_by_field_name("name")
                    m_name = get_node_text(name_n) if name_n else "<method>"
                    params_n = child.child_by_field_name("parameters")
                    methods.append(
                        MethodMetadata(
                            name=m_name,
                            start_line=child.start_point[0] + 1,
                            end_line=child.end_point[0] + 1,
                            parameters=parse_js_params(params_n),
                        )
                    )
                elif child.type == "field_definition":
                    val_node = child.child_by_field_name("value")
                    prop_name = child.child_by_field_name("property")
                    if val_node and val_node.type in ("arrow_function", "function_expression"):
                        prop_str = get_node_text(prop_name) if prop_name else ""
                        fn = parse_js_func_node(val_node, default_name=prop_str)
                        methods.append(
                            MethodMetadata(
                                name=fn.name,
                                start_line=fn.start_line,
                                end_line=fn.end_line,
                                parameters=fn.parameters,
                            )
                        )

        return ClassMetadata(
            name=class_name,
            start_line=class_node.start_point[0] + 1,
            end_line=class_node.end_point[0] + 1,
            methods=methods,
        )

    def visit(node: tree_sitter.Node) -> None:
        if node.type == "import_statement":
            imports.append(get_node_text(node))
            return
        elif node.type == "export_statement":
            decl = node.child_by_field_name("declaration")
            if decl:
                visit(decl)
                return
            node_str = get_node_text(node)
            if "from" in node_str:
                imports.append(node_str)
            return
        elif node.type in ("function_declaration", "generator_function_declaration"):
            functions.append(parse_js_func_node(node))
            return
        elif node.type in ("class_declaration", "class"):
            classes.append(parse_js_class(node))
            return
        elif node.type in ("lexical_declaration", "variable_declaration"):
            node_str = get_node_text(node)
            if "require(" in node_str:
                imports.append(node_str)
            for decl in node.children:
                if decl.type == "variable_declarator":
                    name_n = decl.child_by_field_name("name")
                    val_n = decl.child_by_field_name("value")
                    if val_n and val_n.type in ("arrow_function", "function_expression"):
                        var_name = get_node_text(name_n) if name_n else ""
                        functions.append(parse_js_func_node(val_n, default_name=var_name))
                    elif val_n and val_n.type == "class":
                        classes.append(parse_js_class(val_n))
            return

        for child in node.children:
            visit(child)

    for child in root_node.children:
        visit(child)

    return imports, functions, classes


# ------------------------------------------------------------------------------
# C++ Extractor
# ------------------------------------------------------------------------------
def extract_cpp(
    root_node: tree_sitter.Node,
) -> tuple[list[str], list[FunctionMetadata], list[ClassMetadata]]:
    """Extracts includes, functions, classes, and structs from a C++ AST."""
    imports: list[str] = []
    functions: list[FunctionMetadata] = []
    classes: list[ClassMetadata] = []

    def get_function_declarator(node: tree_sitter.Node) -> Optional[tree_sitter.Node]:
        if node.type == "function_declarator":
            return node
        for child in node.children:
            if child.type in (
                "function_declarator",
                "pointer_declarator",
                "reference_declarator",
                "qualified_identifier",
            ):
                found = get_function_declarator(child)
                if found:
                    return found
        return None

    def get_declarator_name(decl_node: tree_sitter.Node) -> str:
        name_node = decl_node.child_by_field_name("declarator")
        if name_node:
            if name_node.type in (
                "identifier",
                "field_identifier",
                "destructor_name",
                "operator_name",
                "qualified_identifier",
            ):
                return get_node_text(name_node)
            return get_declarator_name(name_node)
        for child in decl_node.children:
            if child.type in (
                "identifier",
                "field_identifier",
                "destructor_name",
                "operator_name",
                "qualified_identifier",
            ):
                return get_node_text(child)
        return "<function>"

    def parse_cpp_params(param_list_node: Optional[tree_sitter.Node]) -> list[str]:
        if not param_list_node:
            return []
        params = []
        for child in param_list_node.children:
            if child.type in ("parameter_declaration", "optional_parameter_declaration"):
                params.append(get_node_text(child))
        return params

    def parse_cpp_func(node: tree_sitter.Node) -> Optional[FunctionMetadata]:
        decl_node = node.child_by_field_name("declarator")
        if not decl_node:
            return None
        func_decl = get_function_declarator(decl_node)
        if not func_decl:
            return None
        name = get_declarator_name(func_decl)
        params_node = func_decl.child_by_field_name("parameters")
        return FunctionMetadata(
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parse_cpp_params(params_node),
        )

    def parse_cpp_method(node: tree_sitter.Node) -> Optional[MethodMetadata]:
        decl_node = node.child_by_field_name("declarator")
        if not decl_node:
            return None
        func_decl = get_function_declarator(decl_node)
        if not func_decl:
            return None
        name = get_declarator_name(func_decl)
        params_node = func_decl.child_by_field_name("parameters")
        return MethodMetadata(
            name=name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parse_cpp_params(params_node),
        )

    def parse_cpp_class(class_node: tree_sitter.Node) -> ClassMetadata:
        name_node = class_node.child_by_field_name("name")
        class_name = get_node_text(name_node) if name_node else "<anonymous>"
        body_node = class_node.child_by_field_name("body")
        methods: list[MethodMetadata] = []

        if body_node:
            for child in body_node.children:
                if child.type == "function_definition":
                    m = parse_cpp_method(child)
                    if m:
                        methods.append(m)
                elif child.type == "template_declaration":
                    for sub in child.children:
                        if sub.type == "function_definition":
                            m = parse_cpp_method(sub)
                            if m:
                                methods.append(m)

        return ClassMetadata(
            name=class_name,
            start_line=class_node.start_point[0] + 1,
            end_line=class_node.end_point[0] + 1,
            methods=methods,
        )

    def visit(node: tree_sitter.Node) -> None:
        if node.type in ("preproc_include", "using_declaration"):
            imports.append(get_node_text(node))
            return
        elif node.type == "function_definition":
            fn = parse_cpp_func(node)
            if fn:
                functions.append(fn)
            return
        elif node.type in ("class_specifier", "struct_specifier"):
            classes.append(parse_cpp_class(node))
            return
        elif node.type == "template_declaration":
            for child in node.children:
                if child.type == "function_definition":
                    fn = parse_cpp_func(child)
                    if fn:
                        functions.append(fn)
                    return
                elif child.type in ("class_specifier", "struct_specifier"):
                    classes.append(parse_cpp_class(child))
                    return

        for child in node.children:
            if child.type not in ("class_specifier", "struct_specifier", "field_declaration_list"):
                visit(child)

    for child in root_node.children:
        visit(child)

    return imports, functions, classes


# ------------------------------------------------------------------------------
# Java Extractor
# ------------------------------------------------------------------------------
def extract_java(
    root_node: tree_sitter.Node,
) -> tuple[list[str], list[FunctionMetadata], list[ClassMetadata]]:
    """Extracts packages, imports, classes, interfaces, and methods from a Java AST."""
    imports: list[str] = []
    functions: list[FunctionMetadata] = []
    classes: list[ClassMetadata] = []

    def parse_java_params(params_node: Optional[tree_sitter.Node]) -> list[str]:
        if not params_node:
            return []
        params = []
        for child in params_node.children:
            if child.type in ("formal_parameter", "spread_parameter"):
                params.append(get_node_text(child))
        return params

    def parse_java_method(method_node: tree_sitter.Node) -> MethodMetadata:
        name_node = method_node.child_by_field_name("name")
        method_name = get_node_text(name_node) if name_node else "<method>"
        params_node = method_node.child_by_field_name("parameters")
        return MethodMetadata(
            name=method_name,
            start_line=method_node.start_point[0] + 1,
            end_line=method_node.end_point[0] + 1,
            parameters=parse_java_params(params_node),
        )

    def parse_java_class(class_node: tree_sitter.Node) -> ClassMetadata:
        name_node = class_node.child_by_field_name("name")
        class_name = get_node_text(name_node) if name_node else "<anonymous>"
        body_node = class_node.child_by_field_name("body")
        methods: list[MethodMetadata] = []

        if body_node:
            for child in body_node.children:
                if child.type in ("method_declaration", "constructor_declaration"):
                    methods.append(parse_java_method(child))
                elif child.type in (
                    "class_declaration",
                    "interface_declaration",
                    "enum_declaration",
                    "record_declaration",
                ):
                    classes.append(parse_java_class(child))

        return ClassMetadata(
            name=class_name,
            start_line=class_node.start_point[0] + 1,
            end_line=class_node.end_point[0] + 1,
            methods=methods,
        )

    for child in root_node.children:
        if child.type in ("import_declaration", "package_declaration"):
            imports.append(get_node_text(child))
        elif child.type in (
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "record_declaration",
        ):
            classes.append(parse_java_class(child))
        elif child.type in ("method_declaration", "constructor_declaration"):
            m = parse_java_method(child)
            functions.append(
                FunctionMetadata(
                    name=m.name,
                    start_line=m.start_line,
                    end_line=m.end_line,
                    parameters=m.parameters,
                )
            )

    return imports, functions, classes


# ==============================================================================
# 4. MODULAR LANGUAGE CONFIGURATION & REGISTRY
# ==============================================================================

class LanguageConfig:
    def __init__(
        self,
        name: str,
        extensions: set[str],
        grammar_loader: Callable[[], Optional[Language]],
        extractor: Callable[
            [tree_sitter.Node],
            tuple[list[str], list[FunctionMetadata], list[ClassMetadata]],
        ],
    ):
        self.name = name
        self.extensions = extensions
        self.grammar_loader = grammar_loader
        self.extractor = extractor


def _load_python_language() -> Optional[Language]:
    return Language(tree_sitter_python.language()) if tree_sitter_python else None


def _load_javascript_language() -> Optional[Language]:
    return Language(tree_sitter_javascript.language()) if tree_sitter_javascript else None


def _load_cpp_language() -> Optional[Language]:
    return Language(tree_sitter_cpp.language()) if tree_sitter_cpp else None


def _load_java_language() -> Optional[Language]:
    return Language(tree_sitter_java.language()) if tree_sitter_java else None


LANGUAGE_REGISTRY: dict[str, LanguageConfig] = {
    "Python": LanguageConfig(
        name="Python",
        extensions={".py", ".pyi"},
        grammar_loader=_load_python_language,
        extractor=extract_python,
    ),
    "JavaScript": LanguageConfig(
        name="JavaScript",
        extensions={".js", ".jsx", ".mjs", ".cjs"},
        grammar_loader=_load_javascript_language,
        extractor=extract_javascript,
    ),
    "C++": LanguageConfig(
        name="C++",
        extensions={".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".h"},
        grammar_loader=_load_cpp_language,
        extractor=extract_cpp,
    ),
    "Java": LanguageConfig(
        name="Java",
        extensions={".java"},
        grammar_loader=_load_java_language,
        extractor=extract_java,
    ),
}

_PARSER_CACHE: dict[str, Parser] = {}


# ==============================================================================
# 5. CORE HELPER FUNCTIONS
# ==============================================================================

def detect_language(file_path: str | Path) -> Optional[str]:
    """Detects programming language from file extension."""
    path = Path(file_path)
    ext = path.suffix.lower()
    for lang_name, config in LANGUAGE_REGISTRY.items():
        if ext in config.extensions:
            return lang_name
    return None


def get_parser(language: str) -> Optional[Parser]:
    """Retrieves or creates a cached Tree-sitter Parser instance."""
    if language in _PARSER_CACHE:
        return _PARSER_CACHE[language]

    config = LANGUAGE_REGISTRY.get(language)
    if not config:
        return None

    try:
        lang_grammar = config.grammar_loader()
        if not lang_grammar:
            return None
        parser = Parser(lang_grammar)
        _PARSER_CACHE[language] = parser
        return parser
    except Exception:
        return None


def parse_file(
    file_path: str | Path,
) -> tuple[Optional[tree_sitter.Tree], Optional[bytes], list[str]]:
    """Reads and parses a source file into a Tree-sitter AST."""
    path = Path(file_path)
    errors: list[str] = []

    if not path.is_file():
        return None, None, [f"File does not exist: {path}"]

    lang_name = detect_language(path)
    if not lang_name:
        return None, None, [f"Unsupported file type/extension: {path.suffix}"]

    parser = get_parser(lang_name)
    if not parser:
        return None, None, [f"No Tree-sitter grammar available for language: {lang_name}"]

    try:
        source_bytes = path.read_bytes()
    except PermissionError:
        return None, None, [f"Permission denied reading file: {path}"]
    except Exception as e:
        return None, None, [f"Error reading file {path}: {str(e)}"]

    try:
        tree = parser.parse(source_bytes)
        syntax_errors = extract_parse_errors(tree.root_node)
        errors.extend(syntax_errors)
        return tree, source_bytes, errors
    except Exception as e:
        return None, source_bytes, [f"Tree-sitter parse failure: {str(e)}"]


def extract_functions(
    root_node: tree_sitter.Node, language: str
) -> list[FunctionMetadata]:
    """Extracts all top-level functions for the specified language."""
    config = LANGUAGE_REGISTRY.get(language)
    if not config:
        return []
    _, functions, _ = config.extractor(root_node)
    return functions


def extract_classes(
    root_node: tree_sitter.Node, language: str
) -> list[ClassMetadata]:
    """Extracts all classes and nested methods for the specified language."""
    config = LANGUAGE_REGISTRY.get(language)
    if not config:
        return []
    _, _, classes = config.extractor(root_node)
    return classes


def extract_imports(
    root_node: tree_sitter.Node, language: str
) -> list[str]:
    """Extracts all import/include statements for the specified language."""
    config = LANGUAGE_REGISTRY.get(language)
    if not config:
        return []
    imports, _, _ = config.extractor(root_node)
    return imports


# ==============================================================================
# 6. PUBLIC ANALYSIS INTERFACE
# ==============================================================================

def analyze_file(file_path: str | Path) -> FileMetadata:
    """Analyzes a single source file and returns normalized FileMetadata."""
    path = Path(file_path)
    lang_name = detect_language(path) or "Unknown"

    tree, _, errors = parse_file(path)
    if not tree:
        return FileMetadata(
            path=str(path.as_posix()),
            language=lang_name,
            imports=[],
            functions=[],
            classes=[],
            parse_errors=errors,
        )

    config = LANGUAGE_REGISTRY.get(lang_name)
    if not config:
        return FileMetadata(
            path=str(path.as_posix()),
            language=lang_name,
            imports=[],
            functions=[],
            classes=[],
            parse_errors=errors,
        )

    try:
        imports, functions, classes = config.extractor(tree.root_node)
    except Exception as e:
        errors.append(f"AST extraction exception: {str(e)}")
        imports, functions, classes = [], [], []

    return FileMetadata(
        path=str(path.as_posix()),
        language=lang_name,
        imports=imports,
        functions=functions,
        classes=classes,
        parse_errors=errors,
    )


def analyze_repository(
    repo_path: str | Path,
    ignore_dirs: Optional[set[str]] = None,
    ignore_extensions: Optional[set[str]] = None,
) -> list[FileMetadata]:
    """Recursively scans a repository directory and returns normalized FileMetadata."""
    repo = Path(repo_path).resolve()
    ignored_directories = ignore_dirs if ignore_dirs is not None else DEFAULT_IGNORE_DIRS
    ignored_exts = ignore_extensions if ignore_extensions is not None else DEFAULT_IGNORE_EXTENSIONS

    if not repo.exists():
        return []

    results: list[FileMetadata] = []

    if repo.is_file():
        if detect_language(repo):
            results.append(analyze_file(repo))
        return results

    for root, dirs, files in os.walk(repo, topdown=True):
        dirs[:] = [d for d in dirs if d not in ignored_directories and not d.startswith(".")]

        for filename in files:
            file_path = Path(root) / filename
            ext = file_path.suffix.lower()

            if ext in ignored_exts or filename.startswith("."):
                continue

            if detect_language(file_path):
                file_metadata = analyze_file(file_path)
                results.append(file_metadata)

    return results


# ==============================================================================
# 7. CLI / DEMONSTRATION RUNNER
# ==============================================================================

def _create_sample_demo_repository(demo_dir: Path) -> None:
    """Creates a sample multi-language test directory."""
    demo_dir.mkdir(parents=True, exist_ok=True)

    (demo_dir / "calculator.py").write_text(
        "import math\nfrom typing import Optional\n\ndef add(a: int, b: int = 0) -> int:\n    return a + b\n\nclass MathEngine:\n    def __init__(self, precision: int = 2):\n        self.precision = precision\n\n    def compute_sqrt(self, value: float) -> float:\n        return round(math.sqrt(value), self.precision)\n",
        encoding="utf-8",
    )

    (demo_dir / "service.js").write_text(
        "import axios from 'axios';\nconst fs = require('fs');\n\nexport async function fetchUserData(userId, options = {}) {\n    const response = await axios.get(`/users/${userId}`);\n    return response.data;\n}\n\nconst computeTotal = (items, taxRate = 0.05) => {\n    return items.reduce((acc, curr) => acc + curr.price, 0) * (1 + taxRate);\n};\n\nclass AuthManager {\n    constructor(secretKey) {\n        this.secretKey = secretKey;\n    }\n\n    validateToken(token) {\n        return token.startsWith('bearer-');\n    }\n}\n",
        encoding="utf-8",
    )

    (demo_dir / "engine.cpp").write_text(
        "#include <iostream>\n#include <vector>\n#include \"engine.hpp\"\n\nint calculateFactorial(int n) {\n    if (n <= 1) return 1;\n    return n * calculateFactorial(n - 1);\n}\n\nclass Vector3D {\npublic:\n    Vector3D(double x, double y, double z) : x(x), y(y), z(z) {}\n    double magnitude() const {\n        return x * x + y * y + z * z;\n    }\nprivate:\n    double x, y, z;\n};\n",
        encoding="utf-8",
    )

    (demo_dir / "PaymentProcessor.java").write_text(
        "package com.saas.billing;\n\nimport java.util.List;\nimport java.util.UUID;\n\npublic class PaymentProcessor {\n    private String merchantId;\n\n    public PaymentProcessor(String merchantId) {\n        this.merchantId = merchantId;\n    }\n\n    public boolean processTransaction(String accountId, double amount) {\n        return amount > 0;\n    }\n}\n",
        encoding="utf-8",
    )

    (demo_dir / "broken_syntax.py").write_text(
        "def invalid_func(x, :\n    return x +\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser_cli = argparse.ArgumentParser(
        description="Repository Code Parser for AI Code Verification SaaS"
    )
    parser_cli.add_argument(
        "repository_path",
        nargs="?",
        default="./test_repository",
        help="Path to repository to analyze (default: ./test_repository)",
    )
    parser_cli.add_argument(
        "--demo",
        action="store_true",
        help="Generate sample files before scanning",
    )

    args = parser_cli.parse_args()
    target_path = Path(args.repository_path)

    if args.demo or not target_path.exists():
        print(f"[+] Creating sample multi-language test repository at '{target_path}'...")
        _create_sample_demo_repository(target_path)

    print(f"[+] Scanning and analyzing repository: '{target_path}'")
    scan_results = analyze_repository(target_path)

    serialized = [item.to_dict() for item in scan_results]
    print(json.dumps(serialized, indent=2))

    print("\n" + "=" * 50)
    print("ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"Files Processed  : {len(scan_results)}")
    print(f"Top-level Funcs  : {sum(len(f.functions) for f in scan_results)}")
    print(f"Classes / Structs: {sum(len(f.classes) for f in scan_results)}")
    print(f"Class Methods    : {sum(sum(len(c.methods) for c in f.classes) for f in scan_results)}")
    print(f"Parse Errors     : {sum(len(f.parse_errors) for f in scan_results)}")
    print("=" * 50)
