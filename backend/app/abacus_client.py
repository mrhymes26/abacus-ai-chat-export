from __future__ import annotations

import hashlib
import inspect
from typing import Any, Callable

from .exporters import to_plain_data
from .models import ChatItem, ConnectionResult, ExportResult
from .security import create_client, get_api_key_from_env, safe_error
from .utils import first_present, get_value, shallow_preview


CANDIDATE_METHODS = [
    "suggest_abacus_apis",
    "list_chat_sessions",
    "get_chat_session",
    "export_chat_session",
    "list_projects",
    "list_deployments",
    "list_external_applications",
    "list_deployment_conversations",
    "get_deployment_conversation",
    "export_deployment_conversation",
]

ID_KEYS = (
    "chat_session_id",
    "chatSessionId",
    "deployment_conversation_id",
    "deploymentConversationId",
    "conversation_id",
    "conversationId",
    "external_session_id",
    "externalSessionId",
    "id",
    "session_id",
    "sessionId",
)
TITLE_KEYS = (
    "name",
    "title",
    "chat_session_name",
    "chatSessionName",
    "conversation_name",
    "conversationName",
    "deployment_conversation_name",
    "deploymentConversationName",
)
CREATED_KEYS = ("created_at", "createdAt", "created", "creation_time", "creationTime")
UPDATED_KEYS = ("updated_at", "updatedAt", "modified_at", "modifiedAt")
LAST_EVENT_KEYS = ("last_event_created_at", "lastEventCreatedAt", "last_message_at", "lastMessageAt")
MESSAGE_COUNT_KEYS = ("message_count", "messageCount", "num_messages", "numMessages")
PROJECT_ID_KEYS = ("project_id", "projectId", "id")
DEPLOYMENT_ID_KEYS = ("deployment_id", "deploymentId", "id")
EXTERNAL_APPLICATION_ID_KEYS = ("external_application_id", "externalApplicationId", "application_id", "applicationId", "id")
DEFAULT_ITEM_KEYS = (
    "items",
    "results",
    "chat_sessions",
    "chatSessions",
    "conversations",
    "deployment_conversations",
    "deploymentConversations",
)
NEXT_TOKEN_KEYS = ("next_page_token", "nextPageToken", "page_token", "pageToken")
SCOPE_PARAM_VARIANTS = {
    "deployment_id": ("deployment_id", "deploymentId"),
    "external_application_id": ("external_application_id", "externalApplicationId"),
    "conversation_type": ("conversation_type", "conversationType"),
}
UNSUPPORTED_KWARGS_MARKER = "No supported keyword arguments for SDK method"


def call_with_supported_kwargs(method: Callable[..., Any], **kwargs: Any) -> Any:
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return method(**kwargs)

    parameters = signature.parameters
    accepts_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values())
    if accepts_kwargs:
        try:
            return method(**kwargs)
        except TypeError:
            pass

    supported = {key: value for key, value in kwargs.items() if key in parameters}
    if kwargs and not supported:
        raise TypeError(f"{UNSUPPORTED_KWARGS_MARKER}: {', '.join(sorted(kwargs))}")
    try:
        return method(**supported)
    except TypeError:
        if supported != kwargs:
            return method(**kwargs)
        raise


def try_call_variants(method: Callable[..., Any], variants: list[dict[str, Any]]) -> Any:
    last_error: Exception | None = None
    for variant in variants:
        try:
            return call_with_supported_kwargs(method, **variant)
        except Exception as exc:
            if last_error is None or not _is_unsupported_kwargs_error(exc):
                last_error = exc
    if last_error:
        raise last_error
    return call_with_supported_kwargs(method)


def iter_paginated_results(
    method: Callable[..., Any],
    base_kwargs: dict[str, Any] | None = None,
    item_keys: list[str] | None = None,
    max_pages: int = 50,
) -> list[Any]:
    keys = tuple(item_keys or []) + DEFAULT_ITEM_KEYS
    kwargs = dict(base_kwargs or {})
    results: list[Any] = []
    seen_tokens: set[str] = set()
    offset = int(kwargs.get("offset") or 0)

    for _ in range(max_pages):
        response = call_with_supported_kwargs(method, **kwargs)
        page_items = _extract_items(response, keys)
        results.extend(page_items)

        token = _extract_next_token(response)
        if token:
            token_text = str(token)
            if token_text in seen_tokens:
                break
            seen_tokens.add(token_text)
            kwargs["page_token"] = token_text
            kwargs["pageToken"] = token_text
            kwargs["next_page_token"] = token_text
            continue

        has_more = bool(first_present(response, ("has_more", "hasMore", "more", "has_next", "hasNext")))
        if has_more and page_items:
            offset += len(page_items)
            kwargs["offset"] = offset
            continue
        break
    return results


class AbacusService:
    def __init__(self) -> None:
        self._client: Any | None = None
        self._source: str = "none"
        self.available_methods: list[str] = []
        self.missing_methods: list[str] = CANDIDATE_METHODS.copy()
        self.last_warnings: list[str] = []
        self._discovered_conversation_scopes: list[dict[str, str]] | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    @property
    def source(self) -> str:
        return self._source

    def connect(self, api_key: str | None = None) -> ConnectionResult:
        return self.connect_with_fallback(api_key=api_key)

    def connect_with_fallback(
        self,
        api_key: str | None = None,
        fallback_api_key: str | None = None,
        fallback_source: str = "stored",
    ) -> ConnectionResult:
        env_key = None if api_key else get_api_key_from_env()
        chosen_key = api_key or env_key or fallback_api_key
        source = "ui" if api_key else "env" if env_key else fallback_source if fallback_api_key else "none"
        if not chosen_key:
            raise ValueError("Kein Abacus.AI API-Key vorhanden.")

        client = create_client(chosen_key)
        warnings: list[str] = []
        available = self.discover_methods(client)
        missing = [method for method in CANDIDATE_METHODS if method not in available]

        if hasattr(client, "suggest_abacus_apis"):
            method = getattr(client, "suggest_abacus_apis")
            query = "list and export all chat sessions and deployment conversations"
            try:
                method(query, verbosity=2, limit=10)
            except TypeError:
                try_call_variants(
                    method,
                    [
                        {"query": query, "verbosity": 2, "limit": 10},
                        {"prompt": query, "verbosity": 2, "limit": 10},
                        {"request": query, "verbosity": 2, "limit": 10},
                    ],
                )
            except Exception as exc:
                raise RuntimeError(f"Abacus-Verbindungstest fehlgeschlagen: {safe_error(exc)}") from exc
        else:
            warnings.append("suggest_abacus_apis ist im installierten SDK nicht verfügbar; Verbindung wurde nur initialisiert.")

        self._client = client
        self._source = source
        self.available_methods = available
        self.missing_methods = missing
        self.last_warnings = warnings
        self._discovered_conversation_scopes = None
        return ConnectionResult(
            connected=True,
            source=source,  # type: ignore[arg-type]
            available_methods=available,
            missing_methods=missing,
            warnings=warnings,
        )

    def discover_methods(self, client: Any | None = None) -> list[str]:
        active_client = client or self._client
        if active_client is None:
            return []
        return [method for method in CANDIDATE_METHODS if hasattr(active_client, method)]

    def discover_conversation_scopes(self, force: bool = False) -> list[dict[str, str]]:
        if self._discovered_conversation_scopes is not None and not force:
            return self._discovered_conversation_scopes

        client = self._require_client()
        warnings: list[str] = []
        scopes: list[dict[str, str]] = []
        scopes.extend(self._discover_deployment_id_scopes(client, warnings))
        scopes.extend(self._discover_external_application_scopes(client, warnings))
        if not scopes:
            scopes.extend({"conversation_type": value} for value in _deployment_conversation_type_values())
            if scopes:
                warnings.append(
                    "Keine Deployment IDs oder External Application IDs automatisch gefunden; "
                    "verwende Conversation-Type-Fallbacks aus dem installierten Abacus SDK."
                )

        self._discovered_conversation_scopes = _dedupe_scopes(scopes)
        if warnings:
            self.last_warnings = _dedupe_strings(self.last_warnings + warnings)
        return self._discovered_conversation_scopes

    def discovered_conversation_scope_summary(self) -> dict[str, list[str]]:
        return _scope_summary_from_scopes(self._discovered_conversation_scopes or [])

    def list_all_chats(
        self,
        include_ai_chat: bool = True,
        include_deployments: bool = True,
        deployment_ids: list[str] | None = None,
        conversation_scopes: list[dict[str, str]] | None = None,
    ) -> list[ChatItem]:
        client = self._require_client()
        warnings: list[str] = []
        items: list[ChatItem] = []

        if include_ai_chat:
            if hasattr(client, "list_chat_sessions"):
                try:
                    raw_items = iter_paginated_results(
                        getattr(client, "list_chat_sessions"),
                        item_keys=["chat_sessions", "chatSessions", "items", "results"],
                    )
                    items.extend(_normalize_chat_item(raw, "ai_chat") for raw in raw_items)
                except Exception as exc:
                    warnings.append(f"AI-Chat-Sessions konnten nicht geladen werden: {safe_error(exc)}")
            else:
                warnings.append("SDK-Methode list_chat_sessions fehlt.")

        if include_deployments:
            if hasattr(client, "list_deployment_conversations"):
                method = getattr(client, "list_deployment_conversations")
                scopes = _merge_conversation_scopes(deployment_ids or [], conversation_scopes or [])
                if not scopes:
                    scopes = self.discover_conversation_scopes()
                if scopes:
                    for scope in scopes:
                        items.extend(self._list_deployment_conversations_for_scope(method, scope, warnings))
                else:
                    warnings.append(
                        "Deployment Conversations konnten nicht geladen werden, weil kein unterstuetzter Scope "
                        "gesetzt oder automatisch ermittelt werden konnte. Setze eine Deployment ID, External "
                        "Application ID oder Conversation Type."
                    )
            else:
                warnings.append("SDK-Methode list_deployment_conversations fehlt.")

        unique: dict[tuple[str, str | None, str], ChatItem] = {}
        for item in items:
            unique[(item.type, item.deployment_id, item.id)] = item
        self.last_warnings = warnings
        return list(unique.values())

    def get_chat_detail(self, chat_item: ChatItem) -> dict[str, Any]:
        client = self._require_client()
        if chat_item.type == "ai_chat":
            if not hasattr(client, "get_chat_session"):
                return {"raw_preview": chat_item.raw_preview or {}, "warning": "SDK-Methode get_chat_session fehlt."}
            method = getattr(client, "get_chat_session")
            response = try_call_variants(
                method,
                [
                    {"chat_session_id": chat_item.id},
                    {"chatSessionId": chat_item.id},
                    {"id": chat_item.id},
                    {"session_id": chat_item.id},
                    {"sessionId": chat_item.id},
                ],
            )
            return to_plain_data(response)

        if not hasattr(client, "get_deployment_conversation"):
            return {
                "raw_preview": chat_item.raw_preview or {},
                "warning": "SDK-Methode get_deployment_conversation fehlt.",
            }
        method = getattr(client, "get_deployment_conversation")
        response = try_call_variants(
            method,
            _deployment_conversation_variants(chat_item),
        )
        return to_plain_data(response)

    def export_chat_html(self, chat_item: ChatItem) -> ExportResult:
        client = self._require_client()
        if chat_item.type == "ai_chat":
            if not hasattr(client, "export_chat_session"):
                raise AttributeError("SDK-Methode export_chat_session fehlt.")
            method = getattr(client, "export_chat_session")
            response = try_call_variants(
                method,
                [
                    {"chat_session_id": chat_item.id},
                    {"chatSessionId": chat_item.id},
                    {"id": chat_item.id},
                    {"session_id": chat_item.id},
                    {"sessionId": chat_item.id},
                ],
            )
        else:
            if not hasattr(client, "export_deployment_conversation"):
                raise AttributeError("SDK-Methode export_deployment_conversation fehlt.")
            method = getattr(client, "export_deployment_conversation")
            response = try_call_variants(
                method,
                _deployment_conversation_variants(chat_item),
            )
        return ExportResult(ok=True, data=response)

    def _discover_deployment_id_scopes(self, client: Any, warnings: list[str]) -> list[dict[str, str]]:
        if not hasattr(client, "list_projects") or not hasattr(client, "list_deployments"):
            return []
        try:
            projects = iter_paginated_results(
                getattr(client, "list_projects"),
                base_kwargs={"limit": 100},
                item_keys=["projects", "items", "results"],
                max_pages=1,
            )
        except Exception as exc:
            warnings.append(f"Deployment-ID Autodiscovery ueber list_projects fehlgeschlagen: {safe_error(exc)}")
            return []

        scopes: list[dict[str, str]] = []
        for project in projects[:100]:
            project_id = _extract_text_value(project, PROJECT_ID_KEYS)
            if not project_id:
                continue
            try:
                deployments = iter_paginated_results(
                    getattr(client, "list_deployments"),
                    base_kwargs={"project_id": project_id},
                    item_keys=["deployments", "items", "results"],
                    max_pages=5,
                )
            except Exception as exc:
                warnings.append(f"Deployments fuer project_id={project_id} konnten nicht ermittelt werden: {safe_error(exc)}")
                continue
            for deployment in deployments:
                deployment_id = _extract_text_value(deployment, DEPLOYMENT_ID_KEYS)
                if deployment_id:
                    scopes.append({"deployment_id": deployment_id})
        return scopes

    def _discover_external_application_scopes(self, client: Any, warnings: list[str]) -> list[dict[str, str]]:
        if not hasattr(client, "list_external_applications"):
            return []
        try:
            applications = iter_paginated_results(
                getattr(client, "list_external_applications"),
                item_keys=["external_applications", "externalApplications", "items", "results"],
                max_pages=1,
            )
        except Exception as exc:
            warnings.append(f"External-Application Autodiscovery fehlgeschlagen: {safe_error(exc)}")
            return []
        scopes: list[dict[str, str]] = []
        for application in applications:
            external_application_id = _extract_text_value(application, EXTERNAL_APPLICATION_ID_KEYS)
            if external_application_id:
                scopes.append({"external_application_id": external_application_id})
        return scopes

    def _list_deployment_conversations_for_scope(
        self,
        method: Callable[..., Any],
        scope: dict[str, str],
        warnings: list[str],
    ) -> list[ChatItem]:
        variants = _scope_call_variants(scope)
        last_error: Exception | None = None
        for kwargs in variants:
            kwargs = {
                **kwargs,
                "limit": 600,
                "include_org_level_conversations": True,
            }
            try:
                raw_items = iter_paginated_results(
                    method,
                    base_kwargs=kwargs,
                    item_keys=["deployment_conversations", "deploymentConversations", "conversations", "items", "results"],
                )
                return [
                    _normalize_chat_item(raw, "deployment_conversation", deployment_id=scope.get("deployment_id"), scope=scope)
                    for raw in raw_items
                ]
            except Exception as exc:
                if last_error is None or not _is_unsupported_kwargs_error(exc):
                    last_error = exc
        if last_error:
            warnings.append(
                f"Deployment Conversations fuer {_scope_label(scope)} konnten nicht geladen werden: {safe_error(last_error)}"
            )
        return []

    def _require_client(self) -> Any:
        if self._client is None:
            raise RuntimeError("Nicht verbunden. Bitte zuerst /api/connect aufrufen oder ABACUS_API_KEY setzen.")
        return self._client


def _extract_items(response: Any, item_keys: tuple[str, ...]) -> list[Any]:
    if response is None:
        return []
    if isinstance(response, (list, tuple)):
        return list(response)
    for key in item_keys:
        value = get_value(response, key)
        if isinstance(value, (list, tuple)):
            return list(value)
        if value is not None and not callable(value):
            plain = to_plain_data(value)
            if isinstance(plain, list):
                return plain
    plain_response = to_plain_data(response)
    if isinstance(plain_response, list):
        return plain_response
    if isinstance(plain_response, dict):
        for key in item_keys:
            value = plain_response.get(key)
            if isinstance(value, list):
                return value
    return []


def _is_unsupported_kwargs_error(exc: Exception) -> bool:
    return isinstance(exc, TypeError) and UNSUPPORTED_KWARGS_MARKER in str(exc)


def _extract_next_token(response: Any) -> Any:
    return first_present(response, NEXT_TOKEN_KEYS)


def _extract_text_value(raw: Any, keys: tuple[str, ...]) -> str | None:
    plain = to_plain_data(raw)
    value = first_present(plain, keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_chat_item(
    raw: Any,
    chat_type: str,
    deployment_id: str | None = None,
    scope: dict[str, str] | None = None,
) -> ChatItem:
    plain = to_plain_data(raw)
    preview = shallow_preview(plain)
    if scope:
        preview["abacus_query_scope"] = scope
    raw_id = first_present(plain, ID_KEYS)
    if raw_id is None:
        digest = hashlib.sha256(repr(preview).encode("utf-8")).hexdigest()[:12]
        raw_id = f"generated_{digest}"
        exportable = False
    else:
        exportable = True
    item_deployment_id = deployment_id or first_present(
        plain, ("deployment_id", "deploymentId", "deploymentId", "deployment_reference", "deploymentReference")
    )
    return ChatItem(
        id=str(raw_id),
        type=chat_type,  # type: ignore[arg-type]
        deployment_id=str(item_deployment_id) if item_deployment_id else None,
        title=_string_or_none(first_present(plain, TITLE_KEYS)),
        created_at=_string_or_none(first_present(plain, CREATED_KEYS)),
        updated_at=_string_or_none(first_present(plain, UPDATED_KEYS)),
        last_event_created_at=_string_or_none(first_present(plain, LAST_EVENT_KEYS)),
        message_count=_int_or_none(first_present(plain, MESSAGE_COUNT_KEYS)),
        raw_preview=preview,
        exportable=exportable,
        selected=False,
    )


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _merge_conversation_scopes(
    deployment_ids: list[str],
    conversation_scopes: list[dict[str, str]],
) -> list[dict[str, str]]:
    scopes: list[dict[str, str]] = []
    scopes.extend({"deployment_id": value} for value in deployment_ids if value)
    for scope in conversation_scopes:
        cleaned = {key: str(value) for key, value in scope.items() if key in SCOPE_PARAM_VARIANTS and value}
        if cleaned:
            scopes.append(cleaned)

    unique: dict[tuple[tuple[str, str], ...], dict[str, str]] = {}
    for scope in scopes:
        unique[tuple(sorted(scope.items()))] = scope
    return list(unique.values())


def _dedupe_scopes(scopes: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[tuple[tuple[str, str], ...], dict[str, str]] = {}
    for scope in scopes:
        cleaned = {key: str(value) for key, value in scope.items() if key in SCOPE_PARAM_VARIANTS and value}
        if cleaned:
            unique[tuple(sorted(cleaned.items()))] = cleaned
    return list(unique.values())


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _scope_summary_from_scopes(scopes: list[dict[str, str]]) -> dict[str, list[str]]:
    summary = {
        "deployment_ids": [],
        "external_application_ids": [],
        "conversation_types": [],
    }
    for scope in scopes:
        if scope.get("deployment_id") and scope["deployment_id"] not in summary["deployment_ids"]:
            summary["deployment_ids"].append(scope["deployment_id"])
        if scope.get("external_application_id") and scope["external_application_id"] not in summary["external_application_ids"]:
            summary["external_application_ids"].append(scope["external_application_id"])
        if scope.get("conversation_type") and scope["conversation_type"] not in summary["conversation_types"]:
            summary["conversation_types"].append(scope["conversation_type"])
    return summary


def _deployment_conversation_type_values() -> list[str]:
    try:
        from abacusai.api_class.enums import DeploymentConversationType

        return [str(getattr(member, "value", member)).strip() for member in DeploymentConversationType if str(getattr(member, "value", member)).strip()]
    except Exception:
        return [
            "CHATLLM",
            "SIMPLE_AGENT",
            "COMPLEX_AGENT",
            "WORKFLOW_AGENT",
            "COPILOT",
            "AGENT_CONTROLLER",
            "CODE_LLM",
            "CODE_LLM_AGENT",
            "CODE_LLM_COWORK",
            "CHAT_LLM_TASK",
            "COMPUTER_AGENT",
            "SEARCH_LLM",
            "APP_LLM",
            "TEST_AGENT",
            "SUPER_AGENT",
            "CODE_LLM_NON_INTERACTIVE",
            "BROWSER_EXTENSION",
            "OFFICE",
        ]


def _scope_call_variants(scope: dict[str, str]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for key, value in scope.items():
        for param_name in SCOPE_PARAM_VARIANTS.get(key, (key,)):
            variants.append({param_name: value})
    if len(scope) > 1:
        snake_case = {key: value for key, value in scope.items()}
        camel_case = {
            SCOPE_PARAM_VARIANTS[key][1]: value
            for key, value in scope.items()
            if key in SCOPE_PARAM_VARIANTS and len(SCOPE_PARAM_VARIANTS[key]) > 1
        }
        variants.extend([snake_case, camel_case])
    return variants


def _deployment_conversation_variants(chat_item: ChatItem) -> list[dict[str, Any]]:
    id_variants = [
        {"deployment_conversation_id": chat_item.id},
        {"deploymentConversationId": chat_item.id},
        {"conversation_id": chat_item.id},
        {"conversationId": chat_item.id},
        {"id": chat_item.id},
    ]
    scopes = _scope_variants_from_item(chat_item)
    if not scopes:
        return id_variants

    variants: list[dict[str, Any]] = []
    for scope in scopes:
        for id_variant in id_variants:
            merged = {**scope, **id_variant}
            variants.append({key: value for key, value in merged.items() if value is not None})
    variants.extend(id_variants)
    return variants


def _scope_variants_from_item(chat_item: ChatItem) -> list[dict[str, Any]]:
    scope: dict[str, str] = {}
    if chat_item.raw_preview and isinstance(chat_item.raw_preview.get("abacus_query_scope"), dict):
        raw_scope = chat_item.raw_preview["abacus_query_scope"]
        scope.update(
            {
                key: str(value)
                for key, value in raw_scope.items()
                if key in SCOPE_PARAM_VARIANTS and value
            }
        )
    if chat_item.deployment_id:
        scope.setdefault("deployment_id", chat_item.deployment_id)
    return _scope_call_variants(scope) if scope else []


def _scope_label(scope: dict[str, str]) -> str:
    return ", ".join(f"{key}={value}" for key, value in scope.items())
