# OTel GenAI #695: a reproducible attribution counterexample

A tiny, **synthetic**, standard-library-only proof fixture for the accounting questions in [OpenTelemetry GenAI #695](https://github.com/open-telemetry/semantic-conventions-genai/issues/695). It is an independent example, **not** a CounterProof core feature, production telemetry or a normative semantic convention.

```bash
cd examples/otel_695
python -m unittest discover -v
```

The issue's four-agent example yields:

| Invocation | Direct input/output | Inclusive input/output |
| --- | --- | --- |
| coordinator | 100 / 20 | 1000 / 210 |
| researcher | 300 / 50 | 700 / 110 |
| web_search | 400 / 60 | 400 / 60 |
| writer | 200 / 80 | 200 / 80 |

Direct usage summed across invocation nodes = **1000/210**; inclusive usage aggregated only at the root = **1000/210**; incorrectly summing inclusive input at *every* node = **2300**. When a remote child does not report usage, the synthetic oracle marks its root total incomplete rather than treating unknown consumption as zero.

Eight local deterministic tests verify this accounting and reject duplicate IDs, orphans, cycles and negative token counts. No real agent traces, SDK metrics, real billing or remote child receipts are involved. No test proves a proposed metrics schema is correct in real deployments.

Three open questions: (1) How would consumers distinguish *complete* inclusive totals from *known lower bounds* in the presence of missing remote usage? (2) How should a top-level filter behave if a root is only local to a process? (3) What is the recommended dashboard guidance to prevent nested inclusive-histogram double counting after sampling?
