import unittest
from validate_ai_pr import check

BASE = b'DOMAIN-SUFFIX,example.com\nDOMAIN,api.example.net\n'


class ProposalTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(check(BASE, BASE + b'DOMAIN,new.example.net\n'), [('DOMAIN', 'new.example.net')])

    def test_comment_only(self):
        self.assertEqual(check(BASE, BASE + b'# comment\n'), [])

    def test_remove_or_reorder(self):
        for candidate in (b'DOMAIN,api.example.net\n', b'DOMAIN,api.example.net\nDOMAIN-SUFFIX,example.com\n'):
            with self.assertRaises(ValueError):
                check(BASE, candidate)

    def test_shared_or_duplicate(self):
        for added in (b'DOMAIN-SUFFIX,googleapis.com\n', b'DOMAIN,x.example.com\n', b'DOMAIN-SUFFIX,api.example.net\n'):
            with self.assertRaises(ValueError):
                check(BASE, BASE + added)
