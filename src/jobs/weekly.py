import datetime

from fastapi import APIRouter
from quarter_lib.logging import setup_logging

from src.helper.config_helper import get_value
from src.services.ght_service import update_ght
from src.services.notion_service import (
	DATABASES,
	get_random_from_notion_articles,
	get_random_from_notion_database,
)
from src.services.todoist_service import (
	PROJECT_DICT,
	check_due,
	check_next_week,
	get_data,
	get_dates,
	move_items,
)
from src.services.youtube_service import add_video_annotate_task, add_video_transcribe_tasks

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
	get_random_from_notion_database(tech_database)
	logger.info("end weekly - tpt")


@logger.catch
@router.post("/mm")
def mm():
	logger.info("start weekly - mm")
	mm_database = get_value("mindfull_mastery", "name", DATABASES)["id"]
	get_random_from_notion_database(mm_database)
	logger.info("end weekly - mm")


@logger.catch
@router.post("/ght_update")
async def ght_update():
	await update_ght()


@logger.catch
@router.post("/article_to_todo")
def article_to_do():
	logger.info("start weekly - article to todo")
	get_random_from_notion_articles()
	logger.info("end weekly - article to todo")


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
