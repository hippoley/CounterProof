"""Synthetic tests: verify the reader's claim ceiling, not Goose runtime behavior."""
import copy
import unittest

from audit import audit


def span(sid='01', rid='request-1', inp=12, out=3):
    attrs = [('gen_ai.operation.name', 'chat'), ('gen_ai.request.id', rid),
             ('gen_ai.usage.input_tokens', inp), ('gen_ai.usage.output_tokens', out)]
    return {'traceId': 'abcd', 'spanId': sid,
            'attributes': [{'key': k, 'value': {'intValue' if isinstance(v, int) else 'stringValue': str(v)}}
                           for k, v in attrs if v is not None]}


def envelope(*spans):
    return {'resourceSpans': [{'scopeSpans': [{'spans': list(spans)}]}]}


class CoverageTest(unittest.TestCase):
    def test_observed_distinct_attempts_never_prove_retry_relation(self):
        r = audit(envelope(span(), span('02', 'request-2', 5, 2)))
        self.assertEqual(r['check_result'], 'PASS')
        self.assertEqual(r['retry_relation'], 'UNKNOWN')
        self.assertEqual(r['reported_totals'], {'input_tokens_observed': 17, 'output_tokens_observed': 5})

    def test_exact_reexport_is_not_charged_twice(self):
        r = audit(envelope(span(), copy.deepcopy(span())))
        self.assertEqual(r['check_result'], 'PASS')
        self.assertEqual(r['raw_chat_span_count'], 2)
        self.assertEqual(r['exact_reexports'], 1)
        self.assertEqual(r['reported_totals']['input_tokens_observed'], 12)

    def test_conflicting_same_span_identity_is_failure(self):
        r = audit(envelope(span(), span(inp=14)))
        self.assertEqual(r['check_result'], 'FAIL')
        self.assertIsNone(r['reported_totals'])

    def test_missing_request_id_is_unknown_not_assigned(self):
        r = audit(envelope(span(rid=None)))
        self.assertEqual(r['check_result'], 'UNRESOLVED')
        self.assertIsNone(r['attempts'][0]['request_id'])

    def test_missing_usage_is_not_zero(self):
        r = audit(envelope(span(out=None)))
        self.assertEqual(r['check_result'], 'UNRESOLVED')
        self.assertIsNone(r['reported_totals'])

    def test_repeated_request_id_across_distinct_spans_is_unknown(self):
        r = audit(envelope(span(), span('02')))
        self.assertEqual(r['check_result'], 'UNRESOLVED')
        self.assertIn('REQUEST_ID_MULTIPLE_SPANS', [x['code'] for x in r['issues']])

    def test_no_chat_span_is_not_pass(self):
        self.assertEqual(audit(envelope())['check_result'], 'UNRESOLVED')

    def test_negative_usage_invalid(self):
        self.assertEqual(audit(envelope(span(inp=-1)))['check_result'], 'UNRESOLVED')

    def test_malformed_root_fails_closed(self):
        self.assertEqual(audit([])['check_result'], 'FAIL')

    def test_malformed_scope_fails_closed(self):
        self.assertEqual(audit({'resourceSpans': [None]})['check_result'], 'FAIL')
        self.assertEqual(audit({'resourceSpans': [{'scopeSpans': [None]}]})['check_result'], 'FAIL')

    def test_malformed_span_fails_closed(self):
        self.assertEqual(audit(envelope(None))['check_result'], 'FAIL')

    def test_no_resource_spans(self):
        self.assertEqual(audit({})['check_result'], 'UNRESOLVED')


if __name__ == '__main__':
    unittest.main()
