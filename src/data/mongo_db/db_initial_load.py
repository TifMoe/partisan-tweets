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
                        ), int(config.get('MongoConfig', 'port')))

db = client.twitter_db

# Load all legislator tweets to mongo
with gzip.open('data/raw/raw_tweets.pickle', 'r') as f:
    tweets_json = pickle.load(f)

tweets = client.twitter_db.tweets

for tweet in tweets_json[1:]:
    tweets.insert_one(tweet)


# Load all favorited tweets to mongo
with gzip.open('data/raw/raw_favs.pickle', 'r') as f:
    favs_json = pickle.load(f)

favs = client.twitter_db.favorited_tweets

for fav in favs_json:
    favs.insert_one(fav)