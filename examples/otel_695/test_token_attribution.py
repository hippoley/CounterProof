import unittest
from token_attribution import Invocation, attributed, direct_sum, root_total_bounds, root_total_sum


class AttributionTests(unittest.TestCase):
    def example(self):
        return attributed([
            Invocation('coordinator', None, 100, 20),
            Invocation('researcher', 'coordinator', 300, 50),
            Invocation('web_search', 'researcher', 400, 60),
            Invocation('writer', 'coordinator', 200, 80),
        ])

    def test_issue_695_example(self):
        r = self.example()
        self.assertEqual(r['coordinator']['known_total'], (1000, 210))
        self.assertEqual(r['researcher']['known_total'], (700, 110))
        self.assertEqual(direct_sum(r), (1000, 210))
        self.assertEqual(root_total_sum(r), (1000, 210))

    def test_naive_total_double_counts(self):
        r = self.example()
        self.assertEqual(sum(x['known_total'][0] for x in r.values()), 2300)
        self.assertNotEqual(2300, direct_sum(r)[0])

    def test_remote_missing_usage_must_remain_unknown(self):
        r = attributed([Invocation('coordinator', None, 100, 20),
                        Invocation('remote_handoff', 'coordinator', 0, 0, True)])
        self.assertFalse(r['coordinator']['total_complete'])
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            root_total_sum(r)

    def test_multi_root_sum(self):
        r = attributed([Invocation('a', None, 3, 2), Invocation('b', None, 4, 1)])
        self.assertEqual(root_total_sum(r), (7, 3))

    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            attributed([Invocation('x', None, 0, 0), Invocation('x', None, 0, 0)])

    def test_orphan_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unknown parent'):
            attributed([Invocation('x', 'missing', 0, 0)])

    def test_cycle_rejected(self):
        with self.assertRaisesRegex(ValueError, 'cycle'):
            attributed([Invocation('a', 'b', 0, 0), Invocation('b', 'a', 0, 0)])

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            Invocation('x', None, -1, 0)


    def test_nested_remote_gap_propagates_to_all_ancestors(self):
        r = attributed([
            Invocation('root', None, 10, 1),
            Invocation('middle', 'root', 20, 2),
            Invocation('leaf', 'middle', 0, 0, True),
        ])
        self.assertEqual(r['root']['known_total'], (30, 3))
        self.assertFalse(r['leaf']['total_complete'])
        self.assertFalse(r['middle']['total_complete'])
        self.assertFalse(r['root']['total_complete'])
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            root_total_sum(r)

    def test_one_incomplete_root_invalidates_combined_root_total(self):
        r = attributed([
            Invocation('complete', None, 7, 2),
            Invocation('incomplete', None, 3, 1, True),
        ])
        self.assertTrue(r['complete']['total_complete'])
        self.assertFalse(r['incomplete']['total_complete'])
        self.assertEqual(direct_sum(r), (10, 3))
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            root_total_sum(r)

    def test_root_bounds_complete_example(self):
        bounds = root_total_bounds(self.example())
        self.assertEqual(bounds, {
            'known_total': (1000, 210),
            'complete': True,
            'root_count': 1,
        })

    def test_remote_unknown_reports_lower_bound_without_claiming_zero(self):
        rows = attributed([
            Invocation('root', None, 100, 10),
            Invocation('remote', 'root', 0, 0, True),
        ])
        self.assertEqual(root_total_bounds(rows), {
            'known_total': (100, 10),
            'complete': False,
            'root_count': 1,
        })

    def test_mixed_roots_have_known_lower_bound_but_not_authoritative_total(self):
        rows = attributed([
            Invocation('a', None, 7, 2),
            Invocation('b', None, 3, 1, True),
        ])
        self.assertEqual(root_total_bounds(rows), {
            'known_total': (10, 3),
            'complete': False,
            'root_count': 2,
        })
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            root_total_sum(rows)

if __name__ == '__main__':
    unittest.main()
