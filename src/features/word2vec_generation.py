import gensim
from configparser import ConfigParser
from pymongo import MongoClient
import src.data.aws_ec2_functions as aws
import re
import string
import pickle
import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import spacy
    nlp = spacy.load('en')



punctuations = string.punctuation
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


def fetch_train_test(train_group, test_group):
    cursor = db.train_test_dict.find({'group': train_group}, { 'screen_names': 1, '_id': 0 })
    train_group = [doc for doc in cursor]

    cursor = db.train_test_dict.find({'group': test_group}, { 'screen_names': 1, '_id': 0 })
    test_group = [doc for doc in cursor]

    cursor = db.fav_tweets_dict.find( { "name": { "$in": train_group[0]['screen_names'] } } )
    train = [doc for doc in cursor]

    cursor = db.legislator_tweets_dict.find( { "name": { "$in": test_group[0]['screen_names'] } } )
    test = [doc for doc in cursor]

    return train, test


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
    clean = re.sub(r'[^\w\s]', '', no_url)

    result = ''.join([str(i).replace('\n', ' ').lower() for i in clean if not i.isdigit()])

    return result


def spacy_tokenizer(tweet):
    """
    Utility function to remove stopwords, ignore pronouns and tokenize words before vectorizing
    """
    doc = nlp(tweet)
    tokens = [token.orth_ for token in doc if not token.is_stop]

    return tokens


train_a, test_b = fetch_train_test('train_a', 'test_b')

train_data = unlist_tweets(train_a)
test_data = unlist_tweets(test_b)

clean_train = [clean_tweet(tweet[0]) for tweet in train_data]
clean_test = [clean_tweet(tweet[0]) for tweet in test_data]

y_train = [1 if tweet[1]=='R' else 0 for tweet in train_data]
y_test = [1 if tweet[1]=='R' else 0 for tweet in test_data]

with open('data/processed/y_train_a.pickle', 'wb') as file:
    pickle.dump(y_train, file)

with open('data/processed/y_test_b.pickle', 'wb') as file:
    pickle.dump(y_test, file)


tokenized_train = [spacy_tokenizer(tweet) for tweet in clean_train]
tokenized_test = [spacy_tokenizer(tweet) for tweet in clean_test]

with open('data/processed/tokenized_train_a.pickle', 'wb') as file:
    pickle.dump(tokenized_train, file)

with open('data/processed/tokenized_test_b.pickle', 'wb') as file:
    pickle.dump(tokenized_test, file)


# let X be a list of tokenized texts (i.e. list of lists of tokens)
model = gensim.models.Word2Vec(tokenized_train, size=100)
w2v = dict(zip(model.wv.index2word, model.wv.vectors))

with open('models/w2v', 'wb') as file:
    pickle.dump(model, file)

with open('data/processed/w2v_dict.pickle', 'wb') as file:
    pickle.dump(w2v, file)