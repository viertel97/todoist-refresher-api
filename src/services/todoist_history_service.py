from datetime import datetime

import pandas as pd
import requests
from quarter_lib.logging import setup_logging
from quarter_lib.todoist import get_sync_url

from src.helper.web_helper import get_habits_from_web
from src.services.todoist_service import HEADERS

logger = setup_logging(__file__)

HABITS_PROJECT_ID = "6Crcr3mXxHJC2cRQ"
HABITS = get_habits_from_web()
habit_list = [x["name"] for x in HABITS]

COMPLETE_TASKS_LIMIT = 200


def flatten_dict(d, parent_key="", sep="_"):
	"""
	Flatten a dictionary, including nested dictionaries, into a flat dictionary.
	"""
	items = []
	for k, v in d.items():
		new_key = f"{parent_key}{sep}{k}" if parent_key else k
		if isinstance(v, dict):  # If the value is a dictionary, recursively flatten it
			items.extend(flatten_dict(v, new_key, sep=sep).items())
		else:
			items.append((new_key, v))

	# Rebuilding the flattened dictionary after the loop
	return dict(items)


def flatten_list_of_dicts(lst):
	"""
	Flatten a list of dictionaries, where one or more dictionaries might contain nested dictionaries.
	"""
	flattened_list = []
	for item in lst:
		flattened_item = flatten_dict(item)
		flattened_list.append(flattened_item)
	return flattened_list


def get_completed_tasks(since: datetime) -> pd.DataFrame:
	offset = 0
	all_items = []
	try:
		while True:
			response = requests.post(
				get_sync_url("completed/get_all"),
				data={
					"annotate_notes": True,
					"annotate_items": True,
					"since": since.strftime("%Y-%m-%dT%H:%M:%S"),
					"limit": COMPLETE_TASKS_LIMIT,
					"offset": offset,
				},
				headers=HEADERS,
			).json()

			all_items.extend(flatten_list_of_dicts(response["items"]))
			if len(response["items"]) < COMPLETE_TASKS_LIMIT:
				break
			offset += COMPLETE_TASKS_LIMIT
	except Exception as e:
		return pd.DataFrame()
	all_items = [
		{
			k: v
			for k, v in item.items()
			if k
			not in [
				"completed_at",
				"content",
				"id",
				"project_id",
				"section_id",
				"user_id",
				"v2_project_id",
				"v2_section_id",
			]
		}
		for item in all_items
	]
	# flatten
	df = pd.DataFrame(all_items)
	if "item_object_completed_at" in df.columns:
		df["item_object_completed_at"] = pd.to_datetime(df["item_object_completed_at"])
	return df
