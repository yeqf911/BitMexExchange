import json
import logging
from functools import wraps
from time import sleep

import requests

from market_maker import settings
from market_maker.auth import APIKeyAuthWithExpires
from market_maker.utils import errors
from market_maker.ws import ws_thread

VERSION = 1


class BitMEX(object):
    def __init__(self, base_url=None, symbol=None, api_key=None, api_secret=None, order_id_prefix='mm_bitmex',
                 should_ws_auth=True, post_only=False, timeout=8, proxy_host=None, proxy_port=None):
        self.logger = logging.getLogger('bitmex')
        self.base_url = base_url
        self.symbol = symbol
        if api_key is None:
            raise Exception('Please set an API key and secret to start.')
        self.api_key = api_key
        self.api_secret = api_secret
        if len(order_id_prefix) > 13:
            raise ValueError('settings.ORDER_ID_PREFIX must be at most 13 characters long.')
        self.order_id_prefix = order_id_prefix
        self.should_ws_auth = should_ws_auth
        self.post_only = post_only
        self.timeout = timeout
        self.retries = 0

        # prepare HTTPS session
        self.session = requests.Session()
        self.session.headers.update({'user-agent': 'liquidbot-' + str(VERSION)})
        self.session.headers.update({'Content-Type': 'application/json'})
        self.session.headers.update({'Accept': 'application/json'})
        proxies = None
        if proxy_host and proxy_port:
            proxies = {
                'http': 'http://{}:{}'.format(proxy_host, proxy_port),
                'https': 'https://{}:{}'.format(proxy_host, proxy_port)
            }
        self.session.proxies = proxies

        # create websockets
        self.ws = ws_thread.BitMEXWebSocket(symbol, should_ws_auth, proxy_host, proxy_port)

    def connect_ws(self):
        self.ws.connect(self.base_url)

    def authentication_required(func):
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            if not self.api_key:
                message = 'You must be authenticated to use this method'
                raise errors.AuthenticationError(message)
            else:
                return func(self, *args, **kwargs)

        return wrapped

    def order(self, order_id):
        path = 'order'
        order = self._curl_bitmex(path=path, query={
            'orders': [order_id],
            'count': 2
        })
        return order

    @authentication_required
    def cancel(self, order_id):
        """取消一个存在的订单"""
        path = 'order'
        orders = self._curl_bitmex(path=path,
                                   query={
                                       'count': 2
                                   }, verb='GET')

    @authentication_required
    def funds(self):
        """Get your current balance."""
        return self.ws.funds()

    @authentication_required
    def instrument(self, symbol):
        return self.ws.get_instrument(symbol)

    def _curl_bitmex(self, path, query=None, post_dict=None, timeout=None, verb=None, rethrow_errors=None,
                     max_retries=None):
        url = self.base_url + path
        if timeout is None:
            timeout = self.timeout

        if not verb:
            verb = 'POST' if post_dict else 'GET'

        if max_retries is None:
            max_retries = 0 if verb in ['POST', 'PUT'] else 3

        auth = APIKeyAuthWithExpires(self.api_key, self.api_secret)

        def exit_or_throw(e):
            if rethrow_errors:
                raise e
            else:
                exit(1)

        # 这里使用了递归，后面要不要考虑变成队列？
        def retry():
            self.retries += 1
            if self.retries > max_retries:
                raise Exception('Max retries on {} ({}), raising.'.format(path, json.dumps(post_dict)))
            return self._curl_bitmex(path, query, post_dict, timeout, verb, rethrow_errors, max_retries)

        response = None
        try:
            self.logger.info('Sending request to {} ({}) hit, raising.'.format(path, json.dumps(post_dict or '')))
            req = requests.Request(verb, url, json=post_dict, auth=auth, params=query)
            prepped = self.session.prepare_request(req)
            response = self.session.send(prepped, timeout=timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response is None:
                raise e

            if response.status_code == 401:
                self.logger.error("API Key or Secret incorrect, please check it and restart")
                self.logger.error("Error: {}".format(response.text))
                if post_dict:
                    self.logger.error(post_dict)
                # 认证失败总是会直接退出
                exit(1)

            elif response.status_code == 404:
                if verb == 'DELETE':
                    self.logger.error('Order has not found: {}'.format(post_dict['orderID']))
                self.logger.info(
                    'Unable to connect BitMEX API (404). Request: {}\n{}'.format(url, json.dumps(post_dict)))
                exit_or_throw(e)

            elif response.status_code == 429:
                self.logger.error("Ratelimited on current request. Request: {}\n{}".format(url, json.dumps(post_dict)))
                # 被禁止了，登时间过了重试
                sleep(100000)
                retry()

            elif response.status_code == 503:
                self.logger.info(
                    "Unable to connect to BitMEX(503), retring. Request: {}\n{}".format(url, json.dumps(post_dict)))

            elif response.status_code == 400:
                error = response.json()['error']
                message = error['message'].lower() if error else ''
                if 'duplicate orderid' in message:
                    raise Exception('Duplicate Order ids')
                elif 'insufficiant avaliable balance' in message:
                    self.logger.error("I dont konwn what the hell it is")
                    exit_or_throw(e)
            self.logger.error('处理不了了，我也不知道了: {} {} {} {} {}'.format(e, response.text, verb, url, post_dict))
            exit_or_throw(e)
        except requests.exceptions.Timeout as e:
            self.logger.warning("Timeour for request: {} ({}), retrying...".format(url, json.dumps(post_dict)))
            return retry()

        except requests.exceptions.ConnectionError as e:
            self.logger.warning("Unable to connect the BitMEX API ({})".format(e))
            return retry()

        self.retries = 0
        return response.json()


if __name__ == '__main__':
    bitmex = BitMEX(base_url=settings.BASE_URL, api_key=settings.API_KEY, api_secret=settings.API_SECRET,
                    symbol='BCHZ18', proxy_host='127.0.0.1', proxy_port=1087)
    bitmex.connect_ws()
    print(bitmex.order('79045a4'))
