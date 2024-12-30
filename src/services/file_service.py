import os

NOT_MATCHED_FILE = "/home/pi/code/keep2todoist/not_found.txt"
NOT_MATCHED_FILE_WINDOWS = "not_found.txt"


def read_not_matched_file():
	path = NOT_MATCHED_FILE if os.name != "nt" else NOT_MATCHED_FILE_WINDOWS
	with open(path, "r", encoding="utf-8") as f:
		return f.read()
