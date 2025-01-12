import pandas as pd
from quarter_lib.logging import setup_logging
import json
from dateutil import parser

from src.services.notion_service import get_database, update_notion_page_checkbox, NOTION_IDS
from src.services.todoist_service import add_todoist_task, THIS_WEEK_PROJECT_ID

logger = setup_logging(__file__)


COLLECTIONS_ID = NOTION_IDS["COLLECTIONS_ID"]
ANNOTATIONS_ID = NOTION_IDS["ANNOTATIONS_ID"]

GROUP_COLUMNS = [
	'id_collection',
	'created_collection',
	'description',
	'original_link',
	'folder',
	'type',
	'cubox_deep_link_collection',
	'updated_collection',
	'title'
]

def get_collections_data(done_reading=True, synced_to_obsidian=False) -> pd.DataFrame:
	df_collections = get_database(COLLECTIONS_ID)
	df_collections = df_collections[df_collections["properties~Done~formula~boolean"] == done_reading]
	df_collections = df_collections[df_collections["properties~SyncedToObsidian~checkbox"] == synced_to_obsidian]
	df_collections["title"] = df_collections["properties~Title~title"].apply(lambda x: x[0]["plain_text"])
	df_collections = df_collections[['id', 'properties~Created~date~start',
									 'properties~Description~rich_text', 'properties~Done~formula~boolean',
									 'properties~Original Link~url',
									 'properties~Folder~rich_text',
									 'properties~Type~select~name', 'properties~Cubox Deep Link~url',
									 'properties~Tags~multi_select',
									 'properties~Updated~date~start', 'title']]

	df_collections.rename(columns={"properties~Created~date~start": "created",
								   "properties~Description~rich_text": "description",
								   "properties~Done~formula~boolean": "done",
								   "properties~Original Link~url": "original_link",
								   "properties~Folder~rich_text": "folder",
								   "properties~Type~select~name": "type",
								   "properties~Cubox Deep Link~url": "cubox_deep_link",
								   "properties~Tags~multi_select": "tags",
								   "properties~Updated~date~start": "updated"}, inplace=True)

	df_collections['tags'] = df_collections['tags'].apply(lambda x: [y['name'] for y in x])
	df_collections['folder'] = df_collections['folder'].apply(lambda x: x[0]['plain_text'])
	df_collections['description'] = df_collections['description'].apply(lambda x: x[0]['plain_text'] if x else "")
	return df_collections

def get_annotations_data() -> pd.DataFrame:
	df_annotations = get_database(ANNOTATIONS_ID)
	df_annotations["source"] = df_annotations["properties~Source~title"].apply(lambda x: x[0]["plain_text"])
	df_annotations = df_annotations[['id', 'properties~Created~date~start',
									 'properties~Cubox Deep Link~url', 'properties~Note~rich_text',
									 'properties~Highlight~rich_text', 'properties~Updated~date~start', 'source']]

	df_annotations.rename(columns={"properties~Created~date~start": "created",
								   "properties~Cubox Deep Link~url": "cubox_deep_link",
								   "properties~Note~rich_text": "note",
								   "properties~Highlight~rich_text": "highlight",
								   "properties~Updated~date~start": "updated"}, inplace=True)
	df_annotations['note'] = df_annotations['note'].apply(lambda x: x[0]['plain_text'] if x else "")
	df_annotations['highlight'] = df_annotations['highlight'].apply(lambda x: x[0]['plain_text'])
	return df_annotations

def get_cubox_data():
	df_collections = get_collections_data(done_reading=True,synced_to_obsidian=False)
	df_annotations = get_annotations_data()

	df_merge = df_annotations.merge(df_collections, left_on="source", right_on="title",
									suffixes=('_annotation', '_collection'))
	return df_merge

def add_cubox_annotations_to_obsidian() -> None:
	df_merge = get_cubox_data().sample(frac=1)

	for group_keys, annotations in df_merge.groupby(GROUP_COLUMNS):
		group_dict = dict(zip(GROUP_COLUMNS, group_keys))

		logger.info(f"Processing group: {group_dict['title']}")
		metadata_json = {
			"summary": group_dict['title'],
			"created_at": parser.parse(group_dict['created_collection']).strftime("%d-%m-%Y %H:%M:%S"),
			"updated_at": parser.parse(group_dict['updated_collection']).strftime("%d-%m-%Y %H:%M:%S"),
			"type": group_dict['type'],
			"tags": annotations["tags"].tolist(),  # Assuming `tags` is part of the grouped DataFrame
			"folder": group_dict['folder'],
			"original_link": group_dict['original_link'],
			"cubox_deep_link": group_dict['cubox_deep_link_collection'],
		}

		return_string = "---\n"
		return_string += json.dumps(
			metadata_json, indent=4, sort_keys=True, ensure_ascii=False
		)
		print(return_string)
		# update_notion_page_checkbox(id, "SyncedToObsidian", True)
		# TODO: Obsidian Integration

def add_cubox_reading_task_to_todoist():
	df_collections = get_collections_data(done_reading=False,synced_to_obsidian=False)
	df_collections.sort_values("created_time", ascending=False, inplace=True)

	df_collections = df_collections[:10].sample(1)
	for _, row in df_collections.iterrows():
		logger.info(f"Adding reading task for {row['title']}")
		result = add_todoist_task(f"[{row['title']}]({row['cubox_deep_link']})", labels=["Digital"], project_id=THIS_WEEK_PROJECT_ID, due={"string": "today"})
		logger.info(f"Task added: {result!s}")