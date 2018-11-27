from requests.auth import AuthBase
import time
from market_maker.auth.api_key_auth import generate_signature


class APIKeyAuthWithExpires(AuthBase):

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    def __call__(self, req):
        expires = int(round(time.time()) + 5)
        req.headers['api-expires'] = str(expires)
        req.headers['api-key'] = self.api_key
        req.headers['api-signature'] = generate_signature(self.api_secret, req.method, req.url, expires, req.body or '')
        return req
