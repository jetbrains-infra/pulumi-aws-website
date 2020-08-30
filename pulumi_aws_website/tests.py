import unittest
from typing import Optional, Tuple, List

import pulumi

from website import WebSite
from website import config


class MyMocks(pulumi.runtime.Mocks):
    def new_resource(self,
                     type_: str,
                     name: str,
                     inputs: dict,
                     provider: Optional[str],
                     id_: Optional[str]) -> Tuple[str, dict]:
        if type_ == 'aws:acm/certificate:Certificate':
            state = {}
            return name + '_id', dict(inputs, **state)
        return name + '_id', inputs

    def call(self, token, args, provider):
        return {}


pulumi.runtime.set_mocks(MyMocks())

website = WebSite('test',
                  issue='sre-123',
                  stack='staging',
                  zones={
                      'ABCDEF123': ['test.jetbrains.com']
                  },
                  viewer_certificate=config.ViewerCertificate(cloudfront_default_certificate=True)
                  )


class TestingWithMocks(unittest.TestCase):
    @pulumi.runtime.test
    def test_check_tags(self):
        def check_tags(args: List[WebSite]):
            ws = args[0]
            self.assertEqual(ws.tags.get('website'), 'test-staging')
            self.assertEqual(ws.tags.get('stack'), 'staging')
            self.assertEqual(ws.tags.get('issue'), 'sre-123')

        return pulumi.Output.all(website).apply(check_tags)

    def test_check_aliases(self):
        def check_aliases(args: List[WebSite]):
            ws = args[0]
            self.assertEqual(ws.aliases, ['test.jetbrains.com'])

        return pulumi.Output.all(website).apply(check_aliases)

    def test_check_default_behavior(self):
        def check_defautl_behavior(args: List[WebSite]):
            ws = args[0]
            self.assertEqual(ws.default_cache_behavior.lambda_function_associations, [])
            self.assertEqual(ws.default_cache_behavior.allowed_methods, ['GET', 'HEAD'])
            self.assertEqual(ws.default_cache_behavior.cached_methods, ['GET', 'HEAD'])

        return pulumi.Output.all(website).apply(check_defautl_behavior)
