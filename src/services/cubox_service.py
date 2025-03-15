import re
import time
from datetime import datetime

import numpy as np
import pandas as pd
import yaml
from dateutil import parser
from quarter_lib.logging import setup_logging

from src.helper.path_helper import slugify
from src.services.book_note_service import add_rework_tasks
from src.services.github_service import add_files_to_repository, get_files
from src.services.notion_service import NOTION_IDS, get_database, update_notion_page_checkbox
from src.services.todoist_service import THIS_WEEK_PROJECT_ID, add_todoist_task

logger = setup_logging(__file__)

OBSIDIAN_AUTOSTART_TRIGGER = "Obsidian-Eintrag überdenken"


COLLECTIONS_ID = NOTION_IDS["COLLECTIONS_ID"]
ANNOTATIONS_ID = NOTION_IDS["ANNOTATIONS_ID"]

GROUP_COLUMNS = sorted([
	"id_collection",
	"created_collection",
	"description",
	"folder",
	"type",
	"cubox_deep_link_collection",
	"updated_collection",
	"title",
])


def get_collections_data(done_reading=True, synced_to_obsidian=False) -> pd.DataFrame:
	df_collections = get_database(COLLECTIONS_ID)
	df_collections = df_collections[df_collections["properties~Done~formula~boolean"] == done_reading]
	df_collections = df_collections[df_collections["properties~SyncedToObsidian~checkbox"] == synced_to_obsidian]
	df_collections["title"] = df_collections["properties~Title~title"].apply(lambda x: x[0]["plain_text"])
	df_collections = df_collections[
		[
			"id",
			"properties~Created~date~start",
			"properties~Description~rich_text",
			"properties~Done~formula~boolean",
			"properties~Original Link~url",
			"properties~Folder~rich_text",
			"properties~Type~select~name",
			"properties~Cubox Deep Link~url",
			"properties~Tags~multi_select",
			"properties~Updated~date~start",
			"title",
		]
	]

	df_collections.rename(
		columns={
			"properties~Created~date~start": "created",
			"properties~Description~rich_text": "description",
			"properties~Done~formula~boolean": "done",
			"properties~Original Link~url": "original_link",
			"properties~Folder~rich_text": "folder",
			"properties~Type~select~name": "type",
			"properties~Cubox Deep Link~url": "cubox_deep_link",
			"properties~Tags~multi_select": "tags",
			"properties~Updated~date~start": "updated",
		},
		inplace=True,
	)

	df_collections["tags"] = df_collections["tags"].apply(lambda x: [y["name"] for y in x])
	df_collections["folder"] = df_collections["folder"].apply(lambda x: x[0]["plain_text"])
	df_collections["description"] = df_collections["description"].apply(lambda x: x[0]["plain_text"] if x else "")
	return df_collections


def get_annotations_data() -> pd.DataFrame:
	df_annotations = get_database(ANNOTATIONS_ID)
	df_annotations["source"] = df_annotations["properties~Source~title"].apply(lambda x: x[0]["plain_text"])
	df_annotations = df_annotations[
		[
			"id",
			"properties~Created~date~start",
			"properties~Cubox Deep Link~url",
			"properties~Note~rich_text",
			"properties~Highlight~rich_text",
			"properties~Updated~date~start",
			"source",
		]
	]

	df_annotations.rename(
		columns={
			"properties~Created~date~start": "created",
			"properties~Cubox Deep Link~url": "cubox_deep_link",
			"properties~Note~rich_text": "note",
			"properties~Highlight~rich_text": "highlight",
			"properties~Updated~date~start": "updated",
		},
		inplace=True,
	)
	df_annotations["note"] = df_annotations["note"].apply(lambda x: x[0]["plain_text"] if x else "")
	df_annotations["highlight"] = df_annotations["highlight"].apply(lambda x: x[0]["plain_text"])
	df_annotations["created"] = pd.to_datetime(df_annotations["created"])
	return df_annotations


def get_merged_cubox_data():
	df_collections = get_collections_data(done_reading=True, synced_to_obsidian=False)
	df_annotations = get_annotations_data()

	df_merge = df_annotations.merge(df_collections, left_on="source", right_on="title", suffixes=("_annotation", "_collection"))
	# sort columns alphabetically
	df_merge = df_merge.reindex(sorted(df_merge.columns), axis=1)
	return df_merge


def generate_content_from_annotations(annotations: pd.DataFrame, list_of_tasks: list) -> tuple[str, list]:
	content = ""
	content += f"# {annotations.iloc[0]['source']}\n\n"
	for _, row in annotations.iterrows():
		content += f'{row["created_annotation"].strftime("%Y-%m-%d %H:%M:%S")}: "{row["highlight"].strip()}" [Link]({row["cubox_deep_link_annotation"]})\n'
		text = '"{text}" [Link]({link}) - {row} - {OBSIDIAN_AUTOSTART_TRIGGER}'.format(
			text=row["highlight"].strip(),
			link=row["cubox_deep_link_annotation"],
			row=row["source"].replace("-", " ").replace("  ", " "),
			OBSIDIAN_AUTOSTART_TRIGGER=OBSIDIAN_AUTOSTART_TRIGGER,
		)
		if row["note"]:
			content += f"> {row['note']}\n\n"
			list_of_tasks.append((text, row["note"]))
		else:
			list_of_tasks.append(text)

		content += "\n"
	return content, list_of_tasks


async def add_cubox_annotations_to_obsidian() -> None:
	df_merge = get_merged_cubox_data()
	list_of_files, list_of_tasks = [], []
	for group_keys, annotations in df_merge.groupby(GROUP_COLUMNS):
		group_dict = dict(zip(GROUP_COLUMNS, group_keys))
		tags = set([f'"{item}"' for sublist in annotations["tags"].tolist() for item in sublist])
		tags_string = ", ".join(tags)
		logger.info(f"Processing group: {group_dict['title']}")
		metadata_json = {
			"summary": group_dict["title"],
			"created_at": parser.parse(group_dict["created_collection"]).strftime("%Y-%m-%d %H:%M:%S"),
			"updated_at": parser.parse(group_dict["updated_collection"]).strftime("%Y-%m-%d %H:%M:%S"),
			"type": group_dict["type"],
			"tags": f"[{tags_string}]",  # Assuming `tags` is part of the grouped DataFrame
			"folder": group_dict["folder"],
			"cubox_deep_link": group_dict["cubox_deep_link_collection"],
			"source": "Cubox",
		}
		if annotations.iloc[0]["original_link"]:
			metadata_json["original_link"] = annotations.iloc[0]["original_link"]
		metadata_json = {k: v.strip() if isinstance(v, str) else v for k, v in metadata_json.items()}

		return_string = "---\n"
		return_string += yaml.dump(metadata_json, allow_unicode=True, default_flow_style=False)
		return_string = return_string.replace("tags: '[", "tags: [").replace("]'", "]")

		return_string += "---\n\n"
		content, list_of_tasks = generate_content_from_annotations(annotations, list_of_tasks)
		list_of_files.append({"filename": f"{slugify(group_dict['title'])}.md", "content": return_string})

		update_checkbox_result = update_notion_page_checkbox(group_dict["id_collection"], "SyncedToObsidian", True)
		logger.info(update_checkbox_result)
		logger.info(f"Updated Notion page {group_dict['id_collection']} for {group_dict['title']}")
		time.sleep(5)

	# files_in_repo = get_files(f"0200_Sources/Websites")

	if list_of_files:
		add_files_to_repository(list_of_files, f"obsidian-refresher: {datetime.now()}", "0200_Sources/Websites/")
		logger.info("Files added to repository")
		await add_rework_tasks(list_of_tasks)
		logger.info("Tasks added to rework list")
	else:
		logger.info("No files to add to repository")


CARD_ID_REGEX = r"id=(\d+)"


def get_mobile_deep_link(cubox_deep_link: str) -> str:
	card_id = re.search(CARD_ID_REGEX, cubox_deep_link).group(1)
	if card_id:
		return f"cubox://card?id={card_id}"
	return ""


def add_cubox_reading_task_to_todoist(weighted=True) -> None:
	df_collections = get_collections_data(done_reading=False, synced_to_obsidian=False)
	df_collections.sort_values("created", ascending=False, inplace=True)
	df_collections["cubox_deep_link_mobile"] = df_collections["cubox_deep_link"].apply(lambda x: get_mobile_deep_link(x))

	if weighted:
		weights = np.linspace(1, 0, len(df_collections))
		weights /= weights.sum()
		df_collections = df_collections.sample(1, weights=weights)
	else:
		df_collections = df_collections.sample(1)
	for _, row in df_collections.iterrows():
		logger.info(f"Adding reading task for {row['title']}")
		result = add_todoist_task(
			f"[{row['title']}]({row['cubox_deep_link_mobile']}) - [Link]({row['cubox_deep_link']})",
			labels=["Digital"],
			project_id=THIS_WEEK_PROJECT_ID,
			due_string="Today",
			due_lang="en",
		)
		logger.info(f"Task added: {result!s}")
