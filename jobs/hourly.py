import os

from fastapi import APIRouter
from loguru import logger

from helper.config_helper import get_value
from services.monica_database_service import add_to_microjournal, add_deleted_activities_to_obsidian, \
    clean_inbox_activities
from services.notion_service import (
    DATABASES,
    add_to_technical_project_tasks,
)
from services.todoist_service import (
    get_items_by_todoist_label,
    move_item_to_microjournal_done,
    move_item_to_notion_done,
    get_items_by_content, move_item_to_rethink
)

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

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)

TO_NOTION_LABEL_ID = "2160732004"
TO_MICROJOURNAL_LABEL_ID = "2161901884"
BOOK_REWORK_PROJECT_ID = "2300202317"
BOOK_REWORK_2_PROJECT_ID = "2301632406"
BOOK_REWORK_3_PROJECT_ID = "2302294413"
RETHINK_PROJECT_ID = "2296630360"
CHAT_GPT_LABEL_ID = "2167263122"


@logger.catch
@router.post("/todoist_to_notion_routine")
def todoist_to_notion_routine():
    logger.info("start - daily todoist to notion routine")
    list_to_move = get_items_by_todoist_label(TO_NOTION_LABEL_ID)
    logger.info("number of items to move from Todoist to Notion: {length}".format(length=str(len(list_to_move))))
    tech_database = get_value("tech", "name", DATABASES)["id"]
    for item_to_move in list_to_move:
        add_to_technical_project_tasks(tech_database, item_to_move)
        move_item_to_notion_done(item_to_move)
    logger.info("end - daily todoist to notion routine")


@logger.catch
@router.post("/todoist_to_microjournal_routine")
def todoist_to_microjournal_routine():
    logger.info("start - daily todoist to microjournal routine")
    list_to_move = get_items_by_todoist_label(TO_MICROJOURNAL_LABEL_ID)
    logger.info("number of items to move from Todoist to Microjournal: {length}".format(length=str(len(list_to_move))))
    if (len(list_to_move) > 0):
        add_to_microjournal(list_to_move)
        for item_to_move in list_to_move:
            move_item_to_microjournal_done(item_to_move)
    logger.info("end - daily todoist to microjournal routine")


@logger.catch
@router.post("/todoist_to_rethink_routine")
def todoist_to_rethink_routine():
    logger.info("start - daily todoist to rethink routine")
    list_to_move = get_items_by_content(["?!", "!?"])
    list_to_move.extend(get_items_by_todoist_label(CHAT_GPT_LABEL_ID))

    unique_list_to_move = list({item.content: item for item in list_to_move}.values())

    logger.info(
        "number of items to move from Todoist to Rethink: {length}".format(length=str(len(unique_list_to_move))))
    for item_to_move in unique_list_to_move:
        move_item_to_rethink(item_to_move)
    logger.info("end - daily todoist to rethink routine")


@logger.catch
@router.post("/clean_inbox_activities_routine")
def clean_inbox_activities_routine():
    logger.info("start - daily clean inbox activities")
    deletion_list = clean_inbox_activities()
    logger.info("end - daily clean inbox activities")
    logger.info("number of items to add to obsidian: {length}".format(length=str(len(deletion_list))))
    logger.info("start - add deleted activities to obsidian")
    if len(deletion_list) > 0:
        add_deleted_activities_to_obsidian(deletion_list)
    logger.info("end - add deleted activities to obsidian")
