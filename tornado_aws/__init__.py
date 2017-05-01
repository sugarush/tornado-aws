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

        self.access_key = kargs.get('access_key')
        self.secret_key = kargs.get('secret_key')
        self.region = kargs.get('region')
        self.service = kargs.get('service')
        self.method = kargs.get('method').upper()

        self.methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']

        if not (self.method in self.methods):
            raise Exception('Invalid method {method}'.format(
                method=self.method
            ))

        self.now = datetime.utcnow()

        self.amazon_date = self.now.strftime(self.amazon_format)
        self.stamp_date = self.now.strftime(self.stamp_format)

        # TODO: support regionless service
        #self.host = '{service}.{region}.amazonaws.com'.format(
        self.host = '{service}.amazonaws.com'.format(
            service=self.service,
            #region=self.region
        )

        self.endpoint = 'https://{host}'.format(host=self.host)
        self.uri = kargs.get('uri', '/')

        self.headers = { }
        self.canonical_headers = { }
        self.request_headers = { }

        self.body = kargs.get('body', None)
        self.query = kargs.get('query', '')

        self.url = '{endpoint}?{query}'.format(endpoint=self.endpoint, query=self.query)

        self.content_type = kargs.get('content_type', 'application/x-amz-json-1.0')

        self.header_request('accept', '*/*')
        self.header_request('connection', 'keep-alive')
        self.header_request('user-agent', 'tornado-aws/0.0.0')
        self.header_request('content-type', self.content_type)

        self.header_canonical('x-amz-date', self.amazon_date)
        self.header_canonical('host', self.host)

        date = sign(('AWS4' + self.secret_key).encode('utf-8'), self.stamp_date)
        region = sign(date, self.region)
        service = sign(region, self.service)
        self.signing_key = sign(service, 'aws4_request')


        self.header_request('authorization', self.authorization())

    def signature(self):
        return hmac.new(self.signing_key, self.string().encode('utf-8'), hashlib.sha256).hexdigest()

    def header_canonical(self, name, value):
        name = name.lower()
        self.canonical_headers[name] = value

    def header_request(self, name, value):
        name = name.lower()
        self.request_headers[name] = value

    def headers_canonical(self):
        headers = ''
        for k in self.canonical_headers.keys():
            headers += '{key}:{value}\n'.format(
                key=k.strip(),
                value=self.canonical_headers[k]
            )
        return headers

    def headers_signed(self):
        headers = ''
        for k in self.canonical_headers.keys():
            headers += '{key};'.format(key=k.strip())
        return headers.rstrip(';')

    def scope(self):
        kargs = copy(self.__dict__)
        return '{stamp_date}/{region}/{service}/aws4_request'.format(**kargs)

    def request_canonical(self):
        kargs = copy(self.__dict__)
        kargs['body_hash'] = hexdigest(self.body or '')
        kargs['headers_canonical'] = self.headers_canonical()
        kargs['headers_signed'] = self.headers_signed()
        return '{method}\n{uri}\n{query}\n{headers_canonical}\n{headers_signed}\n{body_hash}'.format(**kargs)

    def string(self):
        kargs = copy(self.__dict__)
        kargs['scope'] = self.scope()
        kargs['request_canonical'] = hexdigest(self.request_canonical())
        return '{algorithm}\n{amazon_date}\n{scope}\n{request_canonical}'.format(**kargs)

    def authorization(self):
        kargs = copy(self.__dict__)
        kargs['scope'] = self.scope()
        kargs['headers_signed'] = self.headers_signed()
        kargs['signature'] = self.signature()
        return '{algorithm} Credential={access_key}/{scope}, SignedHeaders={headers_signed}, Signature={signature}'.format(**kargs)

    def create(self):
        self.headers.update(self.canonical_headers)
        self.headers.update(self.request_headers)
        return HTTPRequest(self.url,
            method=self.method,
            headers=self.headers,
            body=self.body
        )
