from pprint import pprint

import ccxt
import pandas as pd

from market_maker import settings

bitmex = ccxt.bitmex()
bitmex.apiKey = settings.API_KEY
bitmex.secret = settings.API_SECRET
bitmex.proxies = {'http': 'http://127.0.0.1:1087', 'https': 'https://127.0.0.1:1087'}

print(bitmex.fetch_balance())
print(bitmex.fetch_ticker('BTC/USD'))
ohlcv = bitmex.fetch_ohlcv('BTC/USD', '5m', limit=750)
df = pd.DataFrame(ohlcv)
df.rename(columns={0: 'date', 1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volumn'}, inplace=True)
df['date'] = pd.to_datetime(df['date'], unit='ms')
pprint(df)
