import unittest
from typing import Optional, Tuple

from pulumi_aws_website import *


class MyMocks(pulumi.runtime.Mocks):
    def new_resource(self,
                     type_: str,
                     name: str,
                     inputs: dict,
                     provider: Optional[str],
                     id_: Optional[str]) -> Tuple[str, dict]:
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

    @pulumi.runtime.test
    def test_check_aliases(self):
        def check_aliases(args: List[WebSite]):
            ws = args[0]
            self.assertEqual(ws.aliases, ['test.jetbrains.com'])

        return pulumi.Output.all(website).apply(check_aliases)

    @pulumi.runtime.test
    def test_check_default_behavior(self):
        def check_default_behavior(args: List[WebSite]):
            ws = args[0]
            self.assertEqual(ws.default_cache_behavior.lambda_function_associations, [])
            self.assertEqual(ws.default_cache_behavior.allowed_methods, ['GET', 'HEAD'])
            self.assertEqual(ws.default_cache_behavior.cached_methods, ['GET', 'HEAD'])
            self.assertEqual(ws.default_cache_behavior.forwarded_values_cookies, 'none')
            self.assertEqual(ws.default_cache_behavior.forwarded_values_headers, None)
            self.assertEqual(ws.default_cache_behavior.forwarded_values_query_string, True)
            self.assertEqual(ws.default_cache_behavior.path_pattern, None)
            self.assertEqual(ws.default_cache_behavior.min_ttl, 0)
            self.assertEqual(ws.default_cache_behavior.default_ttl, 3600)
            self.assertEqual(ws.default_cache_behavior.max_ttl, 86400)
            self.assertEqual(ws.default_cache_behavior.target_origin_id, DEFAULT_ORIGIN_ID)
            self.assertEqual(ws.default_cache_behavior.viewer_protocol_policy,
                             config.VIEWER_PROTOCOL_POLICY_REDIRECT_TO_HTTPS)
            self.assertEqual(ws.default_cache_behavior.lambda_function_associations, [])
            self.assertTrue(ws.default_cache_behavior.compress)

        return pulumi.Output.all(website).apply(check_default_behavior)
