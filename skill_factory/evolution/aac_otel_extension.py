"""Independent consumer for draft-palanisamy-scitt-aac-otel-00.

This module implements only the extension-level admission semantics needed to
consume the draft's positive and must-fail vectors. It does not import
capsule-emit and does not change Agent Action Capsule base verification.

Core rule: correlation metadata may help join a Capsule to telemetry, but it
must never be upgraded into independent corroboration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


BLOCK_KEY = "org.agentactioncapsule.otel"
_SEMCONV_SOURCE_PREFIX = "open-telemetry/semantic-conventions-genai@"
_CACHE_INPUT_TOKENS = re.compile(r"^gen_ai\.usage\.cache_[A-Za-z0-9_.-]+\.input_tokens$")

_HEX = {
    "trace_id": re.compile(r"^[0-9a-f]{32}$"),
    "span_id": re.compile(r"^[0-9a-f]{16}$"),
    "parent_span_id": re.compile(r"^[0-9a-f]{16}$"),
    "trace_flags": re.compile(r"^[0-9a-f]{2}$"),
    "tracestate_digest": re.compile(r"^[0-9a-f]{64}$"),
}

_RESOURCE_ALLOWED = {
    "service.name",
    "service.version",
    "service.namespace",
    "deployment.environment.name",
    "telemetry.sdk.name",
    "telemetry.sdk.version",
}

_SEMCONV_EXACT_ALLOWED = {
    "source",
    "gen_ai.provider.name",
    "gen_ai.request.model",
    "gen_ai.response.model",
    "gen_ai.operation.name",
    "gen_ai.agent.id",
    "gen_ai.agent.name",
    "gen_ai.agent.version",
    "gen_ai.workflow.name",
    "gen_ai.tool.name",
    "gen_ai.tool.type",
    "gen_ai.tool.call.id",
    "gen_ai.usage.input_tokens",
    "gen_ai.usage.output_tokens",
    "gen_ai.usage.reasoning.output_tokens",
    "gen_ai.request.temperature",
    "gen_ai.request.top_p",
    "gen_ai.request.top_k",
    "gen_ai.request.max_tokens",
    "gen_ai.request.seed",
    "gen_ai.request.stop_sequences",
    "gen_ai.request.reasoning.level",
    "gen_ai.request.choice.count",
    "gen_ai.response.finish_reasons",
    "gen_ai.response.status",
    "gen_ai.output.type",
    "gen_ai.response.id",
    "gen_ai.request.previous_response.id",
    "gen_ai.data_source.id",
    "gen_ai.memory.store.id",
    "gen_ai.prompt.name",
    "gen_ai.prompt.version",
}

_NEVER_ENTER_PREFIXES = (
    "gen_ai.input.messages",
    "gen_ai.output.messages",
    "gen_ai.system_instructions",
    "gen_ai.tool.call.arguments",
    "gen_ai.tool.call.result",
    "gen_ai.tool.definitions",
    "gen_ai.memory.records",
    "gen_ai.memory.query.text",
    "gen_ai.retrieval.query.text",
    "gen_ai.retrieval.documents",
    "gen_ai.prompt.variable.",
    "gen_ai.conversation.id",
    "mcp.session.id",
    "session_id",
    "enduser.",
    "user.",
    "gen_ai.evaluation.",
)

_OUT_OF_SCOPE_PREFIXES = (
    "gen_ai.client.",
    "gen_ai.server.",
    "mcp.",
)

_KNOWN_BLOCK_FIELDS = {
    "trace_id",
    "span_id",
    "parent_span_id",
    "trace_flags",
    "tracestate_digest",
    "span_name",
    "resource",
    "semconv",
}


@dataclass(frozen=True)
class OTelExtensionVerdict:
    status: str
    reasons: tuple[str, ...]
    placement: str
    independent_corroboration: bool


class OTelExtensionError(ValueError):
    """Raised only for structurally unusable outer input."""


def _is_namespaced(name: str) -> bool:
    return "." in name or "://" in name


def _extract_block(capsule: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(capsule, dict):
        raise OTelExtensionError("capsule must be a JSON object")

    top = capsule.get(BLOCK_KEY)
    nested = (
        ((capsule.get("model_attestation") or {}).get("compute_attestation") or {}).get(
            BLOCK_KEY
        )
        if isinstance(capsule.get("model_attestation"), dict)
        else None
    )

    if top is not None and nested is not None:
        if top != nested:
            return None, "conflicting-dual-placement"
        return top, "both-identical"
    if top is not None:
        return top, "top-level"
    if nested is not None:
        return nested, "model_attestation.compute_attestation"
    return None, "absent"


def _semconv_name_allowed(name: str) -> bool:
    return name in _SEMCONV_EXACT_ALLOWED or bool(_CACHE_INPUT_TOKENS.fullmatch(name))


def _validate_semconv(semconv: Any, reasons: list[str]) -> None:
    if semconv is None:
        return
    if not isinstance(semconv, dict):
        reasons.append("semconv-not-object")
        return

    source = semconv.get("source")
    source_suffix = (
        source[len(_SEMCONV_SOURCE_PREFIX):]
        if isinstance(source, str) and source.startswith(_SEMCONV_SOURCE_PREFIX)
        else ""
    )
    if not source_suffix.strip():
        reasons.append("semconv-source-missing-or-unpinned")

    for name in semconv:
        if _semconv_name_allowed(name):
            continue
        if any(name.startswith(prefix) for prefix in _NEVER_ENTER_PREFIXES):
            reasons.append(f"semconv-never-enters:{name}")
            continue
        if any(name.startswith(prefix) for prefix in _OUT_OF_SCOPE_PREFIXES):
            reasons.append(f"semconv-out-of-scope:{name}")
            continue
        reasons.append(f"semconv-not-allowlisted:{name}")


def _validate_resource(resource: Any, reasons: list[str]) -> None:
    if resource is None:
        return
    if not isinstance(resource, dict):
        reasons.append("resource-not-object")
        return
    for name in resource:
        if name not in _RESOURCE_ALLOWED:
            reasons.append(f"resource-not-clear-safe:{name}")


def validate_aac_otel_extension(capsule: dict[str, Any]) -> OTelExtensionVerdict:
    """Conservatively validate the AAC OpenTelemetry correlation extension.

    Invalid extension data is classified INFORMATIONAL_ONLY instead of changing
    the surrounding Capsule's base verification verdict, matching the draft's
    extension boundary.
    """
    block, placement = _extract_block(capsule)
    if placement == "conflicting-dual-placement":
        return OTelExtensionVerdict(
            status="INFORMATIONAL_ONLY",
            reasons=("conflicting-dual-placement",),
            placement=placement,
            independent_corroboration=False,
        )
    if block is None:
        return OTelExtensionVerdict(
            status="ABSENT",
            reasons=(),
            placement=placement,
            independent_corroboration=False,
        )
    if not isinstance(block, dict):
        return OTelExtensionVerdict(
            status="INFORMATIONAL_ONLY",
            reasons=("block-not-object",),
            placement=placement,
            independent_corroboration=False,
        )

    reasons: list[str] = []

    for required in ("trace_id", "span_id"):
        if required not in block:
            reasons.append(f"missing-required:{required}")

    for field, pattern in _HEX.items():
        if field in block:
            value = block[field]
            if not isinstance(value, str) or not pattern.fullmatch(value):
                reasons.append(f"malformed-hex:{field}")

    if "tracestate" in block:
        reasons.append("clear-tracestate-forbidden")
    if "baggage" in block:
        reasons.append("baggage-forbidden")

    for field in block:
        if field in _KNOWN_BLOCK_FIELDS:
            continue
        if field in {"tracestate", "baggage"}:
            continue
        if not _is_namespaced(field):
            reasons.append(f"unnamespaced-unknown-member:{field}")

    _validate_resource(block.get("resource"), reasons)
    _validate_semconv(block.get("semconv"), reasons)

    status = "ACCEPTED" if not reasons else "INFORMATIONAL_ONLY"
    return OTelExtensionVerdict(
        status=status,
        reasons=tuple(sorted(set(reasons))),
        placement=placement,
        independent_corroboration=False,
    )
