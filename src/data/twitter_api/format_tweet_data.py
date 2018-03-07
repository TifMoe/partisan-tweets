from pymongo import MongoClient
import pickle
import pandas as pd
from configparser import ConfigParser
import src.data.aws_ec2_functions as aws
from collections import defaultdict

config = ConfigParser()
config.read('config.ini')

# Make sure AWS Ec2 Instance is running and get public IP address
instance = aws.fetch_instances()[0]

if aws.instance_state(instance) != 'running':
    print('Starting {} instance now'.format(instance.public_ip_address))
    aws.start_instance(instance, safety=False)


client = MongoClient("mongodb://{}:{}@{}/{}".format(
                        config.get('MongoConfig', 'user'),
                        config.get('MongoConfig', 'password'),
                        instance.public_ip_address,
                        config.get('MongoConfig', 'db'),
                        int(config.get('MongoConfig', 'port'))))

db = client.twitter_db


def create_tweets_dictionary(party_dict, tweet_list):
    list_dicts = []

    for tweet in tweet_list:

            user = [i for (i, dictionary) in enumerate(list_dicts)
                    if dictionary['name']==tweet['user']['screen_name'].lower()]

            if user:
                list_dicts[user[0]]['tweets'].append(tweet['full_text'])
                list_dicts[user[0]]['tweet_count'] += 1
                list_dicts[user[0]]['most_recent_tweet'] = tweet['created_at']

            else:
                dictionary = defaultdict()
                dictionary['name'] = tweet['user']['screen_name'].lower()
                dictionary['party'] = party_dict[tweet['user']['screen_name'].lower()][0]
                dictionary['tweets'] = [tweet['full_text']]
                dictionary['most_recent_tweet'] = tweet['created_at']
                dictionary['tweet_count'] = 1

                list_dicts.append(dictionary)

    return list_dicts


# Format favorited tweets
users = pd.read_pickle('data/interim/favorited_users.pickle')
users_party_dict = {username.lower(): party for (username, party) in zip(users['user.screen_name'], users['party'])}

cursor = db.favorited_tweets.find( { "user.screen_name": { "$in": list(users_party_dict.keys()) } } )
fav_tweet_data = [doc for doc in cursor]
len(fav_tweet_data)

fav_tweet_en = [doc for doc in fav_tweet_data if doc['lang']=='en']
len(fav_tweet_en)


# Format legislator tweets
with open('data/raw/parties.pickle', 'rb') as file:
    leg_party_dict = pickle.load(file)

cursor = db.tweets.find({})
leg_tweet_data = [doc for doc in cursor]
len(leg_tweet_data)

leg_tweet_en = [doc for doc in leg_tweet_data if doc['lang']=='en']
len(leg_tweet_en)

# Load fav tweets
fav_tweets = create_tweets_dictionary(party_dict=users_party_dict,
                                      tweet_list=fav_tweet_en)

fav_tweets_db = client.twitter_db.fav_tweets_dict
for tweet in fav_tweets:
    fav_tweets_db.insert_one(tweet)


# Load legislator tweets
legislator_tweets = create_tweets_dictionary(party_dict=leg_party_dict,
                                             tweet_list=leg_tweet_en)

leg_tweets_db = client.twitter_db.legislator_tweets_dict
for tweet in legislator_tweets:
    leg_tweets_db.insert_one(tweet)


# Load train_test groups
with open('data/interim/train_test.pickle', 'rb') as file:
    train_test = pickle.load(file)

train_test_db = client.twitter_db.train_test_dict
for tweet in train_test:
    train_test_db.insert_one(tweet)
