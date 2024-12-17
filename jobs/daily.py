from datetime import datetime, timedelta
from typing import Annotated
import copy

from fastapi import APIRouter
from fastapi import Path
from quarter_lib.logging import setup_logging

from helper.config_helper import get_value
from helper.database_helper import create_server_connection
from helper.path_helper import slugify
from helper.web_helper import get_categories_data_from_web, save_categories_data_to_web
from services.database_service import add_or_update_row_koreader_book, add_or_update_row_koreader_page_stat
from services.microsoft_service import get_koreader_settings, upload_transcribed_article_to_onedrive
from services.monica_database_service import add_monica_activities, update_archive
from services.monica_service import (
    add_tasks,
    get_activities,
    get_events,
    was_at_day, get_call_events, get_events_for_days,
)
from services.notion_service import (
    DATABASES,
    get_random_from_notion_link_list,
    update_notion_habit_tracker,
    update_habit_tracker_vacation_mode, get_page_for_date, stretch_project_tasks, stretch_article_list,
    get_article_database, get_text_from_article, update_notion_page_checkbox,
)
from services.sqlite_service import get_koreader_page_stat, get_koreader_book
from services.todoist_service import (
    TODOIST_API,
    add_before_tasks,
    get_vacation_mode, add_after_vacation_tasks
)
from services.tts_service import transcribe

logger = setup_logging(__file__)
router = APIRouter(prefix="/daily", tags=["daily"])

TO_NOTION_LABEL_ID = "2160732004"
TO_MICROJOURNAL_LABEL_ID = "2161901884"

PROJECT_IDS = ["2300202317",
               "2301632406",
               "2302294413",
               "2306562514"]

RETHINK_PROJECT_ID = "2296630360"


def monica(check_for_next_day=False):
    logger.info("start daily - monica (tomorrow)") if check_for_next_day else logger.info(
        "start daily - monica (today)"
    )

    activities = get_activities(0)

    events = get_events_for_days()
    events_today, _ = was_at_day(events, 0, check_for_next_day)
    logger.info("found " + str(len(events_today)) + " Google Calendar events")
    events_today = [event for event in events_today if filter_event(event[0]["summary"])]
    if len(events_today) > 0:
        # TODO: add matched schema so afterwards we can also add
        #  default participants to Todoist and DB-Entry and then remove the Stored Procedure - use "schema_matches"
        add_tasks(TODOIST_API, events_today, activities)
        add_monica_activities(events_today)

    logger.info("end daily - monica (tomorrow)") if check_for_next_day else logger.info("end daily - monica (today)")


@logger.catch
@router.post("/monica-morning")
def monica_morning():
    monica(check_for_next_day=False)


@logger.catch
@router.post("/monica-evening")
def monica_evening():
    monica(check_for_next_day=True)


@logger.catch
@router.post("/monica_before_tasks/{days_in_future}")
def monica_before_tasks(days_in_future: Annotated[int, Path(title="The ID of the item to get")]):
    logger.info("start daily - monica (preparation for today + " + str(days_in_future) + " days)")
    events = get_events()
    events_at_selected_date, selected_date = was_at_day(events, days_in_future)
    logger.info(
        "number of appointments at date ({date}): {length}".format(date=selected_date,
                                                                   length=str(len(events_at_selected_date)))
    )
    activities = get_activities(days_in_future)
    logger.info(
        "number of activities at sdate ({date}): {length}".format(date=selected_date, length=str(len(activities)))
    )
    list_of_calendar_events = [event[1] for event in events_at_selected_date if
                               event[1] is not None]  # because to check if the event has an "before" task
    # if len(activities) > 0:
    #    activities = update_activities_without_date(activities)
    if len(activities) > 0 and len(list_of_calendar_events) > 0:
        add_before_tasks(activities, events_at_selected_date)
    logger.info("end daily - monica (preparation for tomorrow)")


@logger.catch
@router.post("/update_monica_archive")
def update_monica_archive():
    logger.info("start - daily update monica archive")
    update_archive()
    logger.info("end - daily update monica archive")


@logger.catch
@router.post("/update_notion_habit_tracker")
def update_habit_tracker():
    logger.info("start daily - update habit tracker")
    update_notion_habit_tracker()
    logger.info("end daily - update habit tracker")


@logger.catch
@router.post("/vacation_mode_checker")
def vacation_mode_checker():
    logger.info("start - daily vacation mode checker")

    vacation_mode = get_vacation_mode()

    if vacation_mode:
        logger.info("vacation mode: TRUE")
        update_habit_tracker_vacation_mode()
    logger.info("end - daily vacation mode checker")


@logger.catch
@router.post("/notion_habit_tracker_stack")
def notion_habit_tracker_stack():
    logger.info("start - daily notion habit tracker stack")
    habit_tracker_id = get_value("habit_tracker", "name", DATABASES)["id"]
    yesterday = get_page_for_date((datetime.today() - timedelta(days=1)), habit_tracker_id)
    today = get_page_for_date(datetime.today(), habit_tracker_id)
    if yesterday["properties~Vacation~checkbox"] and not today["properties~Vacation~checkbox"]:
        add_after_vacation_tasks()
    # check_order_supplements(df)
    logger.info("end - daily notion habit tracker stack")


@logger.catch
@router.post("/stretch_tpt")
def stretch_tpt():
    logger.info("start daily - stretch tpt")
    database_id = "b3042bf44bd14f40b0167764a0107c2f"
    stretch_project_tasks(database_id)
    logger.info("end daily - stretch tpt")

@logger.catch
@router.post("/stretch_mm")
def stretch_mm():
    logger.info("start daily - stretch mm")
    database_id = "4e5cc9cbbaf741ddbb4b38ac919ae1f1"
    stretch_project_tasks(database_id)
    logger.info("end daily - stretch mm")

@logger.catch
@router.post("/stretch_articles")
def stretch_articles():
    logger.info("start daily - stretch articles")
    stretch_article_list()
    logger.info("end daily - stretch articles")


def links():
    logger.info("start daily - links")

    link_list_database = get_value("link_list", "name", DATABASES)["id"]
    get_random_from_notion_link_list(link_list_database)

    logger.info("end daily - links")


def monica_calls():
    logger.info("start daily - monica (calls)")

    events = get_call_events()

    events = [(event, event['description']) for event in events]
    logger.info("found " + str(len(events)) + " Google Calendar events for calls")
    if len(events) > 0:
        add_tasks(TODOIST_API, events, [])
        add_monica_activities(events)


filter_list = ["K"]
filter_list_in = ["Drive from"]
filter_list_ends_with = ["'s birthday"]


def filter_event(summary):
    # in multiple filters / lines
    filtered_filter_list = any(ext == summary for ext in filter_list)
    filtered_filter_list_ends_with = any(summary.endswith(ext) for ext in filter_list_ends_with)
    filtered_filter_list_in = any(ext in summary for ext in filter_list_in)
    return not (filtered_filter_list or filtered_filter_list_ends_with or filtered_filter_list_in)


def update_koreader_statistics():
    logger.info("start - daily update koreader statistics")
    get_koreader_settings()
    df_books = get_koreader_book()
    df_page_stats = get_koreader_page_stat()

    conn = create_server_connection("private")
    df_books.apply(lambda x: add_or_update_row_koreader_book(x, conn), axis=1)
    df_page_stats.apply(lambda x: add_or_update_row_koreader_page_stat(x, conn), axis=1)
    conn.close()

    logger.info("end - daily update koreader statistics")


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


def umlaut_sort_key(word):
    translation_table = str.maketrans('äöüÄÖÜ', 'aouAOU')
    return word.translate(translation_table)

@logger.catch
@router.post("/order_shopping_list_categories")
async def order_shopping_list_categories():
    logger.info("start daily - order shopping list categories")
    old_categories = get_categories_data_from_web()
    categories = copy.deepcopy(old_categories)

    for section in categories:
        section['items'] = sorted(section['items'], key=umlaut_sort_key)

    if categories != old_categories:
        logger.info("categories changed - saving")
        save_categories_data_to_web(categories)
    else:
        logger.info("categories not changed")
    logger.info("end daily - order shopping list categories")