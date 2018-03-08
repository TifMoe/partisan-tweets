from configparser import ConfigParser
from pymongo import MongoClient
import re
import string
from collections import defaultdict
import pickle
import src.data.aws_ec2_functions as aws

punctuations = string.punctuation
config = ConfigParser()
config.read('config.ini')

# Make sure AWS Ec2 Instance is running and get public IP address
instance = aws.fetch_instances()[0]


client = MongoClient("mongodb://{}:{}@{}/{}".format(
                        config.get('MongoConfig', 'user'),
                        config.get('MongoConfig', 'password'),
                        instance.public_ip_address,
                        config.get('MongoConfig', 'db'),
                        int(config.get('MongoConfig', 'port'))))

db = client.twitter_db

cursor = db.legislator_tweets_dict.find( {} )
legislators = [doc for doc in cursor]


def unlist_tweets(list_tweet_dicts):
    tweets_labels = []

    for dict in list_tweet_dicts:
        for tweet in dict['tweets']:
            tweets_labels.append([tweet, dict['party']])

    return tweets_labels


def clean_tweet(tweet):
    """
    Function to remove urls, numbers and punctuation, and make lowercase
    """
    no_url = re.sub(r'http\S+', '', tweet)
    no_hashtags = re.sub(r'#\S+', '', no_url)
    no_users = re.sub(r'@\S+', '', no_hashtags)
    no_amp = re.sub(r'&\S+', '', no_users)


    result = ''.join([str(i).replace('\n', ' ') for i in no_amp])

    return result


data = unlist_tweets(legislators)
rep_tweets = [clean_tweet(tweet[0]) for tweet in data if tweet[1]=='R']
dem_tweets = [clean_tweet(tweet[0]) for tweet in data if tweet[1]=='D']


def build_corpus_dict(corpus):
    m_dict = defaultdict(list)
    for sen in corpus:
        for i, word in enumerate(sen.split()):
            if i < len(sen.split())-1:
                m_dict[word].append(sen.split()[i + 1])
            else:
                pass
    return m_dict


republican_dict = build_corpus_dict(rep_tweets)
democrat_dict = build_corpus_dict(dem_tweets)

with open('models/republican_dict.pickle', 'wb') as file:
    pickle.dump(republican_dict, file)

with open('models/democrat_dict.pickle', 'wb') as file:
    pickle.dump(democrat_dict, file)