import json
import os

from quarter_lib.logging import setup_logging

logger = setup_logging(__name__)


def get_config(file_path):
	with open(
		os.path.join(
			os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
			"config",
			file_path,
		),
		encoding="utf-8",
	) as f:
		data = json.load(f)
	return data


def get_value(value, row, config):
	return next(i for i in config if i[row] == value)


# def get_debug():
#     if os.name == "nt":
#         file_path = "bad_habit.json"
#         DEBUG = False
#     else:
#         file_path = "/home/pi/python/bad_habit.json"
#         DEBUG = False
#     logger.info("DEBUG MODE: " + str(DEBUG))
#     return DEBUG, file_path
