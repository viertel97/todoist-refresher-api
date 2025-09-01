import os

from loguru import logger
from quarter_lib.google_calendar import build_calendar_service

from src.services.monica_database_service import (
	close_server_connection,
	create_server_connection,
)
from src.services.monica_service import get_dict

logger.add(
	os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
	format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
	backtrace=True,
	diagnose=True,
)


def test_service():
	calendar_service = build_calendar_service()
	calendar_dict = get_dict(calendar_service)
	logger.info(calendar_dict.keys())
	logger.info("Calendar Service build successfully")

	connection = create_server_connection("private")
	close_server_connection(connection)
	logger.info("Private DB Server Connection build successfully")

	connection = create_server_connection("monica")
	close_server_connection(connection)
	logger.info("Monica DB Server Connection build successfully")
