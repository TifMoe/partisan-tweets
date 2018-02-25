import yaml
import tweepy
import time
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


def create_list_twitter_accts(social_json):
    """
    Create a list of all twitter accounts associated with current legislators
    :param social_json: List of json data for congressional social media accounts
    :return: List of twitter screen names for current congressional legislators
    """
    twitter_accounts = []

    for i in range(0, len(social_json)):
        try:
            twitter_accounts.append(social_json[i]['social']['twitter'])
        except KeyError:
            pass

    return twitter_accounts


# Create class to access Twitter API
class TwAPI:

    def __init__(self,
                 access_token,
                 access_token_secret,
                 consumer_key,
                 consumer_secret):
        """
        Initialize api client
        """
        self.auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        self.auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(self.auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

    @staticmethod
    def limit_handled(cursor):
        while True:
            try:
                yield cursor.next()
            except tweepy.RateLimitError:
                time.sleep(15 * 60)

    def fetch_user_favorites(self, screen_name):
        """"
        Takes in a twitter screen name and returns all tweet data in json format for tweets created in the past X days
        Parameter 'include_rts' to exclude or include retweets
        Returns a list of json tweets
        """
        fav_list = []

        cursor = tweepy.Cursor(self.api.favorites,
                               screen_name=screen_name,
                               wait_on_rate_limit=True,
                               count=200).items(200)

        for tweet in self.limit_handled(cursor.items()):
            fav_list.append(tweet._json)

        return fav_list

    def fetch_user_timeline(self, screen_name, last_date, include_rts=False):
        """"
        Takes in a twitter screen name and returns all tweet data in json format for tweets created in the past X days
        Parameter 'include_rts' to exclude or include retweets
        Returns a list of json tweets
        """
        tweet_list = []

        cursor = tweepy.Cursor(self.api.user_timeline, screen_name=screen_name,
                               include_rts=include_rts, tweet_mode="extended", count=200)
        tweets = self.limit_handled(cursor.items())

        for tweet in tweets:
            if tweet.created_at > last_date:
                tweet_list.append(tweet._json)
            else:
                return tweet_list

    def fetch_all_timelines(self, screen_names, last_date, include_rts=False):
        """
        Take in list of twitter screen names and fetch all tweets occurring in the past X days
        :param screen_names: list of twitter screen names
        :param days_ago: number of days to pull tweets from
        :param include_rts: boolean indicator to include retweets
        :return: list of tweets for accounts in list occurring in the past X days
        """
        timeline_list = []

        for index, name in enumerate(screen_names):

            try:
                timeline = self.fetch_user_timeline(screen_name=name, last_date=last_date,
                                                    include_rts=include_rts)
                if timeline:
                    timeline_list.extend(timeline)

            except tweepy.error.TweepError as e:
                if e.response.status_code == 404:
                    pass
                else:
                    raise e

        return timeline_list


api = TwAPI(consumer_key=config.get('TwitterKeys', 'consumer_key'),
            consumer_secret=config.get('TwitterKeys', 'consumer_secret'),
            access_token=config.get('TwitterKeys', 'access_token'),
            access_token_secret=config.get('TwitterKeys', 'access_token_secret'))

twitter_sc_names = create_list_twitter_accts(social)
week_ago = datetime.now() - timedelta(days=7)

time_lines = api.fetch_all_timelines(screen_names=twitter_sc_names,
                                     last_date=week_ago,
                                     include_rts=False)

with gzip.open('data/raw/raw_tweets.pickle', 'wb') as file:
    pickle.dump(time_lines, file)


test = twitter_sc_names[0]
test_fav = api.fetch_user_favorites(screen_name=test)
