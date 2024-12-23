import os
from datetime import datetime

import pandas as pd
from loguru import logger

from services.github_service import add_files_to_repository
from services.grabber_service import create_file_from_dict
from services.llm_service import get_summaries

logger.add(
	os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
	format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
	backtrace=True,
	diagnose=True,
)

if os.name == "nt":
	DEBUG = True
else:
	DEBUG = False


def add_to_obsidian_microjournal(list_to_move):
	df_items = pd.DataFrame([item.__dict__ for item in list_to_move])
	df_items["summary"] = get_summaries(df_items.content)
	df_items["created_at"] = pd.to_datetime(df_items["created_at"]) + pd.Timedelta("01:00:00")
	now = datetime.now()
	list_of_files = []
	for index, row in df_items.iterrows():
		file = create_file_from_dict(row)
		list_of_files.append(file)
	add_files_to_repository(list_of_files, f"todoist-refresher: {now}", "0300_Spaces/Microjournal/")
