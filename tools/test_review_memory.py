import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from check_ai_updates import SOURCES, review
from review_memory import load, disposition

RULE = ('DOMAIN', 'new.googleapis.com')
RISK = 'REVIEW_SHARED_OR_NEW_SERVICE'
TODAY = date(2026, 11, 26)
NAMES = ['Gemini v2fly']
ROW = dict(condition=','.join(RULE), decision='deferred', risk=RISK,
           sources=NAMES, review_until='2027-01-01', reason='Await device evidence')


def encoded(*rows):
    return json.dumps(rows).encode()


class MemoryTests(unittest.TestCase):
    def test_unreviewed_and_blocked(self):
        self.assertEqual(disposition(RULE, RISK, NAMES, {}, TODAY), 'UNREVIEWED')
        self.assertEqual(disposition(RULE, 'BLOCKED_SHARED_ROOT', NAMES, {}, TODAY), 'BLOCKED')

    def test_remember_and_reopen(self):
        decisions = load(encoded(ROW), SOURCES)
        self.assertEqual(disposition(RULE, RISK, NAMES, decisions, TODAY), 'DEFERRED')
        self.assertEqual(disposition(RULE, RISK, NAMES, decisions, date(2027,1,1)), 'REOPENED_EXPIRED')
        self.assertEqual(disposition(RULE, RISK, NAMES + ['Gemini community'], decisions, TODAY), 'REOPENED_CHANGED')
        self.assertEqual(disposition(RULE, 'REVIEW_AI_NAMESPACE', NAMES, decisions, TODAY), 'REOPENED_CHANGED')
        self.assertEqual(disposition(RULE, RISK, NAMES, decisions, TODAY, True), 'REOPENED_INCOMPLETE')
        self.assertEqual(disposition(('DOMAIN-SUFFIX', RULE[1]), RISK, NAMES, decisions, TODAY), 'UNREVIEWED')
        rejected = load(encoded(dict(ROW, decision='rejected')), SOURCES)
        self.assertEqual(disposition(RULE, RISK, NAMES, rejected, TODAY), 'REJECTED')

    def test_invalid_records(self):
        for row in (dict(ROW, decision='approved'), dict(ROW, review_until='bad'),
                    dict(ROW, sources=['unknown']), dict(ROW, reason=' '),
                    dict(ROW, condition='DOMAIN-KEYWORD,google'), dict(ROW, risk='BLOCKED_SHARED_ROOT')):
            with self.subTest(row=row), self.assertRaises(ValueError):
                load(encoded(row), SOURCES)
        with self.assertRaises(ValueError):
            load(encoded(ROW, ROW), SOURCES)
        with self.assertRaises(ValueError):
            load(b'[{"condition":"a","condition":"b"}]', SOURCES)

    def test_report_integration(self):
        def fixture(url):
            fmt = next(fmt for u, fmt in SOURCES.values() if u == url)
            return {'sr': b'DOMAIN-SUFFIX,googleapis.com', 'v2fly': b'full:new.googleapis.com',
                    'openrouter': b'https://openrouter.ai/api'}[fmt]
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / 'memory.json'
            ledger.write_bytes(encoded(ROW))
            before = ledger.read_bytes()
            text, failed = review(fixture, ledger, TODAY)
            self.assertFalse(failed)
            self.assertIn('Actionable: 0; remembered: 1; blocked: 1.', text)
            self.assertIn('DEFERRED', text)
            self.assertIn('BLOCKED_SHARED_ROOT', text)
            def broken(url):
                if 'Claude.list' in url:
                    raise OSError('fixture')
                return fixture(url)
            text, failed = review(broken, ledger, TODAY)
            self.assertTrue(failed)
            self.assertIn('REOPENED_INCOMPLETE', text)
            self.assertIn('Actionable: 1; remembered: 0; blocked: 1.', text)
            self.assertEqual(before, ledger.read_bytes())


if __name__ == '__main__': unittest.main()
