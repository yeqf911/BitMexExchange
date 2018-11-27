from requests.auth import AuthBase


class AccessTokenAuth(AuthBase):
    def __init__(self, access_token):
        self.token = access_token

    def __call__(self, req):
        if self.token:
            req.headers['access-token'] = self.token

