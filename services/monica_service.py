import json
import os
from datetime import datetime, timedelta, time

import requests
from dateutil import parser
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging
from quarter_lib_old.google import (
    build_calendar_service,
    get_dict,
    get_events_from_calendar,
)
from quarter_lib_old.todoist import move_item_to_project, update_due

from helper.date_helper import get_date_or_datetime
from services.monica_database_service import get_activities_db, get_contacts, get_activity_contact

logger = setup_logging(__file__)

SCOPES = [
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/calendar.readonly",
]
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]
MONICA_TOKEN = get_secrets(['monica/token'])

creds = None
DEBUG = os.name == "nt"


def get_events():
    calendar_service = build_calendar_service()

    calendar_dict = get_dict(calendar_service)

    event_list = []

    event_list.extend(get_events_from_calendar("Janik's Kalender", calendar_dict, calendar_service))
    event_list.extend(get_events_from_calendar("Drug-Kalender", calendar_dict, calendar_service))
    event_list.extend(get_events_from_calendar("Reisen", calendar_dict, calendar_service))
    event_list.extend(get_events_from_calendar("Veranstaltungen", calendar_dict, calendar_service))
    event_list.extend(get_events_from_calendar("♥", calendar_dict, calendar_service))

    return event_list


def get_events_from_calendar_for_days(calendar_name, calendar_dict, calendar_service, days=0):
    event_list = []
    page_token = None

    while True:
        time_min = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
        time_max = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days)
        query_params = {"calendarId": calendar_dict[calendar_name]["id"], "pageToken": page_token,
                        "singleEvents": True,
                        "timeMin": time_min.isoformat() + "Z",
                        "timeMax": time_max.isoformat() + "Z"}

        events = calendar_service.events().list(**query_params).execute()
        for event in events.get("items", []):
            event_list.append(event)

        page_token = events.get("nextPageToken")
        if not page_token:
            break
    logger.info(f"Found {len(event_list)} events for {calendar_name}")
    return event_list


def get_events_for_days(days=2):
    calendar_service = build_calendar_service()

    calendar_dict = get_dict(calendar_service)

    event_list = []

    event_list.extend(get_events_from_calendar_for_days("Janik's Kalender", calendar_dict, calendar_service, days))
    event_list.extend(get_events_from_calendar_for_days("Drug-Kalender", calendar_dict, calendar_service, days))
    event_list.extend(get_events_from_calendar_for_days("Reisen", calendar_dict, calendar_service, days))
    event_list.extend(get_events_from_calendar_for_days("Veranstaltungen", calendar_dict, calendar_service, days))
    event_list.extend(get_events_from_calendar_for_days("♥", calendar_dict, calendar_service, days))

    return event_list


def get_call_events():
    calendar_service = build_calendar_service()

    calendar_dict = get_dict(calendar_service)

    event_list = []
    page_token = None

    while True:
        query_params = {"calendarId": calendar_dict["Anrufverlauf"]["id"], "pageToken": page_token,
                        "singleEvents": True,
                        "timeMin": datetime.today().replace(hour=0, minute=0, second=0).isoformat() + "Z"}

        events = calendar_service.events().list(**query_params).execute()

        for event in events.get("items", []):
            event_list.append(event)

        page_token = events.get("nextPageToken")
        if not page_token:
            break

    return event_list


def was_at_day(event_list, days, check_for_next_day=False):
    events = []
    if days > 0:
        selected_day = (datetime.today() + timedelta(days=days)).date()
    else:
        selected_day = (datetime.today() - timedelta(days=days * -1)).date()
    for event in event_list:
        if event["status"] != "cancelled":
            if check_for_next_day:
                created = parser.parse(event["created"]).replace(tzinfo=None)
                start = datetime.today().replace(hour=7, minute=0, second=0)
                if not (start <= created):
                    continue
            start = get_date_or_datetime(event, "start").replace(tzinfo=None).date()
            end = get_date_or_datetime(event, "end").replace(tzinfo=None).date()
            if (end-start).days >= 1:
                end = end - timedelta(days=1)
            # -1 because end is exclusive
            if start <= selected_day <= end:
                if "description" in event.keys():
                    if "#ignore" not in event["description"]:
                        pre_list = get_pre_from_event(event)
                        events.append((event, pre_list))
                else:
                    events.append((event, None))
    return events, selected_day


DAILY_LINKS_THRESHOLD = time(hour=16)


def is_multiday_event(appointment):
    start = get_date_or_datetime(appointment, "start").replace(tzinfo=None)
    end = get_date_or_datetime(appointment, "end").replace(tzinfo=None)
    if start.date() != end.date():
        # which day of multiday event (eg. 2nd day)
        return (datetime.today().date() - start.date()).days + 1
    return False


def add_tasks(api, appointment_list, activities):
    if len(appointment_list) > 0:
        for appointment, calendar_description in appointment_list:
            logger.info("adding Todoist task: " + str(appointment))
            appointment_time = get_date_or_datetime(appointment, "end")
            if appointment_time.time() <= DAILY_LINKS_THRESHOLD:
                due = {"string": "Today"}
            else:
                due = {"string": "Tomorrow"}
            is_multiday = is_multiday_event(appointment)
            if is_multiday:
                appointment["summary"] = appointment["summary"] + f" (Tag {str(is_multiday)})"
                appointment['happened_at'] = datetime.today().strftime("%Y-%m-%d")
            content = "'" + appointment["summary"] + "'" + " - nacharbeiten & Tracker pflegen"
            logger.info("content: " + str(content))
            description = get_description(activities, calendar_description)
            item = api.add_task(
                content,
                description=description,
                project_id="2271705443",
            )
            logger.info("added Todoist task: " + str(item))
            result_move = move_item_to_project(item.id, project_id="2244725398")
            logger.info("moved Todoist task: " + str(result_move))
            result_update_due = update_due(item.id, due=due)
            logger.info("updated Todoist task: " + str(result_update_due))

            logger.info("added Todoist task: " + str(item))


def get_description(activities, calendar_description=None):
    description_string = ""
    for activity in activities:
        description_string += "* " + activity["summary"] + ": \n"
        description_string += activity["description"].replace("*", "  *")
        description_string += "\n\n"
    if calendar_description is not None:
        description_string += "  * Kalender: \n"
        description_string += calendar_description.replace("*", "    *")
    return description_string


def get_from_api(object_type):
    logger.info("getting monica data: " + str(object_type))
    headers = {"Authorization": "Bearer %s" % MONICA_TOKEN}
    # logger.info("headers: " + str(headers))
    api_url = "http://192.168.178.100:7000/api/"
    objects = []
    page = 1
    while True:
        url = api_url + object_type + "?page=" + str(page) + "&limit=100"
        r = requests.get(url, headers=headers, timeout=100)
        logger.info("getting monica data: " + str(object_type) + " - page " + str(page))
        logger.info("getting monica data: " + str(object_type) + " - status code " + str(r.status_code))
        for object_entry in r.json()["data"]:
            objects.append(object_entry)
        if len(r.json()["data"]) != 100:
            break
        else:
            page += 1
    logger.info("found " + str(len(objects)) + " monica events")
    return objects


def get_pre_from_event(event):
    before_indicator = "##### Before"
    if event["description"] and before_indicator in event["description"]:
        try:
            desc = event["description"].split(before_indicator + "\n")[1]
            return desc.split("#")[0].strip()
        except Exception as e:
            logger.error(e)


def get_pre_from_activity(row, pre_list, archived_activities):
    before_indicator = "##### Before"
    if row["description_x"] and before_indicator in row["description_x"]:
        summary = row["summary"]
        try:
            desc = row["description_x"].split(before_indicator + "\n")[1]
            desc = desc.split("#")[0].strip()
            pre_list.append(
                {
                    "summary": summary,
                    "description": desc,
                    "id": row["id_x"],
                    # "contact_ids": [int(contact["id"]) for contact in row["attendees"]["contacts"]],
                    "complete_description": row["description_x"],
                }
            )
        except Exception as e:
            logger.error(e)
    if (row["contact_id"] in archived_activities['contact_id'].to_list()):
        row = archived_activities[archived_activities['contact_id'] == row["contact_id"]].iloc[0]
        try:
            desc = row["description_x"].split(before_indicator + "\n")[1]
            desc = desc.split("#")[0].strip()
            pre_list.append(
                {
                    "summary": row["summary"],
                    "description": desc,
                    "id": row["id_x"],
                    # "contact_ids": [int(contact["id"]) for contact in row["attendees"]["contacts"]],
                    "complete_description": row["description_x"],
                }
            )
        except Exception as e:
            logger.error(e)
            pre_list.append(
                {
                    "summary": row["summary"],
                    "description": desc,
                    "id": row["id_x"],
                    # "contact_ids": [int(contact["id"]) for contact in row["attendees"]["contacts"]],
                    "complete_description": row["description_x"],
                }
            )


def update_activities_without_date(activities):
    new_date = datetime.now() + timedelta(days=7)
    activities_to_remove = []
    for activity in activities:
        if activity["summary"] == "TBD":
            update_acitivity(activity, new_date)
            activities_to_remove.append(activity)
    for activity in activities_to_remove:
        activities.remove(activity)
    return activities


def update_acitivity(activity, new_date):
    headers = {
        "Authorization": "Bearer %s" % MONICA_TOKEN,
        "Content-Type": "application/json",
    }
    api_url = "http://192.168.178.100:7000/api/"
    url = api_url + "activities/" + str(activity["id"])
    data = {
        "happened_at": new_date.strftime("%Y-%m-%d"),
        "summary": activity["summary"],
        "contacts": activity["contact_ids"],
        "description": activity["complete_description"],
    }
    logger.info(data)
    if DEBUG:
        r = requests.put(url, headers=headers, data=json.dumps(data))
        logger.info(r.json())


def get_activities(days):
    activities = get_activities_db()
    activity_contact = get_activity_contact()
    contacts = get_contacts()
    merged = activities.merge(activity_contact, left_on="id", right_on="activity_id", how="left")
    merged = merged.merge(contacts, left_on="contact_id", right_on="id", how="left")
    archived_activities = merged[merged["summary"] == "TBD"]
    merged["happened_tomorrow"] = merged["happened_at"].apply(
        lambda row: row == (datetime.today() + timedelta(days=days)).date()
    )
    merged = merged[merged["happened_tomorrow"] == True]
    pre_list = []
    merged.apply(lambda row: get_pre_from_activity(row, pre_list, archived_activities), axis=1)
    return pre_list
