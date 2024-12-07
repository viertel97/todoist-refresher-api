from fastapi import APIRouter
from quarter_lib.logging import setup_logging

from helper.config_helper import get_value
from services.github_service import add_to_work_inbox
from services.monica_database_service import add_to_microjournal, add_to_be_deleted_activities_to_obsidian, \
    get_inbox_activities_to_clean
from services.notion_service import (
    DATABASES,
    add_task_to_notion_database,
)
from services.todoist_service import (
    get_items_by_todoist_label,
    move_item_to_microjournal_done,
    move_item_to_notion_done,
    move_item_to_work_done, set_done_label
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

TO_TPT_LABEL_ID = "2160732004"
TO_MM_LABEL_ID = "2170899508"

TO_MICROJOURNAL_LABEL_ID = "2161901884"
TO_WORK_LABEL_ID = "2168502713"
BOOK_REWORK_PROJECT_ID = "2300202317"
BOOK_REWORK_2_PROJECT_ID = "2301632406"
BOOK_REWORK_3_PROJECT_ID = "2302294413"
RETHINK_PROJECT_ID = "2296630360"


@logger.catch
@router.post("/todoist_to_notion_routine")
def todoist_to_tpt_routine():
    logger.info("start - hourly todoist to tpt routine")
    list_to_move = get_items_by_todoist_label(TO_TPT_LABEL_ID)
    logger.info("number of items to move from Todoist to Notion - TPT: {length}".format(length=str(len(list_to_move))))
    tech_database = get_value("tech", "name", DATABASES)["id"]
    for item_to_move in list_to_move:
        add_task_to_notion_database(tech_database, item_to_move)
        move_item_to_notion_done(item_to_move)
        set_done_label(item_to_move, "TPT")
    logger.info("end - hourly todoist to tpt routine")


@logger.catch
@router.post("/todoist_to_microjournal_routine")
def todoist_to_microjournal_routine():
    logger.info("start - hourly todoist to microjournal routine")
    list_to_move = get_items_by_todoist_label(TO_MICROJOURNAL_LABEL_ID)
    logger.info("number of items to move from Todoist to Microjournal: {length}".format(length=str(len(list_to_move))))
    if (len(list_to_move) > 0):
        add_to_microjournal(list_to_move)
        for item_to_move in list_to_move:
            move_item_to_microjournal_done(item_to_move)
            set_done_label(item_to_move, "Microjournal")
    logger.info("end - hourly todoist to microjournal routine")


@logger.catch
@router.post("/todoist_to_work_routine")
def todoist_to_work_routine():
    logger.info("start - hourly todoist to work-inbox routine")
    list_to_move = get_items_by_todoist_label(TO_WORK_LABEL_ID)
    logger.info("number of items to move from Todoist to Work: {length}".format(length=str(len(list_to_move))))
    if (len(list_to_move) > 0):
        add_to_work_inbox(list_to_move)
        for item_to_move in list_to_move:
            move_item_to_work_done(item_to_move)
            set_done_label(item_to_move, "Work")
    logger.info("end - hourly todoist to work-inbox routine")


@logger.catch
@router.post("/todoist_to_mm_routine")
def todoist_to_mm_routine():
    logger.info("start - hourly todoist to mm routine")
    list_to_move = get_items_by_todoist_label(TO_MM_LABEL_ID)
    logger.info("number of items to move from Todoist to Notion - MM: {length}".format(length=str(len(list_to_move))))
    mm_database = get_value("mindfull_mastery", "name", DATABASES)["id"]
    for item_to_move in list_to_move:
        add_task_to_notion_database(mm_database, item_to_move)
        move_item_to_notion_done(item_to_move)
        set_done_label(item_to_move, "MM")
    logger.info("end - hourly todoist to mm routine")


@logger.catch
@router.post("/clean_inbox_activities_routine")
async def clean_inbox_activities_routine():
    logger.info("start - hourly clean inbox activities")
    deletion_list = get_inbox_activities_to_clean()
    logger.info("number of items to add to obsidian: {length}".format(length=str(len(deletion_list))))
    logger.info("start - add to-be deleted activities to obsidian")
    if len(deletion_list) > 0:
        deleted_list = await add_to_be_deleted_activities_to_obsidian(deletion_list)
    else:
        deleted_list = []
    logger.info("end - add deleted activities to obsidian")
    logger.info("end - hourly clean inbox activities")
    return {"deleted_list": deleted_list}
