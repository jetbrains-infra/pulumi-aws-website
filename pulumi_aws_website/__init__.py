import json
from copy import deepcopy
from typing import Dict, List

import pulumi
from pulumi_aws import cloudfront
from pulumi_aws import route53
from pulumi_aws import s3

from pulumi_aws_website import config

DEFAULT_ORIGIN_ID = 'S3ContentDefault'


class WebSite(pulumi.ComponentResource):
    def __init__(self,
                 name: str,
                 stack: str,
                 issue: str,
                 zones: Dict[str, List[str]],
                 viewer_certificate: config.ViewerCertificate,
                 lambda_function_associations: [config.LambdaFunctionAssociation] = None,
                 logging_config: config.LoggingConfig = None,
                 additional_buckets_mapping: Dict[str, str] = None,
                 default_cache_behavior: config.CacheBehavior = None,
                 custom_error_responses: List[config.CustomErrorResponse] = None,
                 opts: pulumi.ResourceOptions = None):
        """
        Constructs a WebSite.
        :param stack: Stack name, prod or staging for example
        :param issue: Issue tracker ID
        :param additional_buckets_mapping: Map bucket to CloudFront origin path_pattern for example {"docs": "/docs/*"},
            cache behavior for additional origin will be copied from default_cache_behavior
        :param logging_config: CloudFrond S3 bucket for logging configuration
        :param zones: Map of zone_id: to domains names, for example {'12345ABCDE': ['example.com', 'www.example.com']}
            zone_id will use to create DNS alias to CloudFront Distribution
        :param default_cache_behavior: Default cache behavior configuration
        """
        super().__init__('WebSite', name, None, opts)
        self.name = name
        self.stack = stack
        self.issue = issue
        self.zones = zones
        self.logging_config = logging_config
        self.viewer_certificate = viewer_certificate
        self.tags = {
            'website': f'{self.name}-{self.stack}',
            'stack': self.stack,
            'issue': self.issue,
        }

        self.aliases = []
        for _, domains_list in self.zones.items():
            self.aliases += domains_list

        if default_cache_behavior is None:
            behavior = config.CacheBehavior()
            behavior.allowed_methods = ['GET', 'HEAD']
            behavior.cached_methods = ['GET', 'HEAD']
            behavior.compress = True
            behavior.forwarded_values_cookies = 'none'
            behavior.forwarded_values_headers = None
            behavior.forwarded_values_query_string = True
            behavior.path_pattern = None
            behavior.min_ttl = 0
            behavior.default_ttl = 3600
            behavior.max_ttl = 86400
            behavior.target_origin_id = DEFAULT_ORIGIN_ID
            behavior.viewer_protocol_policy = config.VIEWER_PROTOCOL_POLICY_REDIRECT_TO_HTTPS
            behavior.lambda_function_associations = []
            self.default_cache_behavior = behavior
        else:
            self.default_cache_behavior = default_cache_behavior

        if lambda_function_associations is None:
            self.lambda_function_associations = []
        else:
            self.lambda_function_associations = lambda_function_associations

        if custom_error_responses is None:
            self.custom_error_responses = []
        else:
            self.custom_error_responses = custom_error_responses

        oai = cloudfront.OriginAccessIdentity(
            f'website-{self.name}-{self.stack}-origin-access-identity',
            opts=pulumi.ResourceOptions(parent=self))

        self.default_bucket = self._create_bucket('default', oai)
        default_origin = config.Origin(
            domain_name=self.default_bucket.bucket_domain_name,
            origin_id=pulumi.Output.from_input(DEFAULT_ORIGIN_ID),
            s3_origin_access_identity=oai.cloudfront_access_identity_path
        )

        self.cache_behaviors = []
        self.origins = [default_origin]

        if additional_buckets_mapping is not None:
            for b, path in additional_buckets_mapping.items():
                bucket = self._create_bucket(b, oai)
                cb = deepcopy(self.default_cache_behavior)
                cb.lambda_function_associations = self.lambda_function_associations
                cb.path_pattern = path
                cb.target_origin_id = bucket.id
                self.cache_behaviors.append(cb)
                self.origins.append(config.Origin(
                    domain_name=bucket.bucket_domain_name,
                    origin_id=bucket.id,
                    s3_origin_access_identity=oai.cloudfront_access_identity_path)
                )

        self.default_cache_behavior.lambda_function_associations = self.lambda_function_associations
        self._create_cloudfront()
        record_aliases = [{
            'evaluateTargetHealth': False,
            'name': self.distribution.domain_name,
            'zone_id': self.distribution.hosted_zone_id,
            }]
        i = 0
        for zone_id, domains_list in self.zones.items():
            for name in domains_list:
                route53.Record(f'{name}-record-{i}',
                               zone_id=zone_id,
                               type='A',
                               name=name,
                               aliases=record_aliases,
                               opts=pulumi.ResourceOptions(parent=self))
                i += 1

    @staticmethod
    def _get_s3_policy(args):
        cf_iam_arn, bucket_iam_arn = args
        return json.dumps({
            "Version": "2012-10-17",
            "Id": "PolicyForCloudFrontPrivateContent",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": f"{cf_iam_arn}"
                    },
                    "Action": "s3:GetObject",
                    "Resource": f"{bucket_iam_arn}/*"
                },
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": f"{cf_iam_arn}"
                    },
                    "Action": "s3:ListBucket",
                    "Resource": f"{bucket_iam_arn}"
                }
            ]
        })

    def _create_bucket(self, name, origin_access_identity):
        bucket = s3.Bucket(f'website-{self.name}-{self.stack}-{name}', acl='private', tags=self.tags,
                           opts=pulumi.ResourceOptions(parent=self))
        s3.BucketPublicAccessBlock(f'website-{self.name}-{self.stack}-{name}',
                                   bucket=bucket.id,
                                   block_public_acls=True,
                                   block_public_policy=True,
                                   ignore_public_acls=True,
                                   restrict_public_buckets=True,
                                   opts=pulumi.ResourceOptions(parent=self))
        s3.BucketPolicy(f'website-{self.name}-{self.stack}-{name}-policy',
                        bucket=bucket.id,
                        policy=pulumi.Output.all(origin_access_identity.iam_arn, bucket.arn).apply(self._get_s3_policy),
                        opts=pulumi.ResourceOptions(parent=self))
        return bucket

    def _create_cloudfront(self):
        self.distribution = cloudfront.Distribution(f'website-{self.name}-{self.stack}',
                                                    aliases=self.aliases,
                                                    comment=f'website-{self.name}-{self.stack}',
                                                    default_cache_behavior=self.default_cache_behavior.to_dict(),
                                                    default_root_object="index.html",
                                                    enabled=True,
                                                    is_ipv6_enabled=True,
                                                    logging_config=self.logging_config,
                                                    ordered_cache_behaviors=list(map(lambda x: x.to_dict(),
                                                                                     self.cache_behaviors)),
                                                    origins=list(
                                                        map(lambda x: x.to_dict(), self.origins)),
                                                    tags=self.tags,
                                                    custom_error_responses=list(map(lambda x: x.to_dict(),
                                                                                    self.custom_error_responses)),
                                                    restrictions={
                                                        'geoRestriction': {
                                                            'restrictionType': 'none',
                                                        }
                                                    },
                                                    viewer_certificate=self.viewer_certificate.to_dict(),
                                                    opts=pulumi.ResourceOptions(parent=self))
