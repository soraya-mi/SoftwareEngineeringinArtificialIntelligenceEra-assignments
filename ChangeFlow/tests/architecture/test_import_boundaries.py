import ast
from pathlib import Path


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_domain_and_application_do_not_import_outer_layers() -> None:
    root = Path("src/changeflow")
    forbidden = ("fastapi", "sqlalchemy", "jwt", "changeflow.api", "changeflow.infrastructure")
    offenders: list[str] = []
    for folder in (root / "domain", root / "application"):
        for path in folder.rglob("*.py"):
            for module in imported_modules(path):
                if module.startswith(forbidden):
                    offenders.append(f"{path}: {module}")
    assert offenders == []
