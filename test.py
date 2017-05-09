import os, ConfigParser

from tornado.testing import AsyncTestCase, gen_test
from tornado_aws import AWSClient

from pprint import pprint

from time import sleep


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

        #pprint(response)

        regions = response['DescribeRegionsResponse']['regionInfo']['item']

        assert regions[0]['regionName'] == 'ap-south-1'
        assert regions[1]['regionName'] == 'eu-west-2'
        assert regions[2]['regionName'] == 'eu-west-1'

    @gen_test(timeout=10)
    def test_post(self):
        response = None

        while True:
            response = yield self.aws.request(
                service='dynamodb',
                region='us-west-2',
                method='POST',
                amazon_target='DynamoDB_20120810.CreateTable',
                body='''
                    {
                        "KeySchema": [
                            {"KeyType": "HASH","AttributeName": "Id"}
                        ],
                        "TableName": "TestTable","AttributeDefinitions":[
                            {"AttributeName": "Id","AttributeType": "S"}
                        ],
                        "ProvisionedThroughput": {
                            "WriteCapacityUnits": 5,
                            "ReadCapacityUnits": 5
                        }
                    }
                '''
            )

            #pprint(response)

            if response.get('__type'):
                sleep(1)
                pprint(response)
                continue

            if response['TableDescription']['TableStatus'] in ['CREATING']:
                break

            sleep(1)


        while True:
            response = yield self.aws.request(
                service='dynamodb',
                region='us-west-2',
                method='POST',
                amazon_target='DynamoDB_20120810.DescribeTable',
                body='''
                    {
                        "TableName": "TestTable"
                    }
                '''
            )

            #pprint(response)

            if response.get('__type'):
                sleep(1)
                pprint(response)
                continue

            if response['Table']['TableStatus'] in ['ACTIVE']:
                break

            sleep(1)


        while True:
            response = yield self.aws.request(
                service='dynamodb',
                region='us-west-2',
                method='POST',
                amazon_target='DynamoDB_20120810.DeleteTable',
                body='''
                    {
                        "KeySchema": [
                            {"KeyType": "HASH","AttributeName": "Id"}
                        ],
                        "TableName": "TestTable","AttributeDefinitions":[
                            {"AttributeName": "Id","AttributeType": "S"}
                        ],
                        "ProvisionedThroughput": {
                            "WriteCapacityUnits": 5,
                            "ReadCapacityUnits": 5
                        }
                    }
                '''
            )

            #pprint(response)

            if response.get('__type'):
                sleep(1)
                pprint(response)
                continue

            if response['TableDescription']['TableStatus'] in ['DELETING']:
                break

            sleep(1)
