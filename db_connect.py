from pymongo import MongoClient
import pickle
import gzip
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

client = MongoClient("mongodb://{}:{}@{}/{}".format(
                        config.get('MongoConfig', 'user'),
                        config.get('MongoConfig', 'password'),
                        config.get('MongoConfig', 'host'),
                        config.get('MongoConfig', 'db')
                        ))

db = client.twitter_db

with gzip.open('data/raw/raw_tweets.pickle', 'r') as f:
    tweets_json = pickle.load(f)


tweets = client.twitter_db.tweets

for tweet in tweets_json[1:]:
    tweets.insert_one(tweet)


