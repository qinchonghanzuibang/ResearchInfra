"""Safe helpers for user-editable workspace YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError


class WorkspaceDataError(RuntimeError):
    """Raised when a workspace data file cannot be safely used."""


ModelT = TypeVar("ModelT", bound=BaseModel)


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    """Read a YAML mapping or raise a recovery-oriented workspace error."""

    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise WorkspaceDataError(_malformed_file_message(path)) from exc
    if not isinstance(data, dict):
        raise WorkspaceDataError(_malformed_file_message(path))
    return data


def validate_yaml_model(model_type: type[ModelT], data: object, *, path: Path) -> ModelT:
    """Validate one parsed YAML record while retaining its source path."""

    try:
        return model_type.model_validate(data)
    except ValidationError as exc:
        raise WorkspaceDataError(_malformed_file_message(path)) from exc


def validate_yaml_records(
    data: dict[str, Any], *, key: str, model_type: type[ModelT], path: Path
) -> list[ModelT]:
    """Validate a named YAML list of schema records."""

    records = data.get(key, [])
    if not isinstance(records, list):
        raise WorkspaceDataError(_malformed_file_message(path))
    return [validate_yaml_model(model_type, record, path=path) for record in records]


def write_yaml(path: Path, data: object, *, create_parents: bool = True) -> None:
    """Write YAML and turn workspace I/O failures into user-facing errors."""

    try:
        if create_parents:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    except (OSError, yaml.YAMLError) as exc:
        raise WorkspaceDataError(
            f"Could not write workspace YAML/config file: {path}. "
            "Check permissions and the path, then retry."
        ) from exc


def _malformed_file_message(path: Path) -> str:
    return (
        f"Malformed YAML/config file: {path}. Fix its YAML syntax, restore it from git, "
        "or move the file aside and retry."
    )
