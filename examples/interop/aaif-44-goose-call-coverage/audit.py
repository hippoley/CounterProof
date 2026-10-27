#!/usr/bin/env python3
"""Experimental OTLP/JSON chat-attempt coverage reader; not an AAIF standard."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def attributes(items: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('key'), str):
            continue
        value = item.get('value')
        if isinstance(value, dict):
            for key in ('stringValue', 'intValue', 'boolValue', 'doubleValue'):
                if key in value:
                    value = value[key]
                    break
        result[item['key']] = value
    return result


def as_token_count(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def audit(document: dict[str, Any]) -> dict[str, Any]:
    problems: list[dict[str, str]] = []
    unique: dict[tuple[str, str], str] = {}
    observed: list[dict[str, Any]] = []
    raw_count = 0
    reexports = 0

    resources = document.get('resourceSpans')
    if not isinstance(resources, list):
        return {'check_result': 'UNRESOLVED', 'issues': [{'code': 'NO_RESOURCE_SPANS'}],
                'attempts': [], 'retry_relation': 'UNKNOWN', 'reported_totals': None}

    for resource in resources:
        for scope in resource.get('scopeSpans', []) or []:
            for span in scope.get('spans', []) or []:
                attrs = attributes(span.get('attributes'))
                if attrs.get('gen_ai.operation.name') != 'chat':
                    continue
                raw_count += 1
                trace_id, span_id = span.get('traceId'), span.get('spanId')
                if not isinstance(trace_id, str) or not trace_id or not isinstance(span_id, str) or not span_id:
                    problems.append({'code': 'MISSING_SPAN_ID', 'detail': str(raw_count)})
                else:
                    identity = (trace_id, span_id)
                    fingerprint = json.dumps(span, sort_keys=True, separators=(',', ':'))
                    if identity in unique:
                        if unique[identity] != fingerprint:
                            problems.append({'code': 'CONFLICTING_REEXPORT', 'detail': ':'.join(identity)})
                        else:
                            reexports += 1
                        continue
                    unique[identity] = fingerprint
                rid = attrs.get('gen_ai.request.id')
                if not isinstance(rid, str) or not rid:
                    problems.append({'code': 'REQUEST_ID_UNOBSERVED', 'detail': str(raw_count)})
                    rid = None
                inp = as_token_count(attrs.get('gen_ai.usage.input_tokens'))
                out = as_token_count(attrs.get('gen_ai.usage.output_tokens'))
                if inp is None or out is None:
                    problems.append({'code': 'USAGE_INCOMPLETE_OR_INVALID', 'detail': str(raw_count)})
                observed.append({'trace_id': trace_id, 'span_id': span_id, 'request_id': rid,
                                 'input_tokens': inp, 'output_tokens': out})

    if not observed:
        problems.append({'code': 'NO_CHAT_SPAN', 'detail': 'no exported model-call evidence'})
    request_ids = Counter(x['request_id'] for x in observed if x['request_id'] is not None)
    for rid, count in request_ids.items():
        if count > 1:
            problems.append({'code': 'REQUEST_ID_MULTIPLE_SPANS', 'detail': rid})
    conflict = any(x['code'] == 'CONFLICTING_REEXPORT' for x in problems)
    result = 'FAIL' if conflict else 'UNRESOLVED' if problems else 'PASS'
    totals = None
    if result == 'PASS':
        totals = {'input_tokens_observed': sum(x['input_tokens'] for x in observed),
                  'output_tokens_observed': sum(x['output_tokens'] for x in observed)}
    return {
        'check_result': result,
        'scope': 'exported_chat_spans_only',
        'retry_relation': 'UNKNOWN',
        'hidden_retry_coverage': 'UNKNOWN',
        'billing_accuracy': 'NOT_ESTABLISHED',
        'raw_chat_span_count': raw_count,
        'deduplicated_chat_span_count': len(observed),
        'exact_reexports': reexports,
        'reported_totals': totals,
        'attempts': observed,
        'issues': problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('otlp_json', type=Path)
    args = parser.parse_args()
    try:
        result = audit(json.loads(args.otlp_json.read_text(encoding='utf-8')))
    except (ValueError, OSError) as exc:
        print(json.dumps({'check_result': 'FAIL', 'issues': [{'code': 'INPUT_ERROR', 'detail': str(exc)}]}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result['check_result'] == 'FAIL' else 0 if result['check_result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
