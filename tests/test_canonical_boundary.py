import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_activity_renderer_delegates_to_canonical_renderer():
    source = _source("ui/day_blocks.py")
    tree = ast.parse(source)

    build_activity = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_activity_block"
    )

    calls = [
        node.func.id
        for node in ast.walk(build_activity)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]

    assert calls == ["render_activity_block"]


def test_activity_renderer_does_not_read_raw_supplier_title_directly():
    source = _source("ui/day_blocks.py")
    tree = ast.parse(source)

    build_activity = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_activity_block"
    )

    raw_title_reads = []
    for node in ast.walk(build_activity):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "get":
            continue
        if not node.args:
            continue
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant) and first_arg.value in {"title", "original_title", "details"}:
            raw_title_reads.append(first_arg.value)

    assert raw_title_reads == []

def test_accommodation_renderer_delegates_to_canonical_renderer():
    source = _source("ui/day_blocks.py")
    tree = ast.parse(source)

    build_accommodation = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_accommodation_block"
    )

    calls = [
        node.func.id
        for node in ast.walk(build_accommodation)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]

    assert calls == ["render_accommodation_block"]

