import os
import traceback
from pathlib import Path
from sys import platform

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from quarter_lib.logging import setup_logging

from src.config.api_documentation import description, tags_metadata, title
from src.helper.google_helper import test_service
from src.helper.network_helper import log_request_info
from src.jobs import (
	bi_monthly,
	bi_weekly,
	daily,
	hourly,
	weekly,
)
from src.services.telegram_service import send_to_telegram

controllers = [bi_weekly, bi_monthly, daily, hourly, weekly]

logger = setup_logging(__name__)

DEBUG = platform == "darwin" or platform == "win32" or platform == "Windows"
IS_CONTAINER = os.environ.get("IS_CONTAINER", "False") == "True"
logger.info(f"Variables:\nDEBUG: {DEBUG}\nIS_CONTAINER: {IS_CONTAINER}\nplatform: {platform}")
app = FastAPI(openapi_tags=tags_metadata, title=title, description=description)

# app = FastAPI(debug=DEBUG)
router = APIRouter()

[app.include_router(controller.router, dependencies=[Depends(log_request_info)]) for controller in controllers]


@app.get("/blabla")
async def test():
	raise HTTPException("test")


@app.get("/")
def health():
	return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
	logger.info(f"{request}: {exc_str}")
	content = {"status_code": 10422, "message": exc_str, "data": None}
	return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
	items = request.path_params.items()
	headers = request.headers.items()

	request_logging_string = f"{request.method} {request.url}\n\n Headers:\n{headers}\n\nItems:\n{items}"
	exception_logging_string = f"{exc.__class__.__name__}: {exc}\n\n{''.join(traceback.TracebackException.from_exception(exc).format())}"
	logging_string = f"Exception:\n{exception_logging_string}\n---------\nRequest:\n{request_logging_string}\n\n"
	await send_to_telegram(logging_string)
	logger.error(logging_string)
	return JSONResponse(
		content={
			"status_code": 500,
			"message": "Internal Server Error",
			"data": None,
		},
		status_code=500,
	)


if __name__ == "__main__":
	if DEBUG and IS_CONTAINER:
		# uvicorn.run(f"{Path(__file__).stem}:app", host="localhost", port=9100, workers=1, reload=True)
		# hourly.todoist_to_work_routine()
		# hourly.todoist_to_work_routine()
		# daily.links()
		# daily.monica_morning()
		# daily.monica_before_tasks(0)
		# daily.update_monica_archive()
		weekly.update_todoist_projects()
		# weekly.ght_update()
		# weekly.youtube_tasks()
		# daily.update_notion_habit_tracker()
		# daily.vacation_mode_checker()
		# hourly.todoist_to_notion_routine()
		# hourly.todoist_to_rethink_routine()
		# stretch_tpt()
		# article_to_do()
		# clean_inbox_activities_routine()
		# hourly.todoist_to_microjournal_routine()
		# daily.monica_calls()
		# daily.notion_habit_tracker_stack()
		# bi_weekly.update_book_rework()
		# bi_weekly.update_to_think_about()
		# bi_weekly.obsidian_random_activity()
		# bi_weekly.obsidian_oldest_note()
		# weekly.not_matched_to_todoist()
		# update_koreader_statistics()
		print("test")
		# weekly.article_to_audio_routine()
	else:
		test_service()

		uvicorn.run(f"{Path(__file__).stem}:app", host="0.0.0.0", port=9100)
