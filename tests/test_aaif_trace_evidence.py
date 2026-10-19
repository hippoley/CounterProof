"""Offline, stdlib-only checks against Foreman source-derived projection and mutations."""
from __future__ import annotations

import copy
import contextlib
import io
import importlib.util
import hashlib
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SCRIPT = HERE / "examples" / "aaif_trace_evidence" / "reader.py"
FIXTURE = SCRIPT.with_name("foreman-projection.json")
RAW = SCRIPT.with_name("foreman-web-worker-raw.ndjson")
spec = importlib.util.spec_from_file_location("aaif_evidence_reader", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def rows():
    return copy.deepcopy(json.loads(FIXTURE.read_text())["projection"])


def result_by_verdict(r, value):
    return [v for v in r["results"] if v["verdict"] == value]


def outcome(row):
    return row["events"][0]["attrs"][mod.OUTCOME]


class TraceEvidenceTests(unittest.TestCase):
    def test_pinned_source_counts_and_projection(self):
        data = json.loads(FIXTURE.read_text())
        self.assertEqual(data["git_blob_sha"], "2541dc0f58d34bc113ad2064da9510e444b24504")
        self.assertEqual(data["source_counts"], {"otlp_http_envelopes": 6, "spans": 9, "decision_events": 4})
        self.assertEqual(len(data["projection"]), 7)

    def test_baseline_two_outcomes_and_two_unrelated_tool_calls(self):
        r = mod.inspect(rows())
        self.assertFalse(r["invalid_inputs"])
        self.assertEqual(len(result_by_verdict(r, "CORRELATED_ALLOW_EXECUTION")), 1)
        self.assertEqual(len(result_by_verdict(r, "CORRELATED_DENY_NO_OBSERVED_EXECUTION")), 1)
        self.assertEqual(len(result_by_verdict(r, "UNCONFIRMED")), 2)
        self.assertEqual(len(r["results"]), 4)
        self.assertEqual(sum(v["observed_execution_spans"] for v in r["results"]), 3)
        self.assertEqual(sum(len(v["decisions"]) for v in r["results"]), 4)
        self.assertTrue(all(v["physical_effect"] == "UNKNOWN" for v in r["results"]))
        self.assertTrue(all(v["enforcement_proven"] is False for v in r["results"]))

    def test_decision_and_execution_cross_process_and_trace(self):
        r = mod.inspect(rows())
        allowed = result_by_verdict(r, "CORRELATED_ALLOW_EXECUTION")[0]
        self.assertEqual(allowed["decisions"], ["require_approval", "allow"])
        self.assertEqual(allowed["observed_services"], ["foreman-web", "foreman-worker"])
        self.assertEqual(len(allowed["observed_trace_ids"]), 3)
        denied = result_by_verdict(r, "CORRELATED_DENY_NO_OBSERVED_EXECUTION")[0]
        self.assertEqual(denied["decisions"], ["require_approval", "deny"])
        self.assertEqual(denied["observed_execution_spans"], 0)

    def test_arrival_order_does_not_change_answers(self):
        source = rows()
        baseline = mod.inspect(source)
        for seed in range(15):
            permutation = copy.deepcopy(source)
            random.Random(seed).shuffle(permutation)
            self.assertEqual(mod.inspect(permutation)["results"], baseline["results"])

    def test_exact_duplicate_delivery_does_not_increase_span_count(self):
        source = rows()
        answer = mod.inspect(source)
        self.assertEqual(mod.inspect(source + copy.deepcopy(source)), answer)

    def test_same_span_id_with_changed_contents_is_rejected(self):
        source = rows()
        conflicting = copy.deepcopy(source[3]); conflicting["call"] = "different-call"
        r = mod.inspect(source + [conflicting])
        self.assertIn("same span identity has inconsistent records", r["invalid_inputs"])

    def test_real_extra_execute_span_is_not_deduplicated(self):
        source = rows()
        extra = copy.deepcopy(source[3]); extra["span"] = "1234567890abcdef"
        r = mod.inspect(source + [extra])
        self.assertEqual(len(result_by_verdict(r, "CONTRADICTED")), 1)
        self.assertEqual(result_by_verdict(r, "CONTRADICTED")[0]["observed_execution_spans"], 2)

    def test_deny_with_execute_span_is_contradiction(self):
        source = rows()
        extra = copy.deepcopy(source[3])
        denied = source[6]["events"][0]["attrs"]
        extra["execution"] = denied[mod.EXECUTION]
        extra["call"] = denied[mod.CALL]
        extra["trace"] = "00000000000000000000000000000001"
        extra["span"] = "0000000000000001"
        r = mod.inspect(source + [extra])
        self.assertEqual(len(result_by_verdict(r, "CONTRADICTED")), 1)
        self.assertIn("execution span despite observed deny", result_by_verdict(r, "CONTRADICTED")[0]["reasons"])

    def test_missing_allow_does_not_upgrade_proposal_to_approval(self):
        source = [row for row in rows() if not (row["events"] and outcome(row) == "allow")]
        r = mod.inspect(source)
        self.assertFalse(result_by_verdict(r, "CORRELATED_ALLOW_EXECUTION"))
        self.assertEqual(len(result_by_verdict(r, "UNCONFIRMED")), 3)

    def test_missing_execute_span_does_not_prove_non_execution(self):
        source = [row for row in rows() if row["name"] != "execute_tool send_notification"]
        r = mod.inspect(source)
        self.assertFalse(result_by_verdict(r, "CORRELATED_ALLOW_EXECUTION"))
        self.assertEqual(len(result_by_verdict(r, "UNCONFIRMED")), 3)

    def test_tool_call_id_collision_different_execution_no_cross_join(self):
        source = rows()
        # Same call id reused in another run must remain distinct by execution ID.
        source[6]["events"][0]["attrs"][mod.CALL] = source[2]["call"]
        source[6]["call"] = source[2]["call"]
        source[5]["events"][0]["attrs"][mod.CALL] = source[2]["call"]
        r = mod.inspect(source)
        self.assertEqual(len(result_by_verdict(r, "CORRELATED_ALLOW_EXECUTION")), 1)
        self.assertEqual(len(result_by_verdict(r, "CORRELATED_DENY_NO_OBSERVED_EXECUTION")), 1)

    def test_same_call_different_tool_name_is_contradiction(self):
        source = rows()
        source[2]["events"][0]["attrs"][mod.TOOL] = "delete_dataset"
        r = mod.inspect(source)
        self.assertEqual(len(result_by_verdict(r, "CONTRADICTED")), 1)
        self.assertIn("tool name disagreement", result_by_verdict(r, "CONTRADICTED")[0]["reasons"])

    def test_conflicting_terminal_decision_is_contradiction(self):
        source = rows()
        extra = copy.deepcopy(source[2]); extra["trace"] = "othertrace";extra["span"] = "otherspan"
        extra["events"][0]["attrs"][mod.OUTCOME] = "deny"
        r = mod.inspect(source + [extra])
        self.assertIn("contradictory terminal decisions", result_by_verdict(r, "CONTRADICTED")[0]["reasons"])

    def test_missing_id_is_invalid_not_globally_correlated(self):
        source = rows()
        source[2]["events"][0]["attrs"][mod.CALL] = None
        r = mod.inspect(source)
        self.assertIn("decision missing execution/call id", r["invalid_inputs"])
        self.assertFalse(result_by_verdict(r, "CORRELATED_ALLOW_EXECUTION"))

    def test_decision_enclosing_span_mismatch_is_invalid(self):
        source = rows()
        source[2]["events"][0]["attrs"][mod.EXECUTION] = "some-other-run"
        r = mod.inspect(source)
        self.assertIn("decision execution id contradicts enclosing span", r["invalid_inputs"])

    def test_unsupported_outcome_cannot_be_silently_accepted(self):
        source = rows();source[2]["events"][0]["attrs"][mod.OUTCOME] = "expired"
        r = mod.inspect(source)
        self.assertTrue(r["invalid_inputs"])
        self.assertFalse(result_by_verdict(r, "CORRELATED_ALLOW_EXECUTION"))

    def test_otlp_decoder_roundtrip_through_minimal_sample(self):
        p = rows()[2]
        def attributes(d):
            return [{"key": key, "value": {"stringValue": str(val)}} for key, val in d.items()]
        doc = {"resourceSpans": [{"resource": {"attributes": attributes({"service.name":p["service"]})},
                                   "scopeSpans": [{"spans": [{"traceId":p["trace"],"spanId":p["span"],
                                       "name":p["name"],
                                       "attributes":attributes({mod.CALL:p["call"],mod.EXECUTION:p["execution"]}),
                                       "events":[{"name":mod.DECISION,"timeUnixNano":p["events"][0]["t"],
                                                  "attributes":attributes(p["events"][0]["attrs"])}]}]}]}]}
        projected = mod.project_otlp([{"body":doc}])
        self.assertEqual(projected[0]["events"][0]["attrs"][mod.OUTCOME], "allow")
        self.assertEqual(projected[0]["call"], p["call"])


    def test_approval_identity_mismatch_cannot_claim_correlation(self):
        source = rows()
        source[2]["events"][0]["attrs"][mod.APPROVAL] = "different-approval"
        answer = mod.inspect(source)
        contradicted = result_by_verdict(answer, "CONTRADICTED")
        self.assertEqual(len(contradicted), 1)
        self.assertIn("approval id disagreement", contradicted[0]["reasons"])

    def test_absent_approval_id_is_not_treated_as_verified_correlation(self):
        source = rows()
        del source[2]["events"][0]["attrs"][mod.APPROVAL]
        answer = mod.inspect(source)
        self.assertFalse(result_by_verdict(answer, "CORRELATED_ALLOW_EXECUTION"))
        self.assertIn("approval id missing", result_by_verdict(answer, "CONTRADICTED")[0]["reasons"])

    def test_missing_decision_tool_is_not_silently_accepted(self):
        source = rows()
        del source[2]["events"][0]["attrs"][mod.TOOL]
        answer = mod.inspect(source)
        self.assertFalse(result_by_verdict(answer, "CORRELATED_ALLOW_EXECUTION"))
        self.assertIn("decision tool name missing", result_by_verdict(answer, "CONTRADICTED")[0]["reasons"])

    def test_clock_inversion_downgrades_instead_of_proving_enforcement(self):
        source = rows()
        source[3]["start_ns"] = str(int(source[2]["events"][0]["t"]) - 1)
        answer = mod.inspect(source)
        self.assertFalse(result_by_verdict(answer, "CORRELATED_ALLOW_EXECUTION"))
        uncertain = [r for r in answer["results"] if r["clock_order_uncertain"]]
        self.assertEqual(len(uncertain), 1)
        self.assertEqual(uncertain[0]["verdict"], "UNCONFIRMED")
        self.assertFalse(uncertain[0]["enforcement_proven"])

    def test_late_pending_event_downgrades_not_a_protocol_violation(self):
        source = rows()
        source[1]["events"][0]["t"] = str(int(source[2]["events"][0]["t"]) + 1)
        result = mod.inspect(source)
        self.assertEqual(len([r for r in result["results"] if r["clock_order_uncertain"]]), 1)
        self.assertFalse(result_by_verdict(result, "CORRELATED_ALLOW_EXECUTION"))

    def test_same_timestamp_same_outcome_different_call_is_not_deduped(self):
        source = rows()
        extra = copy.deepcopy(source[1]["events"][0])
        extra["attrs"][mod.CALL] = "another-proposed-call"
        extra["attrs"][mod.APPROVAL] = "another-approval-id"
        source[1]["events"].append(extra)
        r = mod.inspect(source)
        self.assertEqual(len(r["results"]), 5)
        self.assertEqual(len(result_by_verdict(r, "CORRELATED_ALLOW_EXECUTION")), 1)
        self.assertEqual(len(result_by_verdict(r, "UNCONFIRMED")), 3)

    def test_same_timestamp_same_outcome_changed_approval_is_contradicted(self):
        source = rows()
        extra = copy.deepcopy(source[1]["events"][0])
        extra["attrs"][mod.APPROVAL] = "wrong-approval-id"
        source[1]["events"].append(extra)
        # Distinct event with same parent and timestamp is never silently dropped.
        r = mod.inspect(source)
        bad = result_by_verdict(r, "CONTRADICTED")
        self.assertEqual(len(bad), 1)
        self.assertIn("approval id disagreement", bad[0]["reasons"])

    def test_raw_otlp_envelope_from_projection_is_replayable(self):
        # Synthetic shape test; it does NOT stand in for the original captured NDJSON.
        def arr(d):
            return [{"key": key, "value": {"stringValue": str(v)}}
                    for key, v in d.items() if v is not None]
        docs = []
        for row in rows():
            attrs = {mod.EXECUTION: row["execution"], mod.CALL: row["call"],
                     "gen_ai.operation.name": row["operation"]}
            raw = {"body": {"resourceSpans": [{
                "resource": {"attributes": arr({"service.name": row["service"]})},
                "scopeSpans": [{"spans": [{
                    "name": row["name"], "traceId": row["trace"],
                    "spanId": row["span"], "startTimeUnixNano": row["start_ns"],
                    "attributes": arr(attrs),
                    "events": [{"name": ev["name"], "timeUnixNano": ev["t"],
                                "attributes": arr(ev["attrs"])} for ev in row["events"]]
                }]}]}]}}
            docs.append(raw)
        self.assertEqual(mod.inspect(mod.project_otlp(docs))["results"], mod.inspect(rows())["results"])
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "sample.ndjson"
            src.write_text("\n".join(json.dumps(doc) for doc in docs) + "\n")
            self.assertEqual(mod.inspect(mod.load_rows(src))["results"], mod.inspect(rows())["results"])
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(mod.main([str(src), "--verify-foreman-blob"]), 2)

    def test_malformed_raw_envelope_is_not_silently_dropped(self):
        with self.assertRaisesRegex(ValueError, "missing resourceSpans"):
            mod.project_otlp([{"body": {"unrelated": []}}])

    def test_incomplete_approval_emits_nonzero_exit_for_review(self):
        source = rows()
        source = [row for row in source if not (row["events"] and outcome(row) == "allow")]
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "incomplete.json"
            src.write_text(json.dumps({"projection": source}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(mod.main([str(src)]), 1)

    def test_git_blob_digest_matches_git_hash_contract(self):
        data = b"sample raw source\n"
        digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        self.assertNotEqual(digest, mod.SOURCE_BLOB_SHA)
        self.assertEqual(mod.SOURCE_BLOB_SHA, json.loads(FIXTURE.read_text())["git_blob_sha"])

    @unittest.skipUnless(RAW.exists(), "raw upstream capture unavailable locally (pinned file committed to GitHub branch)")
    def test_exact_raw_capture_replay_and_source_digest(self):
        contents = RAW.read_bytes()
        self.assertEqual(hashlib.sha1(b"blob " + str(len(contents)).encode() + b"\0" + contents).hexdigest(), mod.SOURCE_BLOB_SHA)
        docs = [json.loads(line) for line in contents.decode().splitlines() if line.strip()]
        self.assertEqual(len(docs), 6)
        self.assertEqual(mod.project_otlp(docs), rows())
        result = mod.inspect(mod.load_rows(RAW))
        self.assertFalse(result["invalid_inputs"])
        self.assertEqual(len(result_by_verdict(result, "CORRELATED_ALLOW_EXECUTION")), 1)
        self.assertEqual(len(result_by_verdict(result, "CORRELATED_DENY_NO_OBSERVED_EXECUTION")), 1)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mod.main([str(RAW), "--verify-foreman-blob"]), 0)

    def test_cli_exit_codes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mod.main([str(FIXTURE)]), 0)
        with tempfile.TemporaryDirectory() as tmp:
            bad=Path(tmp)/"bad.json"
            d=json.loads(FIXTURE.read_text())
            d["projection"][6]["events"][0]["attrs"][mod.OUTCOME] = "expired"
            bad.write_text(json.dumps(d),encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(mod.main([str(bad)]),1)
                self.assertEqual(mod.main([str(Path(tmp)/"not-exist.json")]),2)


if __name__ == "__main__":
    unittest.main()