import traceback
from pathlib import Path
from sys import platform

import uvicorn
from fastapi import APIRouter, Depends, status
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from quarter_lib.logging import setup_logging

from helper.google_helper import test_service
from helper.network_helper import log_request_info
from jobs import (
    bi_weekly,
    bi_monthly,
    daily,
    hourly,
    weekly,
)
from services.telegram_service import send_to_telegram

controllers = [
    bi_weekly,
    bi_monthly,
    daily,
    hourly,
    weekly
]

logger = setup_logging(__name__)

logger.info(platform)
DEBUG = (platform == "darwin" or platform == "win32" or platform == "Windows")
logger.info(f"DEBUG: {DEBUG}")
app = FastAPI()

# app = FastAPI(debug=DEBUG)
router = APIRouter()

[app.include_router(controller.router, dependencies=[Depends(log_request_info)]) for controller in controllers]


@app.get("/blabla")
async def test():
    raise HTTPException("test")


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
    print("lol")
    if DEBUG:
        uvicorn.run(f"{Path(__file__).stem}:app", host="localhost", port=9100, workers=1, reload=True)
        # hourly.todoist_to_work_routine()
        # hourly.todoist_to_work_routine()
        # daily.links()
        # daily.monica(False)
        # daily.monica_before_tasks(2)
        # daily.monica(True)
        # daily.update_monica_archive()
        # weekly.tpt()
        # weekly.ght_update()
        # weekly.youtube_tasks()
        # daily.update_notion_habit_tracker()
        # daily.vacation_mode_checker()
        # hourly.todoist_to_notion_routine()
        # hourly.todoist_to_rethink_routine()
        # clean_inbox_activities_routine()
        # hourly.todoist_to_microjournal_routine()
        # daily.monica_calls()
        # daily.notion_habit_tracker_stack()
        # bi_weekly.update_book_rework()
        # bi_weekly.update_to_think_about()
        bi_weekly.obsidian_random_activity()
        # bi_weekly.obsidian_oldest_note()
        # weekly.not_matched_to_todoist()
        # update_koreader_statistics()
        print("test")
        # weekly.article_to_audio_routine()
    else:
        test_service()

        uvicorn.run(f"{Path(__file__).stem}:app", host="0.0.0.0", port=9100, workers=2)
