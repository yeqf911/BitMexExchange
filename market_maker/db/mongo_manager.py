import pandas as pd
from pandas import DataFrame
from pymongo import MongoClient


class MongoManager:

    def __init__(self, host, port, dbname, username=None, password=None):
        if username and password:
            mongo_url = "mongodb://{}:{}@{}:{}".format(username, password, host, port)
        else:
            mongo_url = "mongodb://{}:{}".format(host, port)
        self.client = MongoClient(mongo_url)
        self.db = self.client[dbname]

    def read_mongo(self, collection, query=None, no_id=True) -> DataFrame:
        if query is None:
            query = {}
        cursor = self.db[collection].find(query)
        df = pd.DataFrame(list(cursor))
        if no_id:
            del df['_id']
        return df

    def collection(self, collection):
        return self.db[collection]



