from fastapi import APIRouter
from quarter_lib.logging import setup_logging

from src.helper.config_helper import get_value
from src.services.github_service import add_to_work_inbox
from src.services.monica_database_service import (
	add_to_be_deleted_activities_to_obsidian,
	get_inbox_activities_to_clean,
)
from src.services.notion_service import (
	DATABASES,
	add_task_to_notion_database,
	WISHLIST_ID,
)
from src.services.obsidian_service import add_to_obsidian_microjournal
from src.services.todoist_service import (
	complete_task,
	get_items_by_todoist_label,
	move_item_to_microjournal_done,
	move_item_to_notion_done,
	move_item_to_work_done,
	set_done_label,
)

logger = setup_logging(__file__)

tags_metadata = [
	{
		"name": "users",
		"description": "Operations with users. The **login** logic is also here.",
	},
	{
		"name": "items",
		"description": "Manage items. So _fancy_ they have their own docs.",
		"externalDocs": {
			"description": "Items external docs",
			"url": "https://fastapi.tiangolo.com/",
		},
	},
]
router = APIRouter(prefix="/hourly", tags=["hourly"])

TO_TPT_LABEL_NAME = "To-TPT"
TO_MM_LABEL_NAME = "To-MM"
TO_WISHLIST_LABEL_NAME = "To-Wishlist"

TO_MICROJOURNAL_LABEL_NAME = "To-Microjournal"
TO_WORK_LABEL_NAME = "To-Work"


@logger.catch
@router.post("/todoist_to_notion_routine")
def todoist_to_tpt_routine():
	logger.info("start - hourly todoist to tpt routine")
	list_to_move = get_items_by_todoist_label(TO_TPT_LABEL_NAME)
	logger.info(f"number of items to move from Todoist to Notion - TPT: {len(list_to_move)!s}")
	tech_database = get_value("tech", "name", DATABASES)["id"]
	for item_to_move in list_to_move:
		add_task_to_notion_database(tech_database, item_to_move)
		move_item_to_notion_done(item_to_move)
		set_done_label(item_to_move, "TPT")
		complete_task(item_to_move)
	logger.info("end - hourly todoist to tpt routine")
	return list_to_move


@logger.catch
@router.post("/todoist_to_microjournal_routine")
def todoist_to_microjournal_routine():
	logger.info("start - hourly todoist to microjournal routine")
	list_to_move = get_items_by_todoist_label(TO_MICROJOURNAL_LABEL_NAME)
	logger.info(f"number of items to move from Todoist to Microjournal: {len(list_to_move)!s}")
	if len(list_to_move) > 0:
		# add_to_monica_microjournal(list_to_move)
		add_to_obsidian_microjournal(list_to_move)
		for item_to_move in list_to_move:
			move_item_to_microjournal_done(item_to_move)
			set_done_label(item_to_move, "Microjournal")
			complete_task(item_to_move)
	logger.info("end - hourly todoist to microjournal routine")


@logger.catch
@router.post("/todoist_to_work_routine")
def todoist_to_work_routine():
	logger.info("start - hourly todoist to work-inbox routine")
	list_to_move = get_items_by_todoist_label(TO_WORK_LABEL_NAME)
	logger.info(f"number of items to move from Todoist to Work: {len(list_to_move)!s}")
	if len(list_to_move) > 0:
		add_to_work_inbox(list_to_move)
		for item_to_move in list_to_move:
			move_item_to_work_done(item_to_move)
			set_done_label(item_to_move, "Work")
	logger.info("end - hourly todoist to work-inbox routine")


@logger.catch
@router.post("/todoist_to_mm_routine")
def todoist_to_mm_routine():
	logger.info("start - hourly todoist to mm routine")
	list_to_move = get_items_by_todoist_label(TO_MM_LABEL_NAME)
	logger.info(f"number of items to move from Todoist to Notion - MM: {len(list_to_move)!s}")
	mm_database = get_value("mindfull_mastery", "name", DATABASES)["id"]
	for item_to_move in list_to_move:
		add_task_to_notion_database(mm_database, item_to_move)
		move_item_to_notion_done(item_to_move)
		set_done_label(item_to_move, "MM")
	logger.info("end - hourly todoist to mm routine")


@logger.catch
@router.post("/todoist_to_wishlist_routine")
def todoist_to_wishlist_routine():
	logger.info("start - hourly todoist to wishlist routine")
	list_to_move = get_items_by_todoist_label(TO_WISHLIST_LABEL_NAME)
	logger.info(f"number of items to move from Todoist to Notion - Wishlist: {len(list_to_move)!s}")
	for item_to_move in list_to_move:
		add_task_to_notion_database(WISHLIST_ID, item_to_move, priority=-1)
		complete_task(item_to_move)
	logger.info("end - hourly todoist to wishlist routine")


@logger.catch
@router.post("/clean_inbox_activities_routine")
async def clean_inbox_activities_routine():
	logger.info("start - hourly clean inbox activities")
	deletion_list = get_inbox_activities_to_clean()
	logger.info(f"number of items to add to obsidian: {len(deletion_list)!s}")
	logger.info("start - add to-be deleted activities to obsidian")
	if len(deletion_list) > 0:
		deleted_list = await add_to_be_deleted_activities_to_obsidian(deletion_list)
	else:
		deleted_list = []
	logger.info("end - add deleted activities to obsidian")
	logger.info("end - hourly clean inbox activities")
	return {"deleted_list": deleted_list}
