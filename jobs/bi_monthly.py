import os
from datetime import datetime

from fastapi import APIRouter
from loguru import logger

from helper import config_helper
from services.notion_service import (
    DATABASES,
    get_random_from_notion_link_list,
)
from services.todoist_service import (
    get_data
)

router = APIRouter(prefix="/bi_monthly", tags=["bi_monthly"])

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)

TO_NOTION_LABEL_ID = "2160732004"
TO_MICROJOURNAL_LABEL_ID = "2161901884"
BOOK_REWORK_PROJECT_ID = "2300202317"
BOOK_REWORK_2_PROJECT_ID = "2301632406"
BOOK_REWORK_3_PROJECT_ID = "2302294413"
RETHINK_PROJECT_ID = "2296630360"


def article_routine():
    logger.info("start article_routine")
    _, df_projects, _ = get_data()

    article_database = config_helper.get_value("article", "name", DATABASES)["id"]

    due = {"string": "15th"} if datetime.today().day == 1 else {"string": "1st"}
    get_random_from_notion_link_list(article_database, df_projects, due=due)

    logger.info("end article_routine")
