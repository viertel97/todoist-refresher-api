import copy
import re
from datetime import datetime, timedelta
from typing import Annotated

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Path, Query
from github import UnknownObjectException
from quarter_lib.logging import setup_logging

from src.helper.config_helper import get_value
from src.helper.database_helper import create_server_connection
from src.helper.path_helper import slugify
from src.helper.web_helper import get_categories_data_from_web, save_categories_data_to_web
from src.services.cubox_service import add_cubox_annotations_to_obsidian, add_cubox_reading_task_to_todoist
from src.services.database_service import add_or_update_row_koreader_book, add_or_update_row_koreader_page_stat
from src.services.github_service import create_obsidian_markdown_in_git, get_files
from src.services.google_service import create_travel_events_for_upcoming_calendar_events
from src.services.microsoft_service import get_koreader_settings, upload_transcribed_article_to_onedrive
from src.services.monica_database_service import add_monica_activities, update_archive
from src.services.monica_service import (
	add_tasks,
	get_activities,
	get_events_for_days,
	was_at_day,
)
from src.services.notion_service import (
	DATABASES,
	get_article_database,
	get_page_for_date,
	get_random_from_notion_link_list,
	get_text_from_article,
	stretch_article_list,
	stretch_project_tasks,
	update_habit_tracker_vacation_mode,
	update_notion_habit_tracker,
	update_notion_page_checkbox, stretch_databases,
)
from src.services.sqlite_service import get_koreader_book, get_koreader_page_stat
from src.services.todoist_service import TODOIST_API, add_after_vacation_tasks, add_before_tasks, get_vacation_mode
from src.services.tts_service import transcribe

logger = setup_logging(__file__)
router = APIRouter(prefix="/daily", tags=["daily"])

async def monica(check_for_next_day=False, days = 0):
	logger.info("start daily - monica (tomorrow)") if check_for_next_day else logger.info("start daily - monica (today)")


	if not check_for_next_day:
		timestamp = datetime.now()

		try:
			files_in_repo = get_files(f"0300_Spaces/Social Circle/Activities/{timestamp.year!s}/{timestamp.strftime('%m-%B')!s}")
		except UnknownObjectException as e: # folder for month not created yet
			logger.error(f"UnknownObjectException: {e}")
			files_in_repo = []
		files_in_repo.extend(
			get_files(
				f"0300_Spaces/Social Circle/Activities/{(timestamp - relativedelta(months=1)).year!s}/{(timestamp - relativedelta(months=1)).strftime('%m-%B')!s}"
			)
		)

	activities = get_activities(days)

	events = get_events_for_days()
	events_today, _ = was_at_day(events, days, check_for_next_day)
	logger.info("found " + str(len(events_today)) + " Google Calendar events")
	events_today = [event for event in events_today if filter_event(event["summary"])]
	if len(events_today) > 0:
		# TODO: add matched schema so afterwards we can also add
		#  default participants to Todoist and DB-Entry and then remove the Stored Procedure - use "schema_matches"
		add_tasks(TODOIST_API, events_today, activities)
		created_activities = add_monica_activities(events_today)
	#   if not check_for_next_day:
	#		for row in created_activities:
	#			await create_obsidian_markdown_in_git(row, run_timestamp=timestamp, drug_date_dict={}, files_in_repo=files_in_repo)

	logger.info("end daily - monica (tomorrow)") if check_for_next_day else logger.info("end daily - monica (today)")

	return events_today


@logger.catch
@router.post("/monica-morning")
async def monica_morning(
	days: int = Query(0, title="Days", description="Number of days to look ahead / back")
):
	return await monica(check_for_next_day=False, days=days)

@logger.catch
@router.post("/monica-evening")
async def monica_evening():
	return await monica(check_for_next_day=True)

@logger.catch
@router.post("/distance-events")
def distance_events():
	logger.info("start distance_events")
	created_events = create_travel_events_for_upcoming_calendar_events()
	logger.info("end distance_events")
	return created_events


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
@router.post("/stretch_lists")
def stretch_lists():
	logger.info("start daily - stretch lists")
	stretch_databases("ccf13accb1124856b6092fd37614144b")
	logger.info("end daily - stretch lists")



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

filter_list = ["K"]
filter_list_in = ["Drive from", "Buchungsschnitt"]
filter_list_ends_with = ["'s birthday"]
filter_list_starts_with = ["Namenstag", "Hochzeitstag", "Name day"]
filter_list_regex = [r"\w+\sHbf\s→\s\w+\sHbf"]


def filter_event(summary):
	filtered_filter_list = any(ext == summary for ext in filter_list)
	filtered_filter_list_ends_with = any(summary.endswith(ext) for ext in filter_list_ends_with)
	filtered_filter_list_in = any(ext in summary for ext in filter_list_in)
	filtered_filter_list_starts_with = any(summary.startswith(ext) for ext in filter_list_starts_with)
	filtered_filter_list_regex = any(re.search(ext, summary) for ext in filter_list_regex)
	return not (
		filtered_filter_list
		or filtered_filter_list_ends_with
		or filtered_filter_list_in
		or filtered_filter_list_starts_with
		or filtered_filter_list_regex
	)


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
				update_notion_page_checkbox(row["id"], "Transcribed-And-Uploaded-To-OneDrive", True)
			else:
				logger.warning(f'no text for {row["properties~Name~title"][0]["plain_text"]}')
		except Exception as e:
			logger.error(f"error for {row['title']}: {e}")


def umlaut_sort_key(word):
	translation_table = str.maketrans("äöüÄÖÜ", "aouAOU")
	return word.translate(translation_table)


@logger.catch
@router.post("/order_shopping_list_categories")
async def order_shopping_list_categories():
	logger.info("start daily - order shopping list categories")
	old_categories = get_categories_data_from_web()
	categories = copy.deepcopy(old_categories)

	for section in categories:
		section["items"] = sorted(section["items"], key=umlaut_sort_key)

	if categories != old_categories:
		logger.info("categories changed - saving")
		save_categories_data_to_web(categories)
	else:
		logger.info("categories not changed")
	logger.info("end daily - order shopping list categories")


@logger.catch
@router.post("/daily_cubox_to_obsidian_routine")
async def daily_cubox_routine():
	logger.info("start daily - cubox routine")
	await add_cubox_annotations_to_obsidian()
	logger.info("end daily - cubox routine")


@logger.catch
@router.post("/daily_cubox_reading_routine_weighted")
async def daily_cubox_reading_routine_weighted():
	logger.info("start daily - cubox reading routine weighted")
	add_cubox_reading_task_to_todoist(weighted=True)
	logger.info("end daily - cubox reading routine weighted")


@logger.catch
@router.post("/daily_cubox_reading_routine_unweighted")
async def daily_cubox_reading_routine_unweighted():
	logger.info("start daily - cubox reading routine unweighted")
	add_cubox_reading_task_to_todoist(weighted=False)
	logger.info("end daily - cubox reading routine unweighted")
