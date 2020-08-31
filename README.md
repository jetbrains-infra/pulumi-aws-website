# pulumi-aws-website
Pulumi ComponentResource for creating CloudFront + S3 websites

# How to install
```bash
pip install --upgrade pip
pip install wheel
pip install pulumi-aws-website
# or
pip install git+git://github.com/jetbrains-infra/pulumi-aws-website@<tag or branch>
``` 

# How to use
```python
import pulumi
from pulumi_aws_website import config
from pulumi_aws_website import WebSite


website = WebSite('my-site',
                  issue='sre-123',
                  stack='staging',
                  zones={
                      'ABCDEF123': ['test.jetbrains.com']
                  },
                  viewer_certificate=config.ViewerCertificate(cloudfront_default_certificate=True)
                  )

pulumi.export('cf_distribution_id', website.distribution.id)
```