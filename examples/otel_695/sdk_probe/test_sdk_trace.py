"""OTel SDK-generated spans: no provider, network, or production trace claims."""
import unittest

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sdk_trace_probe import summarize_observed_spans


class SdkTraceTests(unittest.TestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        self.provider = TracerProvider()
        self.provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.tracer = self.provider.get_tracer("counterproof-otel-695")

    def tearDown(self):
        self.provider.shutdown()

    def span(self, name, op, input_tokens=None, output_tokens=None):
        attrs = {"gen_ai.operation.name": op}
        if input_tokens is not None:
            attrs["gen_ai.usage.input_tokens"] = input_tokens
        if output_tokens is not None:
            attrs["gen_ai.usage.output_tokens"] = output_tokens
        return self.tracer.start_as_current_span(name, attributes=attrs)

    def test_nested_inference_not_double_counted_with_agent_attributes(self):
        with self.span("coordinator", "invoke_agent", 1000, 210):
            with self.span("coordinator model", "chat", 100, 20):
                pass
            with self.span("researcher", "invoke_agent", 700, 110):
                with self.span("research model", "chat", 300, 50):
                    pass
                with self.span("web_search", "invoke_agent", 400, 60):
                    with self.span("search model", "chat", 400, 60):
                        pass
            with self.span("writer", "invoke_agent", 200, 80):
                with self.span("writer model", "chat", 200, 80):
                    pass
        result = summarize_observed_spans(self.exporter.get_finished_spans())
        counts = {row["name"]: row["observed_direct"] for row in result["agents"]}
        self.assertEqual(counts, {
            "coordinator": [100, 20], "researcher": [300, 50],
            "web_search": [400, 60], "writer": [200, 80],
        })
        self.assertEqual([sum(v[i] for v in counts.values()) for i in (0, 1)], [1000, 210])
        self.assertFalse(result["global_complete"])

    def test_missing_usage_not_assumed_zero(self):
        with self.span("root", "invoke_agent"):
            with self.span("unreported model", "chat"):
                pass
        result = summarize_observed_spans(self.exporter.get_finished_spans())
        self.assertEqual(result["agents"][0]["observed_direct"], [0, 0])
        self.assertEqual(result["agents"][0]["usage_unknown_count"], 1)

    def test_unattributed_inference_is_not_assigned(self):
        with self.span("standalone", "chat", 7, 2):
            pass
        result = summarize_observed_spans(self.exporter.get_finished_spans())
        self.assertEqual(result["unattributed_observed"], [7, 2])
        self.assertEqual(result["agents"], [])

    def test_negative_usage_rejected(self):
        with self.span("root", "invoke_agent"):
            with self.span("invalid", "chat", -1, 2):
                pass
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            summarize_observed_spans(self.exporter.get_finished_spans())

    def test_missing_ancestor_remains_unattributed(self):
        with self.span("root", "invoke_agent"):
            with self.span("model", "chat", 5, 3):
                pass
        spans = [span for span in self.exporter.get_finished_spans()
                 if span.name == "model"]
        result = summarize_observed_spans(spans)
        self.assertEqual(result["unattributed_observed"], [5, 3])
        self.assertFalse(result["global_complete"])


if __name__ == "__main__":
    unittest.main()
