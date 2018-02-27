from pymongo import MongoClient
import pickle
import gzip
import pandas as pd
from sqlalchemy import create_engine
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


# Find party affiliation for favorites using legislator data in postgres
def db_create_engine(config_file, conn_name):
    """
    Create a sqlAlchemy engine to connect to Postgres database given some connection parameters in config file.
    Note - this can be used to connect to any Postgres db either remotely or locally

    :param config_file: A config file with connection configuration details under conn_name heading
    :param conn_name: The section name for set of configuration details for desired connection
    :return: A sqlAlchemy engine connected to aws postgres database
    """
    config = ConfigParser()
    config.read(config_file)

    engine = create_engine('postgresql://{}:{}@{}:{}/{}'
                           .format(config.get('{}'.format(conn_name), 'user'),
                                   config.get('{}'.format(conn_name), 'password'),
                                   config.get('{}'.format(conn_name), 'host'),
                                   config.get('{}'.format(conn_name), 'port'),
                                   config.get('{}'.format(conn_name), 'db')))

    return engine


legislator_parties_sql = """
        SELECT 
        s.twitter_screen_name, 
        l.party
    FROM legislators l
    JOIN social s
        ON l.legislator_id = s.legislator_id
    WHERE s.twitter_screen_name <>'';
"""

engine = db_create_engine(config_file='config.ini', conn_name='PostgresConfig')
result = engine.execute(legislator_parties_sql)
party_dict = {row[0]: row[1] for row in result}

with open('data/raw/parties.pickle', 'wb') as file:
    pickle.dump(party_dict, file)

favorites = pd.read_pickle('data/interim/favorites_df.pickle')
favorites['party'] = [party_dict[name.lower()] for name in favorites['favorited_by']]

# Check out overlap (user being favorited by both Dem and Repub)
party_group = favorites.groupby(['user.screen_name', 'party'], as_index=False).count()
party_wide = party_group.pivot(index='user.screen_name', columns='party', values='text')
party_wide.fillna(0, inplace=True)

cols = ['Democrat', 'Independent', 'Republican']
percents = ['D', 'I', 'R']

party_wide[percents] = party_wide[cols].div(party_wide[cols].sum(axis=1), axis=0).multiply(100)
party_wide['party'] = party_wide[percents].idxmax(axis=1)
party_wide['max_percent'] = party_wide[percents].max(axis=1).astype(int)
party_wide['max_count'] = party_wide[cols].max(axis=1).astype(int)

print(party_wide[['max_percent', 'max_count', 'party']].sort_values(by='max_count', ascending=False).head(25))
print(party_wide.groupby('max_percent')['party'].count())
print(party_wide.groupby('max_count')['party'].count())
# I'm going to throw away any favorites that have less than 95% same-party favorites
# I'm going to ignore any users with less than 10 favorites
# I'm going to ignore any users with Independent party



favorites_party_list = [(name, party) for index, (name, party)
                                    in favorites[['user.screen_name', 'party']].iterrows()]