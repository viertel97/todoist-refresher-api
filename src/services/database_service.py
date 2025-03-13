from datetime import datetime, timedelta

import pandas as pd
from quarter_lib.logging import setup_logging

from src.helper.database_helper import close_server_connection, create_server_connection

logger = setup_logging(__file__)

MAX_PER_WEEK = 15
LENGTH_OF_WEEK = 7


def is_positive(row):
	notation_dict = {}
	if isinstance(row["notation"], str):
		notation = row["notation"].lower().split(" / ")
		for n in notation:
			temp = n.split(":")
			notation_dict[temp[0]] = temp[1].strip()
		if row["default_type"] == "boolean":
			return notation_dict[row["value"]] == "positive"
		return row["value"] == row["default_type"] if notation_dict["cancel"] == "positive" else row["value"] != row["default_type"]
	return None


def get_timestamps(offset=0):
	today = datetime.today() + timedelta(days=offset)
	start_of_week = today + timedelta(days=-today.weekday(), weeks=0)  # 0
	start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
	end_of_week = today + timedelta(days=-today.weekday() - 1, weeks=1)
	end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=0)
	return start_of_week, end_of_week, today.isocalendar()[1]


def get_ght_results(offset=-1):
	connection = create_server_connection("private", alchemy=True)
	start_of_week, end_of_week, kw = get_timestamps(offset=offset)
	ght = pd.read_sql(
		"SELECT * FROM ght WHERE ts >= %s AND ts <= %s",
		connection,
		params=(start_of_week, end_of_week),
	)
	unique_timestamps = [pd.to_datetime(ts).replace(second=0) for ts in ght["created_at"]]
	unique_timestamps = len(list(set(unique_timestamps)))
	if len(ght) <= 0:
		close_server_connection(connection)
		raise Exception(f"No results found for week {kw}. Start of week: {start_of_week} /  end of week: {end_of_week}")
	ght_questions = pd.concat(
		[
			pd.read_sql("SELECT * FROM ght_questions_daily_evening WHERE notation IS NOT NULL AND multiplier > 0", connection),
			pd.read_sql("SELECT * FROM ght_questions_daily_morning WHERE notation IS NOT NULL AND multiplier > 0", connection),
		]
	)
	sum_multiplier_per_week = ght_questions[ght_questions["active"] == 1]["multiplier"].sum() * LENGTH_OF_WEEK
	ght = ght.merge(ght_questions, on="code", how="left")
	ght.rename(
		columns={
			"ts": "timestamp",
		},
		inplace=True,
	)
	ght["positive"] = ght.apply(is_positive, axis=1)
	ght = ght[ght["positive"] == True]
	ght["timestamp"] = ght["timestamp"].dt.strftime("%H:%M, %d.%m.%Y")
	current_multiplier = ght["multiplier_x"].sum()
	ght["text"] = ght.apply(
		lambda row: "{ts}: {message} ({multiplier}) -> {value} ".format(
			ts=row["timestamp"],
			message=row["message"],
			value=row["value"],
			multiplier=row["multiplier_x"],
		),
		axis=1,
	)
	days_used = unique_timestamps / (7 * 2) if unique_timestamps < (7 * 2) else 1

	close_server_connection(connection, alchemy=True)
	return (
		ght[["text"]],
		round((current_multiplier / sum_multiplier_per_week) * MAX_PER_WEEK * days_used, 2),
		kw,
	)


def add_or_update_row_koreader_book(row, conn, table_name="koreader_book"):
	with conn.cursor() as cursor:
		cursor.execute(f"SELECT * FROM {table_name} WHERE id = %s", (row["id"],))
		values = list(row.values)

		if cursor.fetchone():
			update_query = f"UPDATE {table_name} SET "
			update_query += ", ".join([f"{column} = %s" for column in row.keys() if column != "id"])
			update_query += " WHERE id = %s"
			values.pop(0)
			cursor.execute(update_query, tuple(values + [row["id"]]))
			conn.commit()
			print(f"Updated {row['title']}")
		else:
			insert_query = f"INSERT INTO {table_name} ("
			insert_query += ", ".join(row.keys())
			insert_query += ") VALUES ("
			insert_query += ", ".join(["%s" for _ in row.keys()])
			insert_query += ")"
			cursor.execute(insert_query, tuple(row.values))
			conn.commit()
			print(f"Inserted {row['title']}")


def add_or_update_row_koreader_page_stat(row, conn, table_name="koreader_page_stat"):
	with conn.cursor() as cursor:
		cursor.execute(
			f"SELECT * FROM {table_name} WHERE page = %s and start_time = %s",
			(row["page"], row["start_time"]),
		)
		list(row.values)

		if cursor.fetchone():
			print(f"No update needed for {row['id_book']} {row['page']} {row['start_time']}")

			# update_query = f"UPDATE {table_name} SET "
			# update_query += ", ".join(
			#     [f"{column} = %s" for column in row.keys() if column != "page" and column != "start_time"])
			# update_query += " WHERE page = %s and start_time = %s"
			# [values.pop(x) for x in [1, 2]]
			# cursor.execute(update_query, tuple(values + [row["page"], row["start_time"]]))
			# conn.commit()
			# print(f"Updated {row['id_book']} {row['page']} {row['start_time']}")
		else:
			insert_query = f"INSERT INTO {table_name} ("
			insert_query += ", ".join(row.keys())
			insert_query += ") VALUES ("
			insert_query += ", ".join(["%s" for _ in row.keys()])
			insert_query += ")"
			cursor.execute(insert_query, tuple(row.values))
			conn.commit()
			print(f"Inserted {row['id_book']} {row['page']} {row['start_time']}")
