import requests
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

from src.helper.caching import ttl_cache

logger = setup_logging(__file__)

(MASTER_KEY, REWORK_EVENTS_BIN, CATEGORIES_BIN, HABIT_LIST_BIN, NOTION_IDS_BIN, DISTANCES_BIN) = get_secrets(
	[
		"jsonbin/masterkey",
		"jsonbin/Rework-Events-bin",
		"jsonbin/categories-bin",
		"jsonbin/habit_list-bin",
		"jsonbin/notion_ids-bin",
		"jsonbin/default_distances-bin",
	]
)

BASE_URL = "https://api.jsonbin.io/v3"

REWORK_EVENTS_URL = f"{BASE_URL}/b/{REWORK_EVENTS_BIN}/latest"
CATEGORIES_URL = f"{BASE_URL}/b/{CATEGORIES_BIN}/latest"
HABITS_URL = f"{BASE_URL}/b/{HABIT_LIST_BIN}/latest"
NOTION_IDS_URL = f"{BASE_URL}/b/{NOTION_IDS_BIN}/latest"
DISTANCES_URL = f"{BASE_URL}/b/{DISTANCES_BIN}/latest"


@ttl_cache(ttl=60 * 60)
def get_rework_data_from_web():
	logger.info("getting rework data from web")
	response = requests.get(
		REWORK_EVENTS_URL,
		headers={"User-Agent": "Mozilla/5.0", "X-Master-Key": MASTER_KEY},
	)
	return response.json()["record"]


@ttl_cache(ttl=60 * 60)
def get_habits_from_web():
	logger.info("get habits data from web")
	response = requests.get(HABITS_URL, headers={"User-Agent": "Mozilla/5.0", "X-Master-Key": MASTER_KEY})
	return response.json()["record"]


@ttl_cache(ttl=60 * 60)
def get_distance_entries_from_web():
	logger.info("get habits data from web")
	response = requests.get(DISTANCES_URL, headers={"User-Agent": "Mozilla/5.0", "X-Master-Key": MASTER_KEY})
	return response.json()["record"]


def get_categories_data_from_web():
	logger.info("get categories data from web")
	response = requests.get(
		CATEGORIES_URL,
		headers={"User-Agent": "Mozilla/5.0", "X-Master-Key": MASTER_KEY},
	)
	return response.json()["record"]


def get_notion_ids_from_web():
	logger.info("get notion ids data from web")
	response = requests.get(
		NOTION_IDS_URL,
		headers={"User-Agent": "Mozilla/5.0", "X-Master-Key": MASTER_KEY},
	)
	return response.json()["record"]


def save_categories_data_to_web(data):
	logger.info("saving categories data to web")
	response = requests.put(
		CATEGORIES_URL.replace("/latest", ""),
		json=data,
		headers={"User-Agent": "Mozilla/5.0", "X-Master-Key": MASTER_KEY},
	)
	return response.json()
