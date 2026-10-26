"""Compatibility for local absolute paths saved before the project was renamed."""
from pathlib import Path


def relocated_project_path(value: str, root: Path) -> Path | None:
    if root.name.lower() != 'in-editaone':
        return None
    path = Path(value)
    if not path.is_absolute() or path.exists():
        return None
    previous_root = root.parent / 'data-editing-system'
    try:
        relative = path.relative_to(previous_root)
        candidate = (root / relative).resolve()
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.exists() else None
