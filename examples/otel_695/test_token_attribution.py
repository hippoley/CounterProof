import unittest
from token_attribution import Invocation, attributed, direct_sum, root_total_sum


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


if __name__ == '__main__':
    unittest.main()
