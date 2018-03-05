import gzip
import pickle
import yaml
from sqlalchemy import create_engine
import pandas as pd
from datetime import timedelta, datetime
from src.data.twitter_functions import TwAPI, create_list_twitter_accts
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

with open('congress-legislators/legislators-social-media.yaml', 'r') as f:
    social = yaml.load(f)

twitter_sc_names = create_list_twitter_accts(social)


# Find favorites
api = TwAPI(consumer_key=config.get('TwitterKeys', 'consumer_key'),
            consumer_secret=config.get('TwitterKeys', 'consumer_secret'),
            access_token=config.get('TwitterKeys', 'access_token'),
            access_token_secret=config.get('TwitterKeys', 'access_token_secret'))


favorites = api.fetch_all_favorites(screen_names=twitter_sc_names)

with gzip.open('data/raw/raw_favorites.pickle', 'wb') as file:
    pickle.dump(favorites, file)

wide_fav_df = pd.io.json.json_normalize(favorites)

favorites_df = wide_fav_df.loc[:, ['created_at', 'favorite_count', 'favorited_by',
                                   'text', 'user.description', 'user.screen_name']]

favorites_df.to_pickle('data/interim/favorites_df.pickle')

# Apply party labels for legislators doing the favoriting and ignore users with mixed favorites


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


def find_legislator_parties(list_social):
    """
    Take a list of twitter accounts and return a dictionary with the corresponding party label
    """
    engine = db_create_engine(config_file='config.ini', conn_name='PostgresConfig')
    result = engine.execute(legislator_parties_sql)
    party_dict = {row[0]: row[1] for row in result}

    return party_dict


party_dict = find_legislator_parties(social)

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
print(party_wide[['max_percent', 'max_count', 'party']].sort_values(by='max_count', ascending=True).head(25))

print(party_wide.groupby('max_percent')['party'].count())
print(party_wide.groupby('max_count')['party'].count())

""" Assumptions to define relevant favorites:
- Either favorited by a Republican or Democrat
- At least 99% of favorites in same party
- 

"""
# I'm going to throw away any favorites that have less than 99% same-party favorites
# I'm going to ignore any users with Independent party
# I'm going to ignore any favorited users who are primary users (official legislators)
# I'm going to

party_wide['official'] = [True if name.lower() in party_dict else False for name in party_wide.index]

users = party_wide.loc[((party_wide['max_percent'] >= 99) & (party_wide['party'] != 'I') & ~party_wide['official']), :]
users.reset_index(inplace=True)

users.to_pickle('data/interim/favorited_users.pickle')

# Find tweets of favorited users

users = pd.read_pickle('data/interim/favorited_users.pickle')
week_ago = datetime.now() - timedelta(days=7)

fav_time_lines = api.fetch_all_timelines(screen_names=users['user.screen_name'],
                                         last_date=week_ago,
                                         include_rts=False)

with gzip.open('data/raw/raw_favs.pickle', 'wb') as file:
    pickle.dump(fav_time_lines, file)