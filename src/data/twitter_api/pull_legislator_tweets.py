import yaml
from src.data.twitter_api.twitter_functions import TwAPI, create_list_twitter_accts
from src.data.mongo_db.db_functions import find_legislator_parties
import gzip
import pickle
from datetime import timedelta, datetime
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

with open('congress-legislators/legislators-current.yaml', 'r') as f:
    legislators = yaml.load(f)

with open('congress-legislators/legislators-social-media.yaml', 'r') as f:
    social = yaml.load(f)


api = TwAPI(consumer_key=config.get('TwitterKeys', 'consumer_key'),
            consumer_secret=config.get('TwitterKeys', 'consumer_secret'),
            access_token=config.get('TwitterKeys', 'access_token'),
            access_token_secret=config.get('TwitterKeys', 'access_token_secret'))

twitter_sc_names = create_list_twitter_accts(social)
month_ago = datetime.now() - timedelta(days=300)

time_lines = api.fetch_all_timelines(screen_names=twitter_sc_names,
                                     last_date=month_ago,
                                     include_rts=False)

with gzip.open('data/raw/raw_tweets_300.pickle', 'wb') as file:
    pickle.dump(time_lines, file)


# Pickle legislator party affiliation
party_dict = find_legislator_parties(social)

with open('data/raw/parties.pickle', 'wb') as file:
    pickle.dump(party_dict, file)
