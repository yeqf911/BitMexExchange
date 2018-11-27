from market_maker import constants
from pprint import pprint
from time import sleep
import sys
from market_maker import settings
from datetime import datetime
from os.path import getmtime
from market_maker import bitmex

import random
import requests
import atexit
import signal
from market_maker.utils import log

# pprint(constants.USD_DECIMAL_PLACES)

logger = log.setup_custom_logger('root')


class ExchangeInterface:
    def __init__(self, dry_run):
        self.dry_run = dry_run
        if len(sys.argv) > 1:
            self.symbol = sys.argv[1]
        else:
            self.symbol = settings.SYMBOL
        self.bitmex = bitmex.BitMEX(base_url=settings.BASE_URL, symbol=self.symbol, api_key=settings.API_KEY,
                                    api_secret=settings.API_SECRET, order_id_prefix=settings.ORDER_ID_PREFIX,
                                    post_only=settings.POST_ONLY, timeout=settings.TIMEOUT)

    def cancel_order(self, order):
        tick_log = self.get_instrument()['tickLog']
        logger.info("Canceling: {} {} @ {}".format(order['side'], order['orderQty'], tick_log, order['price']))
        while True:
            try:
                self.bitmex.cancel(order['orderID'])
                sleep(settings.API_REST_INTERVAL)
            except ValueError as e:
                logger.info(e)
                sleep(settings.API_ERROR_INTERVAL)
            else:
                break

    def cancel_all_order(self):
        if self.dry_run:
            return
        logger.info('Resetting current position. Canceling all existing orders.')
        tick_log = self.get_instrument()['tickLog']

        orders = self.bitmex.http_open_orders()

        for order in orders:
            logger.info("Canceling: {} {} @ {}".format(order['side'], order['orderQty'], tick_log, order['price']))
            self.bitmex.cancel(order['orderID'])
        if len(orders):
            self.bitmex.cancel([order['orderID'] for order in orders])

    def get_instrument(self, symbol=None):
        return self.bitmex.instrument(symbol or self.symbol)
