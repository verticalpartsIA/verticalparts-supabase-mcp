from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

from .config import settings


def load_projects() -> dict[str, Any]:
    path: Path = settings.projects_file
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("projects", {})


def get_project_policy(name: str) -> dict[str, Any]:
    return load_projects().get(name, {})


def resolve_ref(name_or_ref: str) -> str:
    """Aceita tanto um project_ref direto quanto um nome registrado em config/projects.yaml."""
    projects = load_projects()
    if name_or_ref in projects:
        ref = projects[name_or_ref].get("ref")
        if ref:
            return ref
    return name_or_ref
