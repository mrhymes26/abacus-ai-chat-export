from __future__ import annotations

from pathlib import Path

from .models import ConversationScopes
from .utils import ensure_dir, safe_json_dumps, safe_json_loads


SUPPORTED_SCOPE_KEYS = ("deployment_ids", "external_application_ids", "conversation_types")


def read_conversation_scopes(path: str | Path) -> ConversationScopes:
    file_path = Path(path)
    if not file_path.is_file():
        return ConversationScopes()
    data = safe_json_loads(file_path.read_text(encoding="utf-8"), {})
    return ConversationScopes(**data)


def write_conversation_scopes(path: str | Path, scopes: ConversationScopes) -> ConversationScopes:
    file_path = Path(path)
    ensure_dir(file_path.parent)
    normalized = ConversationScopes(**scopes.model_dump())
    file_path.write_text(safe_json_dumps(normalized.model_dump(mode="json")), encoding="utf-8")
    return normalized


def merge_scope_summaries(*summaries: dict[str, list[str]]) -> dict[str, list[str]]:
    merged = {
        "deployment_ids": [],
        "external_application_ids": [],
        "conversation_types": [],
    }
    for summary in summaries:
        for key in merged:
            for value in summary.get(key, []):
                if value and value not in merged[key]:
                    merged[key].append(value)
    return merged


def summary_to_query_scopes(summary: dict[str, list[str]]) -> list[dict[str, str]]:
    scopes: list[dict[str, str]] = []
    scopes.extend({"deployment_id": value} for value in summary.get("deployment_ids", []))
    scopes.extend({"external_application_id": value} for value in summary.get("external_application_ids", []))
    scopes.extend({"conversation_type": value} for value in summary.get("conversation_types", []))
    return scopes


def has_supported_conversation_scope(summary: dict[str, list[str]]) -> bool:
    return any(summary.get(key) for key in SUPPORTED_SCOPE_KEYS)
