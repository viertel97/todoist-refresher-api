import os
from datetime import datetime, time, timedelta

from dateutil import parser
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging
from quarter_lib.google_calendar import (
	build_calendar_service,
	get_dict,
)
from todoist_api_python.api import TodoistAPI

from src.helper.date_helper import get_date_or_datetime
from src.services.monica_database_service import (
	get_activities_db,
	get_activity_contact,
	get_contacts,
)

logger = setup_logging(__file__)

SCOPES = [
	"https://www.googleapis.com/auth/fitness.activity.read",
	"https://www.googleapis.com/auth/calendar.readonly",
]
SCOPES = [
	"https://www.googleapis.com/auth/calendar",
]
MONICA_TOKEN = get_secrets(["monica/token"])

creds = None
DEBUG = os.name == "nt"


def get_events_from_calendar_for_days(calendar_name, calendar_dict, calendar_service, days=0):
	event_list = []
	page_token = None

	while True:
		time_min = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
		time_max = datetime.today().replace(hour=23, minute=59, second=59, microsecond=0) + timedelta(days=days)
		query_params = {
			"calendarId": calendar_dict[calendar_name]["id"],
			"pageToken": page_token,
			"singleEvents": True,
			"timeMin": time_min.isoformat() + "Z",
			"timeMax": time_max.isoformat() + "Z",
		}

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
	event_list.extend(get_events_from_calendar_for_days("Systemischer Berater", calendar_dict, calendar_service, days))

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
			# check if event has time or is all day
			start = get_date_or_datetime(event, "start").replace(tzinfo=None).date()
			end = get_date_or_datetime(event, "end").replace(tzinfo=None).date()
			if "dateTime" not in event["start"].keys():
				if (end - start).days >= 1:
					end = end - timedelta(days=1)
			# -1 because end is exclusive
			if start <= selected_day <= end:
				if "description" in event.keys():
					if "#ignore" not in event["description"]:
						events.append(event)
				else:
					events.append(event)
	return events, selected_day


DAILY_LINKS_THRESHOLD = time(hour=16)


def is_multiday_event(appointment):
	start = get_date_or_datetime(appointment, "start").replace(tzinfo=None)
	end = get_date_or_datetime(appointment, "end").replace(tzinfo=None)

	if start.date() == end.date():
		return False

	if "dateTime" in appointment["start"].keys():
		if start.date() != end.date():
			return (datetime.today().date() - start.date()).days + 1

	if start.date() != (
		end.date() - timedelta(days=1)
	):  # adding 1 day because full day events would otherwise be counted as multiday events
		# which day of multiday event (eg. 2nd day)
		return (datetime.today().date() - start.date()).days + 1
	return False


def add_tasks(api: TodoistAPI, events: list[dict], activities: list):
	if len(events) > 0:
		for event in events:
			logger.info("adding Todoist task: " + str(event))
			event_time = get_date_or_datetime(event, "end")
			if event_time.time() <= DAILY_LINKS_THRESHOLD:
				due = {"string": "Today"}
			else:
				due = {"string": "Tomorrow"}
			is_multiday = is_multiday_event(event)
			if is_multiday:
				today = datetime.today()
				event["happened_at"] = today.strftime("%Y-%m-%d")
				event["summary"] = event["summary"] + f" (Tag {is_multiday!s} - {event['happened_at']} - {today.strftime('%A')})"
				due = {"string": "Tomorrow"}
			content = "'" + event["summary"] + "'" + " - nacharbeiten & Tracker pflegen"
			logger.info("content: " + str(content))
			description = get_description(activities)
			item = api.add_task(
				content,
				description=description if description != "" else None,
				project_id="6Crcr3mXxVh6f97J",
				labels=["Digital"],
				due_string=due["string"],
			)
			logger.info("added Todoist task: " + str(item))

			logger.info("added Todoist task: " + str(item))


def get_description(activities):
	description_string = ""
	for activity in activities:
		description_string += "* " + activity["summary"] + ": \n"
		description_string += activity["description"].replace("*", "  *")
		description_string += "\n\n"
	return description_string



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
	if row["contact_id"] in archived_activities["contact_id"].to_list():
		row = archived_activities[archived_activities["contact_id"] == row["contact_id"]].iloc[0]
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



def get_activities(days):
	activities = get_activities_db()
	activity_contact = get_activity_contact()
	contacts = get_contacts()
	merged = activities.merge(activity_contact, left_on="id", right_on="activity_id", how="left")
	merged = merged.merge(contacts, left_on="contact_id", right_on="id", how="left")
	archived_activities = merged[merged["summary"] == "TBD"]
	merged["happened_tomorrow"] = merged["happened_at"].apply(lambda row: row == (datetime.today() + timedelta(days=days)).date())
	merged = merged[merged["happened_tomorrow"] == True]
	pre_list = []
	merged.apply(lambda row: get_pre_from_activity(row, pre_list, archived_activities), axis=1)
	return pre_list
