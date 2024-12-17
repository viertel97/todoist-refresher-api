import os
import pathlib
import subprocess
import time
from datetime import datetime, timedelta
from typing import Text

import requests
from loguru import logger

import helper

CONFIG = helper.get_config("obsidian_config.json")


logger.add(
	os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
	format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
	backtrace=True,
	diagnose=True,
)

if os.name == "nt":
	DEBUG = True
else:
	DEBUG = False


def get_link_for_file(file, link_text=""):
	if link_text != "":
		return "[[" + file.replace(".md", "") + "|" + link_text + "]]"
	else:
		return "[[" + file.replace(".md", "") + "]]"


def get_weather(location):
	payload = {"format": "3"}
	r = requests.get("http://wttr.in/" + str(location), params=payload)
	return r.text.strip()


def read_file(file_name):
	file_content = ""
	with open(file_name, "r") as file_obj:
		for line in file_obj:
			file_content += line
	return file_content


def get_daily_notes_filename(offset=0):
	file_date = datetime.now()
	if offset != 0:
		file_date = file_date + timedelta(days=offset)
	return file_date.strftime("%Y.%m.%d.%a") + ".md"


def copy_to_onedrive(file_path):
	cmd = ["rclone", "copy", file_path, CONFIG[0]["notes_root"]]
	logger.info(cmd)
	if not DEBUG:
		logger.info(subprocess.check_call(cmd))
	time.sleep(10)
	os.remove(file_path)


def generate_daily_note():
	daily_notes_file = os.path.join(pathlib.Path(__file__).parent.resolve(), get_daily_notes_filename())
	if os.path.exists(daily_notes_file):
		logger.info("File already exists. Not overwriting...")
	else:
		logger.info("Generating daily notes file " + os.path.basename(daily_notes_file) + "...")
		with open(daily_notes_file, "w", encoding="utf-8") as fh:
			nav_bar = get_link_for_file(get_daily_notes_filename(offset=-1))
			nav_bar += " | " + get_link_for_file(get_daily_notes_filename(offset=1))
			nav_bar += " | " + get_weather(int(CONFIG[0]["weather_zip"]))
			fh.write(nav_bar + "\n")

			fh.write("\n## Reading\n")

			fh.write("\n## Today's notes\n")
		copy_to_onedrive(daily_notes_file)


if __name__ == "__main__":
	generate_daily_note()
