#! /usr/bin/env python
import pymongo
import threading
from pprint import pprint
import time

from market_maker import bitmex
from market_maker import settings
from market_maker.db import MongoManager


def fund(b):
    while True:
        funds = b.funds()
        pprint(funds)
        time.sleep(5)


bitmex = bitmex.BitMEX(base_url=settings.BASE_URL, api_key=settings.API_KEY, api_secret=settings.API_SECRET,
                       symbol='BCHZ18', proxy_host='127.0.0.1', proxy_port=1087)
bitmex.connect_ws()
threading.Thread(target=fund, args=[bitmex]).start()

# print(bitmex.order('79045a4'))
#
# client = pymongo.MongoClient('mongodb://127.0.0.1:27017')
#
# db = client['bitmex']
# collection = db['trade']
#
# t1 = {
#     'symbol': 'XBTUSD',
#     'price': 4000
# }
#
# t2 = {
#     'type': 'ETHUSD',
#     'count': 100000
# }
#
# result = collection.insert(t2)
#
# print(result)
#
# print(collection.find_one({'symbol': 'XBTUSD'}))

mongo_manager = MongoManager(host='127.0.0.1', port=27017, dbname='bitmex')

df = mongo_manager.read_mongo('trade')
# print(df)
# print(mongo_manager.collection('trade').insert({'name': 'Nicole'}))
