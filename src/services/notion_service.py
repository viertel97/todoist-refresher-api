import json
import time
import urllib.parse
from datetime import datetime, timedelta

import pandas as pd
import pytz
import requests
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

from src.helper.config_helper import get_config, get_value
from src.helper.web_helper import get_notion_ids_from_web
from src.services import todoist_history_service
from src.services.todoist_service import (
	DAILY_SECTION_ID,
	THIS_WEEK_PROJECT_ID,
	TODOIST_API,
	generate_reminders,
	move_item_to_section,
	update_task_due,
)

logger = setup_logging(__file__)

NOTION_TOKEN = get_secrets(["notion/token"])

BASE_URL = "https://api.notion.com/v1/"
HEADERS = {
	"Authorization": "Bearer " + NOTION_TOKEN,
	"Content-Type": "application/json",
	"Notion-Version": "2021-08-16",
}

NOTION_IDS = get_notion_ids_from_web()

ARTICLES_ID = NOTION_IDS["ARTICLES_ID"]
TPT_ID = NOTION_IDS["TPT_ID"]


DATABASES = get_config("databases_config.json")
UNWANTED_COLUMNS = [
	"Date",
	"Day of Week",
	"Kater",
	"Month",
	"Month-Number",
	"Name",
	"R DATE",
	"RELATIVE DATE NUMBER",
	"RELATIVE DATE NUMBER - WEEK",
	"This-Week",
]


def get_database(database_id):
	url = BASE_URL + "databases/" + database_id + "/query"
	result_list = []
	body = None
	while True:
		r = (
			requests.post(url, headers=HEADERS).json()
			if body is None
			else requests.post(url, data=json.dumps(body), headers=HEADERS).json()
		)
		for results in r["results"]:
			result_list.append(results)
		body = {"start_cursor": r.get("next_cursor")}
		if not r["has_more"]:
			break
	logger.info("length of result_list: " + str(len(result_list)))
	return pd.json_normalize(result_list, sep="~")


def get_priorities(df):
	df = df[df["properties~Priority~number"] > 0]
	return df.sample(frac=1).reset_index(drop=True).sort_values("properties~Priority~number").reset_index(drop=True).iloc[0]


def get_title(row):
	title = ""
	for single_title in row:
		if "text" in single_title.keys():
			title += single_title["text"]["content"]
		if "mention" in single_title.keys():
			title += single_title["plain_text"]
	if title == "":
		title = "No Title"
	return title.strip()


def get_random_row_from_notion_tech_database(database_id):
	df = get_database(database_id)

	df["properties~Name~title~content"] = df["properties~Name~title"].apply(lambda row: get_title(row))
	df = df[df["properties~Synced-to-Todoist~checkbox"] == False]
	df = df[df["properties~Obsolet~checkbox"] == False]
	df = df[df["properties~Status~status~name"] == "Not started"]

	try:
		df = df[
			[
				"id",
				"properties~Name~title~content",
				"properties~Priority~number",
				"properties~Completed~date~start",
				"created_time",
				"last_edited_time",
				"url",
			]
		]
		df["properties~Completed~date~start"] = pd.to_datetime(df["properties~Completed~date~start"])
		df = df[df["properties~Completed~date~start"].isnull()]
	except Exception:
		df = df[
			[
				"id",
				"properties~Name~title~content",
				"properties~Priority~number",
				"properties~Completed~date~start",
				"created_time",
				"last_edited_time",
				"url",
			]
		]
		df["properties~Completed~date~start"] = df["properties~Completed~date"]
		df = df[
			[
				"id",
				"properties~Name~title~content",
				"properties~Priority~number",
				"properties~Completed~date~start",
				"created_time",
				"last_edited_time",
				"url",
			]
		]
	selected_row = get_priorities(df)
	return selected_row


def get_random_row_from_link_list(database_id):
	df = get_database(database_id)
	df["properties~Name~title~content"] = df["properties~Name~title"].apply(
		lambda row: row[0]["text"]["content"] if len(row) > 0 else "No Title"
	)
	try:
		df = df[
			[
				"id",
				"properties~Name~title~content",
				"properties~Synced-to-Todoist~checkbox",
				"properties~URL~url",
				"properties~Dates Read~date~start",
				"properties~Priority~number",
				"properties~Pages~number",
				"properties~Not-Available~checkbox",
				"created_time",
				"last_edited_time",
			]
		]
		df["properties~Dates Read~date~start"] = pd.to_datetime(df["properties~Dates Read~date~start"])
		df = df[df["properties~Dates Read~date~start"].isnull()]
	except Exception:
		df["properties~Dates Read~date~start"] = df["properties~Dates Read~date"]
		df = df[
			[
				"id",
				"properties~Name~title~content",
				"properties~Synced-to-Todoist~checkbox",
				"properties~URL~url",
				"properties~Dates Read~date~start",
				"properties~Priority~number",
				"properties~Pages~number",
				"properties~Not-Available~checkbox",
				"created_time",
				"last_edited_time",
			]
		]
	df = df[df["properties~Synced-to-Todoist~checkbox"] == False]
	df = df[df["properties~Not-Available~checkbox"] == False]
	selected_row = get_priorities(df)
	return selected_row


def update_notion_page(page_id):
	url = BASE_URL + "pages/" + page_id
	data = {"properties": {"Synced-to-Todoist": {"checkbox": True}}}
	requests.patch(url, data=json.dumps(data), headers=HEADERS).json()


def update_notion_page_checkbox(page_id, checkbox_name, checkbox_value):
	url = BASE_URL + "pages/" + page_id
	data = {"properties": {checkbox_name: {"checkbox": checkbox_value}}}
	r = requests.patch(url, data=json.dumps(data), headers=HEADERS)
	if r.status_code == 200:
		logger.info("Updated notion page " + page_id + " with checkbox " + checkbox_name)
		return r.json()
	logger.error("Error updating notion page " + page_id + " with checkbox " + checkbox_name)


def get_article_database():
	article_database = get_value("article", "name", DATABASES)["id"]
	url = BASE_URL + "databases/" + article_database + "/query"
	result_list = []
	data = {
		"filter": {
			"and": [
				{"property": "Done", "checkbox": {"equals": False}},
				{"property": "Not-Available", "checkbox": {"equals": False}},
				{"property": "Priority", "number": {"is_not_empty": True}},
				{"property": "Medium", "select": {"is_not_empty": True}},
				{"property": "Topics", "multi_select": {"is_not_empty": True}},
				{
					"property": "Transcribed-And-Uploaded-To-OneDrive",
					"checkbox": {"equals": False},
				},
				{"property": "Language", "select": {"is_not_empty": True}},
			]
		}
	}
	while True:
		r = (
			requests.post(url, headers=HEADERS).json()
			if data is None
			else requests.post(url, data=json.dumps(data), headers=HEADERS).json()
		)
		for results in r["results"]:
			result_list.append(results)
		data = {"start_cursor": r.get("next_cursor")}
		if not r["has_more"]:
			break
	logger.info("length of result_list: " + str(len(result_list)))
	return pd.json_normalize(result_list, sep="~")


def get_article_database_already_downloaded():
	article_database = get_value("article", "name", DATABASES)["id"]
	url = BASE_URL + "databases/" + article_database + "/query"
	result_list = []
	data = {
		"filter": {
			"and": [
				{"property": "Done", "checkbox": {"equals": False}},
				{"property": "Not-Available", "checkbox": {"equals": False}},
				{"property": "Priority", "number": {"is_not_empty": True}},
				{"property": "Medium", "select": {"is_not_empty": True}},
				{"property": "Topics", "multi_select": {"is_not_empty": True}},
				{
					"property": "Transcribed-And-Uploaded-To-OneDrive",
					"checkbox": {"equals": True},
				},
				{"property": "Language", "select": {"is_not_empty": True}},
			]
		}
	}
	while True:
		r = (
			requests.post(url, headers=HEADERS).json()
			if data is None
			else requests.post(url, data=json.dumps(data), headers=HEADERS).json()
		)
		for results in r["results"]:
			result_list.append(results)
		data = {"start_cursor": r.get("next_cursor")}
		if not r["has_more"]:
			break
	logger.info("length of result_list: " + str(len(result_list)))
	return pd.json_normalize(result_list, sep="~")


def get_text_from_article(row):
	url = "https://api.notion.com/v1/blocks/" + row["id"]
	response = requests.get(url, headers=HEADERS).json()
	if not response["has_children"]:
		return None
	url = "https://api.notion.com/v1/blocks/" + row["id"] + "/children"
	response = requests.get(url, headers=HEADERS).json()
	content = ""
	for block in response["results"]:
		if block["type"] == "paragraph":
			content += block["paragraph"]["text"][0]["plain_text"]
	content = content.replace("\n", " ")
	return content


def transform_content(content):
	notion_habit_list = []

	for habit in content.values:
		if habit == "Pomodoro":
			notion_habit_list.append("Pomodoro")
		elif habit == "Vitaminkonzentrat trinken + Omega 3 / Zink  nehmen":
			notion_habit_list.append("Supplements")
		elif habit == "Tasse Tee trinken":
			notion_habit_list.append("Tee")
	return list(dict.fromkeys(notion_habit_list))


def check_habits(data_frame, checked_date):
	logger.info("date: " + str(checked_date.date()))
	local_tz = pytz.timezone("Europe/Berlin")
	start_date = checked_date + timedelta(days=0, hours=6, minutes=0, seconds=0)
	start_date = start_date.replace(tzinfo=None).astimezone(tz=local_tz)
	end_date = (checked_date + timedelta(days=1, hours=6, minutes=0, seconds=0)).replace(tzinfo=None).astimezone(tz=local_tz)
	df = data_frame.loc[(data_frame["event_date"] > start_date) & (data_frame["event_date"] < end_date)]
	return transform_content(df.content)


def get_page_for_date(date, database_id=None):
	if database_id is not None:
		url = BASE_URL + "databases/" + database_id + "/query"
		body = {
			"filter": {
				"property": "Date",
				"date": {"equals": date.strftime("%Y-%m-%d")},
			}
		}

		result_list = []
		while True:
			r = requests.post(url, data=json.dumps(body), headers=HEADERS).json()
			for results in r["results"]:
				result_list.append(results)
			body["start_cursor"] = r.get("next_cursor")
			if not r["has_more"]:
				break
		return pd.json_normalize(result_list, sep="~").iloc[0]


def get_page_for_date_old(date, database_id=None, df=None):
	if df is None and database_id is not None:
		df = get_database(database_id)
	elif df is None and database_id is None:
		raise ValueError("Either database_id or df must be provided")
	return df.loc[df["properties~Date~date~start"] == date.strftime("%Y-%m-%d")].iloc[0]


def update_notion_habit_tracker_page(page_id, completed_habits):
	url = BASE_URL + "pages/" + page_id
	for habit in completed_habits:
		data = {"properties": {habit: {"checkbox": True}}}
		requests.patch(url, data=json.dumps(data), headers=HEADERS).json()
		logger.info("'" + habit + "' checked on page '" + page_id + "'")


def update_notion_habit_tracker():
	acitivites = todoist_history_service.fetch_days_new_new()
	start_date = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
	completed_habits = check_habits(acitivites, start_date)
	habit_tracker_database = get_value("habit_tracker", "name", DATABASES)
	page_id = get_page_for_date(
		datetime.today() - timedelta(days=1),
		habit_tracker_database["id"],
	)["id"]
	update_notion_habit_tracker_page(page_id, completed_habits)


def update_habit_tracker_vacation_mode():
	habit_tracker_database = get_value("habit_tracker", "name", DATABASES)
	page_id = get_page_for_date(
		datetime.today(),
		habit_tracker_database["id"],
	)["id"]
	update_notion_habit_tracker_page(page_id, ["Vacation"])


def get_random_from_notion_database(database_id):
	selected_row = get_random_row_from_notion_tech_database(database_id)
	content = "[" + selected_row["properties~Name~title~content"] + "](" + selected_row["url"] + ")"
	logger.info("update_todoist_and_notion - weekly")
	TODOIST_API.add_task(content, project_id=THIS_WEEK_PROJECT_ID, labels=["Digital"])
	update_notion_page(selected_row["id"])


def get_random_from_notion_articles():
	df = get_article_database_already_downloaded()
	if len(df.index) > 0:
		selected_row = get_priorities(df)
		title = selected_row["properties~Name~title"][0]["plain_text"]
		content = "[" + title + "](" + selected_row["url"] + ")"
		logger.info("update_todoist_and_notion - weekly")
		TODOIST_API.add_task(content, project_id=THIS_WEEK_PROJECT_ID, labels=["Digital"])
		update_notion_page(selected_row["id"])


def get_random_from_notion_link_list(database_id, df_projects=None, due={"string": "Tomorrow"}):
	selected_row = get_random_row_from_link_list(database_id)
	if selected_row["properties~URL~url"]:
		link = selected_row["properties~URL~url"]
	else:
		link = "https://www.google.com/search?q=" + urllib.parse.quote(selected_row["properties~Name~title~content"])

	content = "[" + selected_row["properties~Name~title~content"] + "](" + link + ")"
	logger.info("update_todoist_and_notion - daily")
	if df_projects is None:
		item = TODOIST_API.add_task(content, labels=["Digital"])
		move_item_to_section(item, DAILY_SECTION_ID)
		update_task_due(item, due)
	else:
		item = TODOIST_API.add_task(content, due=due, labels=["Digital"])
		update_task_due(item.id, due)
		generate_reminders(item, due)
	update_notion_page(selected_row["id"])


def add_task_to_notion_database(database_id, todoist_item):
	url = BASE_URL + "pages"
	if todoist_item.description:
		data = {
			"parent": {"database_id": database_id},
			"properties": {
				"Name": {"title": [{"text": {"content": todoist_item.content}}]},
				"Priority": {"type": "number", "number": 0},
			},
			"children": [
				{
					"object": "block",
					"type": "paragraph",
					"paragraph": {
						"rich_text": [
							{
								"type": "text",
								"text": {"content": todoist_item.description},
							}
						]
					},
				}
			],
		}
	else:
		data = {
			"parent": {"database_id": database_id},
			"properties": {
				"Name": {"title": [{"text": {"content": todoist_item.content}}]},
				"Priority": {"type": "number", "number": 0},
			},
		}
	requests.post(url, data=json.dumps(data), headers=HEADERS).json()
	# logger.info(r)


def get_drugs_from_activity(row, drug_date_dict):
	happened_at = row["happened_at"]
	if happened_at in drug_date_dict.keys():
		return drug_date_dict
	drug_tracker_database_id = get_value("drug", "name", DATABASES)["id"]
	url = BASE_URL + "databases/" + drug_tracker_database_id + "/query"
	body = {
		"filter": {
			"property": "Date",
			"date": {"equals": happened_at.strftime("%Y-%m-%d")},
		}
	}

	result_list = []
	while True:
		r = requests.post(url, data=json.dumps(body), headers=HEADERS).json()
		try:
			for results in r["results"]:
				result_list.append(results)
			body["start_cursor"] = r.get("next_cursor")
			if not r["has_more"]:
				break
		except Exception:
			break
	if not len(result_list):
		return drug_date_dict
	result = result_list[0]
	result_properties = result["properties"]
	result_properties = [result_properties[key] for key in result_properties.keys() if key not in UNWANTED_COLUMNS]
	drug_date_dict[happened_at] = []
	for prop in result_properties:
		multi_select = prop["multi_select"]
		for multi_select_item in multi_select:
			drug_date_dict[happened_at].append(multi_select_item["name"])
	return drug_date_dict


def update_priority(id, priority, title):
	url = BASE_URL + "pages/" + id
	data = {"properties": {"Priority": {"number": priority}}}
	r = requests.patch(url, data=json.dumps(data), headers=HEADERS)
	if r.status_code != 200:
		logger.error(r.status_code)
		logger.error(r.text)
	else:
		logger.info(f"Updated priority for '{title}' ({id}) to '{priority}'")
	return r


def stretch_article_list():
	logger.info("stretching Articles")
	df = get_database(ARTICLES_ID)
	logger.info("got Articles")
	df["title"] = df["properties~Name~title"].apply(lambda x: x[0]["plain_text"])
	df.drop(columns=["properties~Name~title"], inplace=True)
	df = df[
		[
			"id",
			"title",
			"properties~Priority~number",
			"properties~Not-Available~checkbox",
			"properties~Done~checkbox",
			"properties~Medium~select~name",
			"properties~Topics~multi_select",
		]
	]
	df.sort_values(by="properties~Priority~number", inplace=True)
	df = df[df["properties~Not-Available~checkbox"] == False]
	df = df[df["properties~Done~checkbox"] == False]
	df = df[df["properties~Priority~number"] > 0]
	df = df[~df["properties~Medium~select~name"].isna()]
	df = df[df["properties~Topics~multi_select"].str.len() != 0]

	df.reset_index(drop=True, inplace=True)
	logger.info("filtered Articles & starting to update")
	for index, row in df.iterrows():
		update_priority(df.iloc[index]["id"], index + 1, df.iloc[index]["title"])
		if (index + 1) % 10 == 0:
			logger.info(f"updated {index + 1} rows")
		if (index + 1) % 30 == 0:
			logger.info(f"updated {index + 1} rows")
		time.sleep(1)
	logger.info("Done updating Articles")


def stretch_project_tasks(database_id):
	logger.info("stretching database with id " + database_id)
	df = get_database(database_id)
	logger.info("got database with id " + database_id)
	df["title"] = df["properties~Name~title"].apply(lambda x: x[0]["plain_text"])
	df.drop(columns=["properties~Name~title"], inplace=True)
	df = df[
		[
			"id",
			"title",
			"properties~Priority~number",
			"properties~Completed~date~start",
			"properties~Obsolet~checkbox",
			"properties~Project~multi_select",
			"properties~Effort~select~name",
			"properties~Status~status~name",
		]
	]
	df.sort_values(by="properties~Priority~number", inplace=True)
	df = df[df["properties~Obsolet~checkbox"] == False]
	df = df[df["properties~Completed~date~start"].isna()]
	df = df[~df["properties~Priority~number"].isna()]
	df = df[~df["properties~Effort~select~name"].isna()]
	df = df[df["properties~Status~status~name"] == "Not started"]
	df = df[df["properties~Project~multi_select"].str.len() != 0]

	df.reset_index(drop=True, inplace=True)
	logger.info("filtered & starting to update with id " + database_id)
	for index, row in df.iterrows():
		update_priority(df.iloc[index]["id"], index + 1, df.iloc[index]["title"])
		if (index + 1) % 10 == 0:
			logger.info(f"updated {index + 1} rows")
		if (index + 1) % 30 == 0:
			logger.info(f"updated {index + 1} rows")
		time.sleep(1)
	logger.info("Done updating database with id " + database_id)
