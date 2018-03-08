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
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.naive_bayes import BernoulliNB, MultinomialNB
from sklearn.pipeline import Pipeline
from collections import defaultdict


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


class MeanEmbeddingVectorizer(object):
    def __init__(self, word2vec):
        self.word2vec = word2vec
        # if a text is empty we should return a vector of zeros
        # with the same dimensionality as all the other vectors
        self.dim = len(word2vec.itervalues().next())

    def fit(self, X, y):
        return self

    def transform(self, X):
        return np.array([
            np.mean([self.word2vec[w] for w in words if w in self.word2vec]
                    or [np.zeros(self.dim)], axis=0)
            for words in X
        ])


class TfidfEmbeddingVectorizer(object):
    def __init__(self, word2vec):
        self.word2vec = word2vec
        self.word2weight = None
        self.dim = len(word2vec.itervalues().next())

    def fit(self, X, y):
        tfidf = TfidfVectorizer(analyzer=lambda x: x)
        tfidf.fit(X)
        # if a word was never seen - it must be at least as infrequent
        # as any of the known words - so the default idf is the max of
        # known idf's
        max_idf = max(tfidf.idf_)
        self.word2weight = defaultdict(
            lambda: max_idf,
            [(w, tfidf.idf_[i]) for w, i in tfidf.vocabulary_.items()])

        return self

    def transform(self, X):
        return np.array([
                np.mean([self.word2vec[w] * self.word2weight[w]
                         for w in words if w in self.word2vec] or
                        [np.zeros(self.dim)], axis=0)
                for words in X
            ])


etree_w2v = Pipeline([("word2vec vectorizer", MeanEmbeddingVectorizer(w2v)),
                        ("extra trees", ExtraTreesClassifier(n_estimators=200))])
etree_w2v_tfidf = Pipeline([("word2vec vectorizer", TfidfEmbeddingVectorizer(w2v)),
                        ("extra trees", ExtraTreesClassifier(n_estimators=200))])