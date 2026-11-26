import unittest
from check_ai_updates import SOURCES, classify, covered, extract, review
from ai_rules import LIST, parse


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.stable = parse(LIST.read_bytes())

    def test_exact_and_suffix(self):
        self.assertTrue(covered(('DOMAIN','api.openai.com'),self.stable))
        self.assertTrue(covered(('DOMAIN-SUFFIX','api.openai.com'),self.stable))
        self.assertFalse(covered(('DOMAIN-SUFFIX','generativelanguage.googleapis.com'),self.stable))
        self.assertFalse(covered(('DOMAIN','notopenai.com'),self.stable))

    def test_risk(self):
        self.assertEqual(classify(('DOMAIN-SUFFIX','googleapis.com'),self.stable),'BLOCKED_SHARED_ROOT')
        self.assertEqual(classify(('DOMAIN-SUFFIX','generativelanguage.googleapis.com'),self.stable),'REVIEW_SCOPE_EXPANSION')
        self.assertEqual(classify(('DOMAIN','other.googleapis.com'),self.stable),'REVIEW_SHARED_OR_NEW_SERVICE')

    def test_sr(self):
        r,s=extract(b'DOMAIN,api.openai.com\nDOMAIN-KEYWORD,openai\nIP-CIDR,1.2.3.0/24,no-resolve\nDOMAIN,bad..com\n','sr')
        self.assertEqual(r,{('DOMAIN','api.openai.com')})
        self.assertEqual(s,3)

    def test_v2fly(self):
        r,s=extract(b'full:a.google.com\nfoo.com\ninclude:other\nregex:abc\n','v2fly')
        self.assertEqual(r,{('DOMAIN','a.google.com'),('DOMAIN-SUFFIX','foo.com')})
        self.assertEqual(s,2)

    def test_openrouter(self):
        r,_=extract(b'https://eu.openrouter.ai/api https://notopenrouter.ai https://openrouter.ai.evil.com','openrouter')
        self.assertEqual(r,{('DOMAIN','eu.openrouter.ai')})

    def test_empty_and_large(self):
        with self.assertRaises(ValueError): extract(b'<html>error</html>','sr')
        with self.assertRaises(ValueError): extract('\n'.join(f'DOMAIN,h{i}.example.com' for i in range(501)).encode(),'sr')

    def test_success_and_failure_no_mutation(self):
        before=LIST.read_bytes()
        def fixture(url):
            fmt=next(fmt for u,fmt in SOURCES.values() if u==url)
            return {'sr':b'DOMAIN,api.openai.com\nDOMAIN-SUFFIX,googleapis.com', 'v2fly':b'full:new.googleapis.com', 'openrouter':b'https://openrouter.ai/api'}[fmt]
        result,failed=review(fixture)
        self.assertFalse(failed)
        self.assertIn('BLOCKED_SHARED_ROOT',result)
        self.assertIn('REVIEW_SHARED_OR_NEW_SERVICE',result)
        def broken(url):
            if 'Gemini.list' in url: raise OSError('test failure')
            return fixture(url)
        result,failed=review(broken)
        self.assertTrue(failed)
        self.assertIn('INCOMPLETE',result)
        self.assertEqual(before,LIST.read_bytes())


if __name__ == '__main__': unittest.main()
