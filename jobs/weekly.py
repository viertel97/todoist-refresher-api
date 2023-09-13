import asyncio
import datetime
import requests

from fastapi import APIRouter
from quarter_lib.logging import setup_logging
from quarter_lib_old.notion import get_database

from helper.config_helper import get_value
from helper.path_helper import slugify
from services.file_service import read_not_matched_file
from services.ght_service import update_ght
from services.microsoft_service import upload_transcribed_article_to_onedrive
from services.notion_service import (
    DATABASES,
    get_random_from_notion_technical_projects, get_article_database, get_text_from_article, update_notion_page_checkbox,
)
from services.todoist_service import (
    PROJECT_DICT,
    check_due,
    check_next_week,
    get_data,
    get_dates,
    move_items, add_not_matched_task
)
from services.tts_service import transcribe
from services.youtube_service import add_video_annotate_task, add_video_transcribe_tasks

logger = setup_logging(__file__)

router = APIRouter(prefix="/weekly", tags=["weekly"])


@logger.catch
@router.post("/update_todoist_projects")
def update_todoist_projects():
    logger.info("start weekly - todoist projects")

    df_items_due, df_projects, df_items_next_week = get_data()

    temp_project_dict = PROJECT_DICT.copy()

    week_list = get_dates()
    df_items_due.apply(
        lambda row: check_due(
            row["id"],
            row["due"],
            row["project_id"],
            week_list,
            df_projects,
            temp_project_dict,
        ),
        axis=1,
    )
    if len(df_items_next_week.index) > 0:
        df_items_next_week.apply(
            lambda row: check_next_week(row["id"], row["project_id"], df_projects, temp_project_dict),
            axis=1,
        )
    # remove duplicates from project dict
    temp_project_dict = {k: v for k, v in temp_project_dict.items() if v is not None}
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


@logger.catch
@router.post("/article_to_audio_routine")
async def article_to_audio_routine():
    logger.info("start article to audio")
    db = get_article_database()
    for _, row in db.iterrows():
        try:
            text = get_text_from_article(row)
            if text:
                language = row["properties~Language~select~name"]
                filename = slugify(row["properties~Name~title"][0]["plain_text"]) + ".mp3"
                await transcribe(text, language, filename)
                upload_transcribed_article_to_onedrive(filename, row["properties~Website~formula~string"])
                update_notion_page_checkbox(row['id'], "Transcribed-And-Uploaded-To-OneDrive", True)
            else:
                logger.warning(f'no text for {row["properties~Name~title"][0]["plain_text"]}')
        except Exception as e:
            logger.error(f"error for {row['title']}: {e}")