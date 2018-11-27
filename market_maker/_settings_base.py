# API URL.
BASE_URL = "https://www.bitmex.com/api/v1/"

# Credentials
LOGIN = "test@test.com"
PASSWORD = "password"

# Instrument to market make.
SYMBOL = "XBTP14"

# If true, don't set up any orders, just say what we would do
# DRY_RUN = True
DRY_RUN = False

# If we're doing a dry run, use these numbers for BTC balances
DRY_BTC = 50

# How many pairs of buy/sell orders to keep open
ORDER_PAIRS = 6

# How many contracts each order should contain
ORDER_SIZE = 500

# Distance between successive orders, as a percentage (example: 0.005 for 0.5%)
INTERVAL = 0.005
