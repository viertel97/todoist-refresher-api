import datetime

from fastapi import APIRouter
from quarter_lib.logging import setup_logging

from helper.config_helper import get_value
from services.file_service import read_not_matched_file
from services.ght_service import update_ght
from services.notion_service import (
    DATABASES,
    get_random_from_notion_technical_projects,
)
from services.todoist_service import (
    PROJECT_DICT,
    check_due,
    check_next_week,
    get_data,
    get_dates,
    move_items, add_not_matched_task
)
from services.youtube_service import add_video_annotate_task, add_video_transcribe_tasks

logger = setup_logging(__file__)

router = APIRouter(prefix="/weekly", tags=["weekly"])


@logger.catch
@router.post("/update_todoist_projects")
def update_todoist_projects():
    logger.info("start weekly - todoist projects")

    df_items_due, df_projects, df_items_next_week = get_data()

    week_list = get_dates()
    df_items_due.apply(
        lambda row: check_due(
            row["id"],
            row["due"],
            row["project_id"],
            week_list,
            df_projects,
            PROJECT_DICT,
        ),
        axis=1,
    )
    df_items_next_week.apply(
        lambda row: check_next_week(row["id"], row["project_id"], df_projects, PROJECT_DICT),
        axis=1,
    )
    move_items(PROJECT_DICT, df_projects)
    logger.info("end weekly - todoist projects")


@logger.catch
@router.post("/tpt")
def tpt():
    logger.info("start weekly - tpt")
    tech_database = get_value("tech", "name", DATABASES)["id"]
    get_random_from_notion_technical_projects(tech_database)
    logger.info("end weekly - tpt")


@logger.catch
@router.post("/ght_update")
def ght_update():
    update_ght()


def youtube_tasks():
    logger.info("start weekly - youtube tasks")
    current_calendar_week = datetime.datetime.now().isocalendar()[1]
    if current_calendar_week % 2 == 0:
        result = add_video_transcribe_tasks()
        if not result:
            logger.info("no video to transcribe")
            add_video_annotate_task()
    else:
        result = add_video_annotate_task()
        if not result:
            logger.info("no video to annotate")
            add_video_transcribe_tasks()
    logger.info("end weekly - youtube tasks")


def not_matched_to_todoist():
    logger.info("start not matched to todoist")
    not_matched = read_not_matched_file()
    add_not_matched_task(not_matched)
    logger.info("end not matched to todoist")
