import os
from datetime import datetime

from fastapi import APIRouter
from quarter_lib.logging import setup_logging

from src.helper import config_helper
from src.services.github_service import get_files, get_files_with_modification_date
from src.services.notion_service import (
	DATABASES,
	get_random_from_notion_link_list,
)
from src.services.todoist_service import get_data, add_obsidian_task_for_note

router = APIRouter(prefix="/bi_monthly", tags=["bi_monthly"])

logger = setup_logging(__file__)



@logger.catch
@router.post("/whole_book_routine")
def whole_book_routine():
	logger.info("start whole_book_routine")

	files = get_files_with_modification_date("0200_Sources/Books")

	now = datetime.now()
	for file in files:
		# int to datetime
		file["created_date"] = datetime.fromtimestamp(file["created_date"])
		file["last_modified_date"] = datetime.fromtimestamp(file["last_modified_date"])

		relative_last_modified_date = (now - file["last_modified_date"]).days
		relative_created_date = (now - file["created_date"]).days



		file["score"] = relative_created_date * 0.6 + relative_last_modified_date * 0.4
		if relative_last_modified_date > 365:
			file["score"] = file["score"] * (relative_last_modified_date / 365)

	sorted_files = sorted(files, key=lambda x: x["score"], reverse=True)

	file = sorted_files[0]

	# check if today is saturday
	if now.weekday() == 5:
		due_string = "today"
	else:
		due_string = "1st Saturday"

	add_obsidian_task_for_note(file["path"], "Oldest book file - time to rework whole book!", due_string=due_string)
	logger.info("selected oldest file '{}'".format(file["path"]))

	logger.info("end whole_book_routine")