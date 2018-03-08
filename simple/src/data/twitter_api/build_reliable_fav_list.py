import pandas as pd
import pickle

with open('data/raw/parties.pickle', 'rb') as file:
    party_dict = pickle.load(file)

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

""" 
Assumptions to define relevant favorites:

- Either favorited by a Republican or Democrat
- At least 99% of favorites in same party
- Not also a current congressional legislator
- At least two tweets favorited by legislator

"""

party_wide['official'] = [True if name.lower() in party_dict else False for name in party_wide.index]

users = party_wide.loc[((party_wide['party'] != 'I') &
                        (party_wide['max_percent'] >= 99) &
                        (~party_wide['official']) &
                        (party_wide['max_count'] > 1)), :]
users.reset_index(inplace=True)

users.to_pickle('data/interim/favorited_users.pickle')

