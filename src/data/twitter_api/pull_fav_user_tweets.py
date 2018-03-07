from datetime import timedelta, datetime
import pandas as pd
from src.data.twitter_api.twitter_functions import TwAPI
from configparser import ConfigParser
import gzip
import pickle

config = ConfigParser()
config.read('config.ini')

# Find tweets of favorited users
users = pd.read_pickle('data/interim/favorited_users.pickle')
week_ago = datetime.now() - timedelta(days=7)

# Find favorites
api = TwAPI(consumer_key=config.get('TwitterKeys', 'consumer_key'),
            consumer_secret=config.get('TwitterKeys', 'consumer_secret'),
            access_token=config.get('TwitterKeys', 'access_token'),
            access_token_secret=config.get('TwitterKeys', 'access_token_secret'))


fav_time_lines = api.fetch_all_timelines(screen_names=users['user.screen_name'],
                                         last_date=week_ago,
                                         include_rts=False)

with gzip.open('data/raw/raw_favs.pickle', 'wb') as file:
    pickle.dump(fav_time_lines, file)