import os
import ConfigParser

from tornado.testing import AsyncTestCase, gen_test

from tornado_aws import AWSClient
from pprint import pprint


class TestTornadoAWS(AsyncTestCase):

    def setUp(self):
        super(TestTornadoAWS, self).setUp()
        config = ConfigParser.RawConfigParser()
        config.read(os.path.expanduser('~/.aws/credentials'))
        profile = os.getenv('AWS_PROFILE', 'default')
        try:
            access_key = config.get(profile, 'aws_access_key_id')
            secret_key = config.get(profile, 'aws_secret_access_key')
        except ConfigParser.NoSectionError:
            raise Exception('Profile not found \'{profile}\''.format(profile=profile))
        self.aws = AWSClient(access_key=access_key, secret_key=secret_key)

    @gen_test
    def test_get(self):
        response = yield self.aws.request(
            service='ec2',
            region='us-west-1',
            method='GET',
            query='Action=DescribeRegions&Version=2013-10-15',
        )
        pprint(response)

    @gen_test
    def test_post(self):
        pass
