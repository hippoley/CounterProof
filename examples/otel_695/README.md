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

Thirteen deterministic standard-library tests cover this accounting, duplicate IDs, orphans, cycles, negative token counts, nested unknown-usage propagation and mixed-completeness root aggregation. The fixture now runs in the repository pull-request CI matrix on Python 3.10–3.12; local test counts are not a claim that GitHub checks have passed. No real agent traces, SDK metrics, real billing or remote child receipts are involved. No test proves a proposed metrics schema is correct in real deployments.

A consumer can call `root_total_bounds(rows)` to receive the **observed known lower bound** (`known_total`), a `complete` flag, and the number of locally observed roots. For example, a locally observed 100/10 root with an unreported remote child yields `known_total=(100, 10)` and `complete=False`, **not** an asserted 100/10 request total. `root_total_sum(rows)` still refuses incomplete results. These are local forest semantics; even `complete=True` does not establish global completeness across processes or missing traces.

## OpenTelemetry SDK-generated span probe

The separately gated `sdk_probe/` tests exercise actual `ReadableSpan` objects
generated with the **OpenTelemetry Python SDK** and its in-memory exporter.
No GenAI provider, remote agent, external collector, production workload or
exported production trace is involved.

```bash
python -m pip install 'opentelemetry-sdk>=1.30,<2'
python -m unittest discover -s examples/otel_695/sdk_probe -p 'test_*.py' -v
```

The consumer probe attributes observed inference spans to their nearest visible
agent ancestor in the same trace. It **does not add agent-span usage attributes**
to inference usage, because agent usage may already be inclusive. Missing
inference usage remains unknown, missing ancestors leave consumption
unattributed, and `global_complete` is always false because an observed
SDK span set cannot establish complete collection in the presence of sampling,
cross-process calls or dropped telemetry.

These SDK spans are real library-generated telemetry, but their token values
and agent topology are intentionally constructed test inputs, **not** live
provider-measured usage. No proposed OTel metric naming or production behavior
is validated.

Three open questions: (1) How would consumers distinguish *complete* inclusive totals from *known lower bounds* in the presence of missing remote usage? (2) How should a top-level filter behave if a root is only local to a process? (3) What is the recommended dashboard guidance to prevent nested inclusive-histogram double counting after sampling?
