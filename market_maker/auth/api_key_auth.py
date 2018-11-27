import hashlib
import hmac
import time

from future.builtins import bytes
from future.standard_library import hooks
from requests.auth import AuthBase

with hooks():
    from urllib.parse import urlparse


class APIKeyAuth(AuthBase):
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    def __call__(self, req):
        nonce = generate_expires()
        req.headers['api-expires'] = str(nonce)
        req.headers['api-key'] = self.api_key
        req.headers['api-signature'] = generate_signature(self.api_secret, req.method, req.url, nonce, req.body or '')


def generate_expires():
    return int(time.time() + 3600)


def generate_signature(secret, verb, url, nonce, data):
    parsed_url = urlparse(url)
    path = parsed_url.path
    if parsed_url.query:
        path = path + '?' + parsed_url.query

    if isinstance(data, (bytes, bytearray)):
        data = data.decode('utf8')

    message = verb + path + str(nonce) + data
    signature = hmac.new(bytes(secret, 'utf8'), bytes(message, 'utf8'), digestmod=hashlib.sha256).hexdigest()
    return signature
