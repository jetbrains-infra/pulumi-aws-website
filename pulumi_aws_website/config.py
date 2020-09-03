from typing import Dict

import pulumi

LAMBDA_EVENT_TYPE_VIEWER_REQUEST = 'viewer-request'
LAMBDA_EVENT_TYPE_ORIGIN_REQUEST = 'origin-request'
LAMBDA_EVENT_TYPE_VIEWER_RESPONSE = 'viewer-response'
LAMBDA_EVENT_TYPE_ORIGIN_RESPONSE = 'origin-response'

LAMBDA_EVENT_TYPES = [
    LAMBDA_EVENT_TYPE_ORIGIN_REQUEST,
    LAMBDA_EVENT_TYPE_VIEWER_REQUEST,
    LAMBDA_EVENT_TYPE_ORIGIN_RESPONSE,
    LAMBDA_EVENT_TYPE_VIEWER_RESPONSE,
]


class LoggingConfig:
    bucket: str
    include_cookies: bool
    prefix: str

    def __init__(self, bucket: str, include_cookies: bool, prefix: str):
        self.bucket = bucket
        self.include_cookies = include_cookies
        self.prefix = prefix

    def to_dict(self) -> Dict[str, str]:
        return {
            'bucket': self.bucket,
            'includeCookies': self.include_cookies,
            'prefix': self.prefix,
        }


class LambdaFunctionAssociation:
    event_type: str
    lambda_arn: pulumi.Input[str]
    include_body: bool

    def __init__(self, event_type: str, lambda_arn: pulumi.Input[str], include_body=False):
        if event_type not in LAMBDA_EVENT_TYPES:
            raise Exception(f'Lambda edge event type must be '
                            f'< viewer-request | origin-request | viewer-response | origin-response >, '
                            f'not {event_type}')
        self.event_type = event_type
        self.lambda_arn = lambda_arn
        self.include_body = include_body

    def to_dict(self) -> Dict[str, str]:
        return {
            'eventType': self.event_type,
            'lambdaArn': self.lambda_arn,
            'includeBody': self.include_body,
        }


class Origin:
    domain_name: pulumi.Output[str]
    origin_id: pulumi.Output[str]
    s3_origin_access_identity: pulumi.Output[str]

    def __init__(self, domain_name: pulumi.Output[str],
                 origin_id: pulumi.Output[str],
                 s3_origin_access_identity: pulumi.Output[str]):
        self.domain_name = domain_name
        self.origin_id = origin_id
        self.s3_origin_access_identity = s3_origin_access_identity

    def to_dict(self) -> Dict:
        return {
            "domain_name": self.domain_name,
            "originId": self.origin_id,
            "s3OriginConfig": {
                "originAccessIdentity": self.s3_origin_access_identity,
            },
        }


VIEWER_PROTOCOL_POLICY_HTTP_ONLY = 'http-only'
VIEWER_PROTOCOL_POLICY_HTTPS_ONLY = 'https-only'
VIEWER_PROTOCOL_POLICY_REDIRECT_TO_HTTPS = 'redirect-to-https'
VIEWER_PROTOCOL_POLICY_MATCH_VIEWER = 'match-viewer'


class CacheBehavior:
    allowed_methods: [str]
    cached_methods: [str]
    compress: bool
    default_ttl: int
    min_ttl: int
    max_ttl: int
    path_pattern: str
    target_origin_id: str
    viewer_protocol_policy: str
    forwarded_values_cookies: str
    forwarded_values_headers: [str]
    forwarded_values_query_string: bool
    lambda_function_associations: [LambdaFunctionAssociation]

    def to_dict(self) -> Dict:
        output = {
            'allowedMethods': self.allowed_methods,
            'cachedMethods': self.cached_methods,
            'compress': self.compress,
            'defaultTtl': self.default_ttl,
            'forwardedValues': {
                'cookies': {
                    'forward': self.forwarded_values_cookies,
                },
                'queryString': self.forwarded_values_query_string,
            },
            'maxTtl': self.max_ttl,
            'minTtl': self.min_ttl,
            'targetOriginId': self.target_origin_id,
            'viewerProtocolPolicy': self.viewer_protocol_policy,
            'lambdaFunctionAssociations': list(map(lambda x: x.to_dict(), self.lambda_function_associations))
        }
        if self.forwarded_values_headers is not None:
            output['forwardedValues']['headers'] = self.forwarded_values_headers
        if self.path_pattern is not None:
            output['pathPattern'] = self.path_pattern
        return output


MIN_PROTOCOL_VERSION_SSLV3 = 'SSLv3'
MIN_PROTOCOL_VERSION_TLSV1 = 'TLSv1'
MIN_PROTOCOL_VERSION_TLSV1_2016 = 'TLSv1_2016'
MIN_PROTOCOL_VERSION_TLSV1_1_2016 = 'TLSv1.1_2016'
MIN_PROTOCOL_VERSION_TLSV1_2_2018 = 'TLSv1.2_2018'

SSL_SUPPORT_METHOD_SNI_ONLY = 'sni-only'
SSL_SUPPORT_METHOD_VIP = 'vip'


class ViewerCertificate:
    acm_certificate_arn: pulumi.Input[str]
    cloudfront_default_certificate: bool
    iam_certificate_id: pulumi.Input[str]
    minimum_protocol_version: str
    ssl_support_method: str

    def __init__(self, acm_certificate_arn: pulumi.Input[str] = None,
                 cloudfront_default_certificate: bool = None,
                 iam_certificate_id: pulumi.Input[str] = None,
                 minimum_protocol_version: str = None,
                 ssl_support_method: str = None):
        """
        The SSL configuration for this distribution (maximum one).
            https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distribution-viewercertificate.html
        :param acm_certificate_arn: The ARN of the [AWS Certificate Manager]
            (https://aws.amazon.com/certificate-manager/)
            certificate that you wish to use with this distribution. Specify this,
            `cloudfront_default_certificate`, or `iam_certificate_id`.  The ACM
            certificate must be in  US-EAST-1.
        :param cloudfront_default_certificate: if you want viewers to use HTTPS
            to request your objects and you're using the CloudFront domain name for your
            distribution. Specify this, `acm_certificate_arn`, or `iam_certificate_id`.
        :param iam_certificate_id: The IAM certificate identifier of the custom viewer
            certificate for this distribution if you are using a custom domain. Specify
            this, `acm_certificate_arn`, or `cloudfront_default_certificate`.
        :param minimum_protocol_version: The minimum version of the SSL protocol that
            you want CloudFront to use for HTTPS connections. Can only be set if
            `cloudfront_default_certificate = false`. One of `SSLv3`, `TLSv1`,
            `TLSv1_2016`, `TLSv1.1_2016` or `TLSv1.2_2018`. Default: `TLSv1`. **NOTE**:
            If you are using a custom certificate (specified with `acm_certificate_arn`
            or `iam_certificate_id`), and have specified `sni-only` in
            `ssl_support_method`, `TLSv1` or later must be specified. If you have
            specified `vip` in `ssl_support_method`, only `SSLv3` or `TLSv1` can be
            specified. If you have specified `cloudfront_default_certificate`, `TLSv1`
            must be specified.
        :param ssl_support_method
        """
        self.acm_certificate_arn = acm_certificate_arn
        self.cloudfront_default_certificate = cloudfront_default_certificate
        self.iam_certificate_id = iam_certificate_id
        self.minimum_protocol_version = minimum_protocol_version
        self.ssl_support_method = ssl_support_method

    def to_dict(self) -> Dict:
        output = {}
        if self.acm_certificate_arn is not None:
            output['acmCertificateArn'] = self.acm_certificate_arn
        if self.cloudfront_default_certificate is not None:
            output['cloudfrontDefaultCertificate'] = self.cloudfront_default_certificate
        if self.iam_certificate_id is not None:
            output['iamCertificateId'] = self.iam_certificate_id
        if self.minimum_protocol_version is not None:
            output['minimumProtocolVersion'] = self.minimum_protocol_version
        if self.ssl_support_method is not None:
            output['sslSupportMethod'] = self.ssl_support_method
        return output


class CustomErrorResponse:
    error_code: int
    response_code: int
    response_page_path: str

    def __init__(self, error_code: int, response_code: int, response_page_path: str):
        self.error_code = error_code
        self.response_code = response_code
        self.response_page_path = response_page_path

    def to_dict(self) -> Dict:
        return {
            'errorCode': self.error_code,
            'responseCode': self.response_code,
            'responsePagePath': self.response_page_path,
        }
