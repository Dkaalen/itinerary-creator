import ast
from pathlib import Path


def _python_files(root: Path):
    for py_file in root.rglob('*.py'):
        if '.git' not in py_file.parts:
            yield py_file


def test_retired_time_utils_facade_has_no_project_imports():
    root = Path(__file__).resolve().parents[1]
    offenders = []
    for py_file in _python_files(root):
        tree = ast.parse(py_file.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'time_utils' or alias.name.startswith('time_utils.'):
                        offenders.append(f'{py_file.relative_to(root)}:{node.lineno}')
            elif isinstance(node, ast.ImportFrom) and (node.module == 'time_utils' or (node.module or '').startswith('time_utils.')):
                offenders.append(f'{py_file.relative_to(root)}:{node.lineno}')

    assert offenders == []


def test_retired_time_utils_facade_file_was_removed():
    root = Path(__file__).resolve().parents[1]
    assert not (root / 'time_utils.py').exists()
