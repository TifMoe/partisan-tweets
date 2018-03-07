import pandas as pd
import random
from collections import Counter
import pickle

with open('data/raw/parties.pickle', 'rb') as file:
    leg_party_dict = pickle.load(file)

# Format test/train groups
favorited_users = pd.read_pickle('data/interim/favorites_df.pickle')
favs_groups = favorited_users.loc[:, ['favorited_by', 'user.screen_name']]

legislator_groups_dict = {name.lower(): random.choice(['A', 'B']) for name in list(leg_party_dict.keys())}


def print_class_balance(group_dict, party_dict):
    A = []
    B = []

    for i in group_dict.keys():
        if group_dict[i] == 'A':
            A.append(party_dict[i][0])
        else:
            B.append(party_dict[i][0])

    print("{} in Group A". format(len(A)))
    print(Counter(A))

    print("{} in Group B". format(len(B)))
    print(Counter(B))


print_class_balance(legislator_groups_dict, leg_party_dict)

favs_groups['group'] = [legislator_groups_dict[name.lower()] for name in favs_groups['favorited_by']]

groups = favs_groups.groupby(['user.screen_name', 'group'], as_index=False).count()
groups_wide = groups.pivot(index='user.screen_name', columns='group', values='favorited_by').fillna(0)

# Check out the distribution of mix
groups_wide['group'] = groups_wide[['A', 'B']].idxmax(axis=1)
groups_wide[['A%', 'B%']] = groups_wide[['A', 'B']].div(groups_wide[['A', 'B']].sum(axis=1), axis=0).multiply(100)
Counter(round(groups_wide.loc[groups_wide['group']=='B', 'B%']))

favs_groups_dict = {name.lower(): group for name, group in zip(groups_wide.index, groups_wide['group'])}


def split_a_b(group_dict):
    A = []
    B = []

    for i in list(group_dict.keys()):
        if group_dict[i] == 'A':
            A.append(i)
        else:
            B.append(i)

    return A, B


train_a, train_b = split_a_b(favs_groups_dict)
test_a, test_b = split_a_b(legislator_groups_dict)

train_test_dicts = [{'group': 'train_a', 'screen_names': train_a},
                   {'group': 'train_b', 'screen_names': train_b},
                   {'group': 'test_a', 'screen_names': test_a},
                   {'group': 'test_b', 'screen_names': test_b}]

with open('data/interim/train_test.pickle', 'wb') as file:
    pickle.dump(train_test_dicts, file)