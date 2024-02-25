import os

import requests
from quarter_lib.logging import setup_logging

from helper.caching import ttl_cache

logger = setup_logging(__file__)

HABIT_LIST_URL = os.getenv("habit_list")


@ttl_cache(ttl=60 * 60)
def get_habits_from_web():
    logger.info("getting habits from web")
    response = requests.get(HABIT_LIST_URL, headers={'User-Agent': 'Mozilla/5.0'}, verify=False)
    return response.json()
