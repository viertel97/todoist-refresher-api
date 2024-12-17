import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytz
from loguru import logger

from helper.config_helper import get_config
from helper.web_helper import get_habits_from_web
from services.todoist_service import get_todoist_activity

HABITS_PROJECT_ID = str(2244708745)
HABITS = get_habits_from_web()
habit_list = [x["name"] for x in HABITS]

logger.add(
	os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
	format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
	backtrace=True,
	diagnose=True,
)


def df_standardization(df):
	df.client = df.client.astype("category")
	df.content = df.content.astype(str)
	df.due_date = pd.to_datetime(df.due_date)
	df.event_date = pd.to_datetime(df.event_date)
	df.event_date = df.event_date.dt.tz_localize("Europe/Berlin")
	df.event_type = df.event_type.astype("category")
	df.id = df.id.astype(str)
	df.initiator_id = df.initiator_id.astype(str)
	df.last_content = df.last_content.astype(str)
	df.last_due_date = pd.to_datetime(df.last_due_date)
	df.name = df.name.astype(str)
	df.object_id = df.object_id.astype(str)
	df.object_type = df.object_type.astype("category")
	df.parent_item_id = df.parent_item_id.astype(float)
	df.parent_project_id = df.parent_project_id.astype(float)
	return df


def transform_act(act_dict):
	act_dict = act_dict["events"]
	for i in range(len(act_dict)):
		for key, item in act_dict[i]["extra_data"].items():
			act_dict[i][key] = item
		del act_dict[i]["extra_data"]
	act_df = pd.DataFrame(act_dict)
	vnames = [
		"client",
		"content",
		"due_date",
		"event_date",
		"event_type",
		"id",
		"initiator_id",
		"last_content",
		"last_due_date",
		"name",
		"object_id",
		"object_type",
		"parent_item_id",
		"parent_project_id",
	]
	for vname in vnames:
		if vname not in act_df.columns:
			act_df[vname] = np.nan
	return act_df


def fetch_days_new_new():
	logger.info("Fetch activity from Todoist")
	activity = get_todoist_activity(event_type="completed", limit=30, offset=0, parent_project_id=HABITS_PROJECT_ID)
	logger.info("Fetched length: {}".format(len(activity["events"])))
	activity = activity["events"]
	for i in range(len(activity)):
		for key, item in activity[i]["extra_data"].items():
			activity[i][key] = item
		del activity[i]["extra_data"]
	df = pd.DataFrame(activity)
	df["event_date"] = pd.to_datetime(df["event_date"])
	df = df[df.content.isin(habit_list)]
	return df


def fetch_days_new(days=2):
	local_tz = pytz.timezone("Europe/Berlin")
	start = (datetime.now() - timedelta(days=days)).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0).astimezone(tz=local_tz)
	end = (datetime.now() - timedelta(days=1)).replace(tzinfo=None, hour=23, minute=59, second=59, microsecond=9999).astimezone(tz=local_tz)
	goal = (datetime.now() - timedelta(days=days)).replace(tzinfo=None).astimezone(tz=local_tz)
	activity = get_todoist_activity(event_type="completed", limit=20, offset=0, parent_project_id=HABITS_PROJECT_ID)
	activity = activity["events"]
	for i in range(len(activity)):
		for key, item in activity[i]["extra_data"].items():
			activity[i][key] = item
		del activity[i]["extra_data"]
	df = pd.DataFrame(activity)
	df["event_date"] = pd.to_datetime(df["event_date"])
	df = df.loc[(df["event_date"] >= start) & (df["event_date"] <= end)]
	df = df[df.content.isin(habit_list)]
	return df


def fetch_days(days=2):
	local_tz = pytz.timezone("Europe/Berlin")
	goal = (datetime.now() - timedelta(days=days)).replace(tzinfo=None).astimezone(tz=local_tz)
	until = goal + timedelta(seconds=1)
	until_param = goal.strftime("%Y-%m-%dT%H:%M:%S")
	act_df = df_standardization(
		transform_act(
			get_todoist_activity(
				event_type="completed",
				limit=100,
				until=until_param,
				offset=0,
				parent_project_id=HABITS_PROJECT_ID,
			)
		)
	)
	length = len(act_df)
	while until > goal:
		until = act_df.event_date.min() - timedelta(seconds=1)
		until_param = until.strftime("%Y-%m-%dT%H:%M:%S")
		new_df = df_standardization(
			transform_act(
				get_todoist_activity(
					event_type="completed",
					limit=100,
					until=until_param,
					offset=length,
					parent_project_id=HABITS_PROJECT_ID,
				)
			)
		)
		act_df = act_df.append(new_df)
		length = len(act_df)
	act_df = act_df[act_df.content.isin(habit_list)]
	return act_df
