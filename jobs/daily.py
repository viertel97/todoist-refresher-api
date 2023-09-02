import os
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter
from fastapi import Path
from quarter_lib.logging import setup_logging
from helper.config_helper import get_value
from helper.database_helper import create_server_connection
from services.database_service import add_or_update_row_koreader_book, add_or_update_row_koreader_page_stat
from services.microsoft_service import get_koreader_settings
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
    update_habit_tracker_vacation_mode, get_page_for_date,
)
from services.sqlite_service import get_koreader_page_stat, get_koreader_book
from services.todoist_service import (
    TODOIST_API,
    add_before_tasks,
    get_vacation_mode, add_after_vacation_tasks
)

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
@router.post("/monica_for_following_days/{days_in_future}")
def monica_for_following_days(days_in_future: Annotated[int, Path(title="The ID of the item to get")]):
    logger.info("start daily - monica (preparation for tomorrow)")
    events = get_events()
    events_tomorrow, selected_date = was_at_day(events, days_in_future)
    logger.info(
        "number of appointments at date ({date}): {length}".format(date=selected_date, length=str(len(events_tomorrow)))
    )
    activities = get_activities(days_in_future)
    logger.info(
        "number of activities at date ({date}): {length}".format(date=selected_date, length=str(len(activities)))
    )
    list_of_calendar_events = [event[1] for event in events_tomorrow if event[1] is not None]
    # if len(activities) > 0:
    #    activities = update_activities_without_date(activities)
    if len(activities) > 0 or len(list_of_calendar_events) > 0:
        add_before_tasks(activities, events_tomorrow)
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


def filter_event(summary):
    return not (any(ext == summary for ext in filter_list) or any(ext in summary for ext in filter_list_in))


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
