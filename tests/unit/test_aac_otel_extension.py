from skill_factory.evolution.aac_otel_extension import validate_aac_otel_extension


POSITIVE_BLOCK={
    "org.agentactioncapsule.otel":{
        "trace_id":"4bf92f3577b34da6a3ce929d0e0e4736",
        "span_id":"00f067aa0ba902b7",
        "trace_flags":"01",
        "resource":{"service.name":"support-agent"},
        "semconv":{
            "source":"open-telemetry/semantic-conventions-genai@8c1b98a",
            "gen_ai.provider.name":"local",
            "gen_ai.operation.name":"execute_tool",
        },
    }
}


def test_published_positive_vector_is_accepted():
    verdict=validate_aac_otel_extension(POSITIVE_BLOCK)

    assert verdict.status=="ACCEPTED"
    assert verdict.reasons==()
    assert verdict.independent_corroboration is False


def test_published_malformed_trace_id_vector_is_informational_only():
    capsule={
        "org.agentactioncapsule.otel":{
            "trace_id":"4BF92F3577b34da6a3ce929d0e0e473",
            "span_id":"00f067aa0ba902b7",
        }
    }

    verdict=validate_aac_otel_extension(capsule)

    assert verdict.status=="INFORMATIONAL_ONLY"
    assert "malformed-hex:trace_id" in verdict.reasons


def test_published_clear_tracestate_vector_is_informational_only():
    capsule={
        "org.agentactioncapsule.otel":{
            "trace_id":"4bf92f3577b34da6a3ce929d0e0e4736",
            "span_id":"00f067aa0ba902b7",
            "tracestate":"congo=t61rcWkgMzE",
        }
    }

    verdict=validate_aac_otel_extension(capsule)

    assert verdict.status=="INFORMATIONAL_ONLY"
    assert "clear-tracestate-forbidden" in verdict.reasons


def test_published_non_allowlisted_content_vector_is_informational_only():
    capsule={
        "org.agentactioncapsule.otel":{
            "trace_id":"4bf92f3577b34da6a3ce929d0e0e4736",
            "span_id":"00f067aa0ba902b7",
            "semconv":{
                "source":"open-telemetry/semantic-conventions-genai@8c1b98a",
                "gen_ai.input.messages":[{"role":"user","content":"secret"}],
            },
        }
    }

    verdict=validate_aac_otel_extension(capsule)

    assert verdict.status=="INFORMATIONAL_ONLY"
    assert (
        "semconv-never-enters:gen_ai.input.messages"
        in verdict.reasons
    )


def test_nested_placement_is_treated_identically():
    block=POSITIVE_BLOCK["org.agentactioncapsule.otel"]
    capsule={
        "model_attestation":{
            "compute_attestation":{
                "org.agentactioncapsule.otel":block,
            }
        }
    }

    verdict=validate_aac_otel_extension(capsule)

    assert verdict.status=="ACCEPTED"
    assert verdict.placement=="model_attestation.compute_attestation"


def test_same_producer_telemetry_is_never_independent_corroboration():
    verdict=validate_aac_otel_extension(POSITIVE_BLOCK)

    assert verdict.independent_corroboration is False


def test_unpinned_semconv_source_is_not_promoted():
    block=dict(POSITIVE_BLOCK["org.agentactioncapsule.otel"])
    block["semconv"]={
        "gen_ai.provider.name":"local",
        "gen_ai.operation.name":"execute_tool",
    }

    verdict=validate_aac_otel_extension(
        {"org.agentactioncapsule.otel":block}
    )

    assert verdict.status=="INFORMATIONAL_ONLY"
    assert "semconv-source-missing-or-unpinned" in verdict.reasons


def test_device_identifying_resource_is_not_clear_safe():
    block=dict(POSITIVE_BLOCK["org.agentactioncapsule.otel"])
    block["resource"]={
        "service.name":"support-agent",
        "host.id":"host-123",
    }

    verdict=validate_aac_otel_extension(
        {"org.agentactioncapsule.otel":block}
    )

    assert verdict.status=="INFORMATIONAL_ONLY"
    assert "resource-not-clear-safe:host.id" in verdict.reasons



def test_empty_semconv_source_suffix_is_not_pinned():
    block=dict(POSITIVE_BLOCK["org.agentactioncapsule.otel"])
    block["semconv"]={
        "source":"open-telemetry/semantic-conventions-genai@",
        "gen_ai.operation.name":"execute_tool",
    }

    verdict=validate_aac_otel_extension(
        {"org.agentactioncapsule.otel":block}
    )

    assert verdict.status=="INFORMATIONAL_ONLY"
    assert "semconv-source-missing-or-unpinned" in verdict.reasons


def test_cache_input_token_family_is_admitted_by_draft_pattern():
    block=dict(POSITIVE_BLOCK["org.agentactioncapsule.otel"])
    block["semconv"]={
        "source":"open-telemetry/semantic-conventions-genai@8c1b98a",
        "gen_ai.usage.cache_read.input_tokens":17,
    }

    verdict=validate_aac_otel_extension(
        {"org.agentactioncapsule.otel":block}
    )

    assert verdict.status=="ACCEPTED"
    assert verdict.reasons==()
