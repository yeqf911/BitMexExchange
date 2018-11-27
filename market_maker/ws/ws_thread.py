import json
import ssl
import sys
import threading
import traceback
from time import sleep
from pprint import pprint

import websocket
from future.standard_library import hooks

from market_maker import settings
from market_maker.auth.api_key_auth import generate_expires, generate_signature
from market_maker.utils.log import setup_custom_logger

with hooks():
    from urllib.parse import urlparse, urlunparse


def find_item_by_keys(keys, table, match_data):
    for item in table:
        matched = True
        for key in keys:
            if item[key] != match_data[key]:
                matched = False
        if matched:
            return item


class BitMEXWebSocket(object):
    MAX_TABLE_LEN = 200

    def __init__(self, symbol='XBTUSD', should_auth=True, proxy_host=None, proxy_port=None):
        self.ws = None
        self.exited = False
        self.logger = setup_custom_logger('websocket', log_level=settings.LOG_LEVEL)
        self.__reset()
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.symbol = symbol
        self.should_auth = should_auth

    def connect(self, endpoint=''):
        if self.ws:
            raise Exception('WebSocket has already connected')
        self.logger.debug('Connecting WebSocket')

        subscriptions = [sub + ':' + self.symbol for sub in ['quoteBin1m']]
        # subscriptions += ['instrument']  # we want all of them
        if self.should_auth:
            subscriptions += [sub + ':' + self.symbol for sub in ['order', 'execution']]
            subscriptions += ['margin', 'position']

        # Get WS URL and connect
        url_parts = list(urlparse(endpoint))
        url_parts[0] = url_parts[0].replace('http', 'ws')
        url_parts[2] = '/realtime?subscribe=' + ','.join(subscriptions)
        ws_url = urlunparse(url_parts)
        self.logger.info("Connecting to {}".format(ws_url))
        self.__connect(ws_url)
        self.logger.info("Connected to WS. Waiting for data images, this may take a moment...")
        # Connected. Waiting for partials

    def __connect(self, ws_url):
        self.logger.debug('Starting thread')
        ssl_defaults = ssl.get_default_verify_paths()
        sslpot_ca_certs = {'ca_certs': ssl_defaults.cafile}
        self.ws = websocket.WebSocketApp(ws_url,
                                         header=self.__get_auth(),
                                         on_message=self.__on_message,
                                         on_close=self.__on_close,
                                         on_open=self.__on_open,
                                         on_error=self.__on_error,
                                         on_ping=self.__on_ping,
                                         on_pong=self.__on_pong)

        self.wst = threading.Thread(target=lambda: self.ws.run_forever(sslopt=sslpot_ca_certs,
                                                                       http_proxy_host=self.proxy_host,
                                                                       http_proxy_port=self.proxy_port,
                                                                       ping_interval=20,
                                                                       ping_timeout=10))
        self.wst.demaon = True
        self.wst.start()
        self.logger.info('Start thread')
        # Wait for connnect bnefore continuing
        conn_timeout = 5
        while (not self.ws.sock or not self.ws.sock.connected) and conn_timeout and not self._error:
            sleep(1)
            conn_timeout -= 1
        if not conn_timeout or self._error:
            self.logger.error("Couldn't connect to WS. Exiting...")
            self.exit()
            sys.exit(1)

    def funds(self):
        return self.data['margin'][0]

    def get_instrument(self, symbol):
        return self.symbol

    def __get_auth(self):
        if self.should_auth is False:
            return []

        self.logger.info("Authenticating with API key.")
        nonce = generate_expires()
        return [
            'api-expires:' + str(nonce),
            'api-signature:' + generate_signature(settings.API_SECRET, 'GET', '/realtime', nonce, ''),
            'api-key:' + settings.API_KEY
        ]

    def __auth(self):
        nonce = generate_expires()
        signature = generate_signature(settings.API_SECRET, 'GET', '/realtime', nonce, '')
        args = [settings.API_KEY, nonce, signature]
        self.__send_command('authKeyExpires', args)

    def __wait_for_acount(self):
        while not {'margin', 'position', 'order'} <= set(self.data):
            sleep(0.1)

    def __send_command(self, commmad, args=None):
        if args is None:
            args = []
        self.ws.send(json.dumps({'op': commmad, 'args': args}))

    def __on_message(self, message):
        message = json.loads(message)
        self.logger.debug(json.dumps(message))

        table = message['table'] if 'table' in message else None
        action = message['action'] if 'action' in message else None
        try:
            if 'subscribe' in message:
                if message['success']:
                    self.logger.debug('Subcribed to {}.'.format(message['subscribe']))
                else:
                    self.logger.error('Unable to subscribe {}, please check and restart'.format(message['subscribe']))
            elif 'status' in message:
                self.logger.error(message['error'])

            elif action:
                if table not in self.data:
                    self.data[table] = []

                if table not in self.keys:
                    self.keys[table] = []

                if action == 'partial':
                    self.logger.debug('{}: partial'.format(table))
                    self.data[table] += message['data']
                    self.keys[table] += message['keys']

                elif action == 'insert':
                    self.logger.debug('{}: inserting {}'.format(table, message['data']))
                    self.data[table] += message['data']
                    # 当table的数量超过最大长度，舍弃前面一半的没用的
                    if table not in ['order', 'orderBookL2'] and len(self.data[table]) > BitMEXWebSocket.MAX_TABLE_LEN:
                        self.data[table] = self.data[table][(BitMEXWebSocket.MAX_TABLE_LEN // 2):]

                elif action == 'update':
                    self.logger.info('{}: updating {}'.format(table, message['data']))
                    for update_data in message['data']:
                        item = find_item_by_keys(self.keys[table], self.data[table], update_data)
                        if not item:
                            continue
                        if table == 'order':
                            is_canceled = 'ordStatus' in update_data and update_data['ordStatus'] == 'Canceled'
                            if 'cumQty' in update_data and not is_canceled:
                                cont_executed = update_data['cumQty'] - item['cumQty']
                                if cont_executed > 0:
                                    instrument = self.get_instrument(item['symbol'])
                                    self.logger.info('Execution: {} {} Contracts of {} at {}'
                                                     .format(item['side'], cont_executed,
                                                             item['symbol'],
                                                             instrument['tickLog'],
                                                             item['price']))
                        item.update(update_data)
                        if table == 'order' and item['leavesQty'] <= 0:
                            self.data[table].remove(item)

                elif action == 'delete':
                    self.logger.debug('{}: deleting {}'.format(table, message['data']))
                    for delete_data in message['data']:
                        item = find_item_by_keys(self.keys[table], self.data[table], delete_data)
                        self.data[table].remove(item)
                else:
                    raise Exception('Unknown action: {}'.format(action))
        except:
            self.logger.error(traceback.format_exc())

    def __on_close(self):
        self.logger.info('WebSocket connection has been closed')

    def __on_open(self):
        self.logger.info('WebSocket connected...')

    def __on_error(self, error):
        self.logger.error('超时' + error)

    def __on_ping(self, ping):
        pass

    def __on_pong(self, pong):
        pass

    def __del__(self):
        if self.ws:
            self.exit()

    def exit(self):
        self.exited = True
        self.ws.close()

    def __reset(self):
        self.data = {}
        self.keys = {}
        self.exited = False
        self._error = None
