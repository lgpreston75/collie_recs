import pandas as pd
import pytest

from collie_recs.interactions import Interactions


@pytest.fixture()
def interactions_to_split():
    df = pd.DataFrame(data={
        'user_id': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 4, 4, 4, 4],
        'item_id': [0, 1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 4, 1, 2, 4, 5],
        'rating': [1, 2, 3, 4, 5, 4, 3, 2, 1, 1, 2, 3, 4, 2, 3, 4, 5, 1, 5, 4, 2, 3, 5, 4]
    })

    return Interactions(users=df['user_id'],
                        items=df['item_id'],
                        ratings=df['rating'],
                        check_num_negative_samples_is_valid=False)


@pytest.fixture()
def interactions_to_split_with_a_user_with_only_one_interaction():
    df = pd.DataFrame(data={
        'user_id': [0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4],
        'item_id': [0, 1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 1, 2, 3, 4, 1, 1, 2, 4, 5],
        'rating': [1, 2, 3, 4, 5, 4, 3, 2, 1, 1, 2, 3, 4, 2, 3, 4, 5, 1, 2, 3, 5, 4]
    })

    return Interactions(users=df['user_id'],
                        items=df['item_id'],
                        ratings=df['rating'],
                        check_num_negative_samples_is_valid=False)
