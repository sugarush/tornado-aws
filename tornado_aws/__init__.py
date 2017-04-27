import os, hmac, hashlib

from copy import copy
from datetime import datetime

from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.httputil import HTTPHeaders


from pprint import pprint


def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def hexdigest(msg):
    return hashlib.sha256(msg).hexdigest()

class AWSClient(object):

    def __init__(self, *args, **kargs):
        self.client = AsyncHTTPClient()
        self.access_key = kargs.get('access_key')
        self.secret_key = kargs.get('secret_key')

    @gen.coroutine
    def request(self, **kargs):
        kargs['access_key'] = self.access_key
        kargs['secret_key'] = self.secret_key
        request = AWSRequest(**kargs).create()
        response = yield self.client.fetch(request, raise_error=False)
        raise gen.Return(response)


class AWSRequest(object):

    def __init__(self, **kargs):
        self.algorithm = 'AWS4-HMAC-SHA256'
        self.amazon_format = '%Y%m%dT%H%M%SZ'
        self.stamp_format = '%Y%m%d'

        self.methods = ['GET', 'PUT', 'POST', 'DELETE', 'OPTIONS']

        self.access_key = kargs.get('access_key')
        self.secret_key = kargs.get('secret_key')
        self.region = kargs.get('region')
        self.service = kargs.get('service')
        self.method = kargs.get('method').upper()

        self.now = datetime.now()

        self.amazon_date = self.now.strftime(self.amazon_format)
        self.stamp_date = self.now.strftime(self.stamp_format)

        if not (self.method in self.methods):
            raise Exception('Invalid method {method}'.format(
                method=self.method
            ))

        self.host = '{service}.{region}.amazonaws.com'.format(
            service=self.service,
            region=self.region
        )

        self.endpoint = 'https://{host}'.format(host=self.host)
        self.uri = kargs.get('uri', '/')

        self.headers = HTTPHeaders()

        self.body = kargs.get('body', '')
        self.query = kargs.get('query', '')

        self.url = '{endpoint}?{query}'.format(endpoint=self.endpoint, query=self.query)

        self.content_type = kargs.get('content_type', 'application/x-amz-json-1.0')

        self.header('content-type', self.content_type)
        self.header('host', self.host)

        date = sign(('AWS4' + self.secret_key).encode('utf-8'), self.stamp_date)
        region = sign(date, self.region)
        service = sign(region, self.service)
        self.signing_key = sign(service, 'aws4_request')

    def signiature(self):
        return sign(self.signing_key, self.string())

    def header(self, name, value):
        name = '-'.join([ x.capitalize() for x in name.split('-') ])
        self.headers[name] = value

    def headers_cannonical(self):
        headers = ''
        for k in sorted(self.headers):
            headers += '{key}:{value}\n'.format(
                key=k.strip(),
                value=self.headers[k]
            )
        return headers

    def headers_signed(self):
        headers = ''
        for k in sorted(self.headers):
            headers += '{key};'.format(key=k.strip())
        return headers.rstrip(';')

    def scope(self):
        kargs = copy(self.__dict__)
        return '{stamp_date}/{region}/{service}/aws4_request'.format(**kargs)

    def request_cannonical(self):
        kargs = copy(self.__dict__)
        kargs['headers_signed'] = self.headers_signed()
        kargs['headers_cannonical'] = self.headers_cannonical()
        kargs['body_hash'] = hexdigest(self.body)
        string = '{method}\n{uri}\n{query}\n{headers_cannonical}\n{headers_signed}\n{body_hash}'.format(**kargs)
        pprint(kargs)
        return string

    def string(self):
        kargs = copy(self.__dict__)
        kargs['scope'] = self.scope()
        kargs['request_cannonical'] = hexdigest(self.request_cannonical())
        return '{algorithm}\n{amazon_date}\n{scope}\n{request_cannonical}'.format(**kargs)

    def authorization(self):
        kargs = copy(self.__dict__)
        kargs['scope'] = self.scope()
        kargs['headers_signed'] = self.headers_signed()
        kargs['signiature'] = self.signiature()
        return '{algorithm} Credential={access_key}/{scope}, SignedHeaders={headers_signed}, Signiature={signiature}'.format(**kargs)

    def create(self):
        self.header('Authorization', self.authorization())
        return HTTPRequest(self.url,
            method=self.method,
            headers=self.headers,
            body=self.body
        )
