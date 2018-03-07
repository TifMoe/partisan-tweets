import gzip
import pickle
import yaml
import pandas as pd
from src.data.twitter_api.twitter_functions import TwAPI, create_list_twitter_accts
from configparser import ConfigParser
from src.data.mongo_db.db_functions import find_legislator_parties

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
party_dict = find_legislator_parties()

with open('data/raw/parties.pickle', 'wb') as file:
    pickle.dump(party_dict, file)


