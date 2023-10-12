import os
from datetime import datetime, timedelta
from uuid import uuid4

import pandas as pd
import pymysql.cursors
from loguru import logger

from config.queries import activity_query
from helper.database_helper import create_server_connection, close_server_connection
from helper.date_helper import get_date_or_datetime
from services.github_service import create_obsidian_markdown_in_git
from services.notion_service import get_drugs_from_activity
from services.todoist_service import get_default_offset

DEFAULT_ACCOUNT_ID = 1
INBOX_CONTACT_ID = 52
MICROJOURNAL_CONTACT_ID = 58

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def get_activities_db():
    connection = create_server_connection("monica")
    df = pd.read_sql_query("SELECT * FROM activities", connection)
    close_server_connection(connection)
    return df


def get_activity_contact():
    connection = create_server_connection("monica")
    df = pd.read_sql_query("SELECT * FROM activity_contact", connection)
    close_server_connection(connection)
    return df


def get_contacts():
    connection = create_server_connection("monica")
    df = pd.read_sql_query("SELECT * FROM contacts", connection)
    close_server_connection(connection)
    return df


def add_monica_activities(appointment_list):
    connection = create_server_connection("monica")
    for appointment, additional_description in appointment_list:
        try:
            with connection.cursor() as cursor:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                happened_at = appointment[
                    'happened_at'] if 'happened_at' in appointment.keys() else get_date_or_datetime(appointment,
                                                                                                    "start").strftime(
                    "%Y-%m-%d")
                activities_values = tuple(
                    (
                        uuid4(),
                        DEFAULT_ACCOUNT_ID,
                        appointment["summary"],
                        additional_description if additional_description is not None else "",
                        happened_at,
                        timestamp,
                        timestamp,
                    )
                )
                cursor.execute(
                    "INSERT INTO activities (uuid, account_id, summary, description, happened_at, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    activities_values,
                )
                connection.commit()
                last_row_id = cursor.lastrowid

                activity_contact_values = tuple((last_row_id, INBOX_CONTACT_ID, DEFAULT_ACCOUNT_ID))
                cursor.execute(
                    "INSERT INTO activity_contact (activity_id, contact_id, account_id) VALUES (%s, %s, %s)",
                    activity_contact_values,
                )
                connection.commit()
                logger.info("Activity with id {activity_id} was added".format(activity_id=last_row_id))
        except pymysql.err.IntegrityError as e:
            logger.error("IntegrityError: {error}".format(error=e))
            continue
    close_server_connection(connection)


def get_inbox_activities_to_clean():
    temp_dict = {}
    connection = create_server_connection("monica")
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT activity_id, contact_id  from activity_contact ac where activity_id in 
                (SELECT activity_id FROM activity_contact where contact_id = 52)"""
        )
        for row in cursor:
            if row["activity_id"] not in temp_dict.keys():
                temp_dict[row["activity_id"]] = []
            temp_dict[row["activity_id"]].append(row["contact_id"])
    close_server_connection(connection)
    logger.info("Found {len} potential deletions.".format(len=len(temp_dict)))
    to_delete_list = []
    for temp_key in temp_dict.keys():
        if len(temp_dict[temp_key]) > 1:
            to_delete_list.append(temp_key)
    return to_delete_list


def delete_inbox_activity(connection, activity_id):
    logger.info("Deleting activity with id: {activity_id}".format(activity_id=activity_id))
    with connection.cursor() as cursor:
        try:
            cursor.execute(
                "DELETE FROM activity_contact WHERE contact_id = 52 and activity_id = %s",
                activity_id,
            )
            connection.commit()
        except pymysql.err.IntegrityError as e:
            logger.error("IntegrityError: {error}".format(error=e))
    logger.info("Activity with id {activity_id} was deleted".format(activity_id=activity_id))


def add_to_be_deleted_activities_to_obsidian(deletion_list):
    drug_date_dict = {}
    connection = create_server_connection("monica")
    timestamp = datetime.now()
    with connection.cursor() as cursor:
        for activity_id in deletion_list:
            try:
                query = activity_query.format(activity_id=activity_id)
                cursor.execute(query)
                for row in cursor:
                    drug_date_dict = get_drugs_from_activity(row, drug_date_dict)
                    create_obsidian_markdown_in_git(row, timestamp, drug_date_dict)
                    delete_inbox_activity(connection, activity_id)
            except pymysql.err.IntegrityError as e:
                logger.error("IntegrityError: {error}".format(error=e))
                continue
            logger.info("Activity with id {activity_id} was added to obsidian".format(activity_id=activity_id))
    close_server_connection(connection)


def add_to_microjournal(microjournal_list):
    delta, delta_str = get_default_offset()
    connection = create_server_connection("monica")
    for microjournal_entry in microjournal_list:
        try:
            with connection.cursor() as cursor:
                date_added = datetime.strptime(microjournal_entry.created_at, "%Y-%m-%dT%H:%M:%S.%fZ") + delta
                title = date_added.strftime("%H:%M:%S") + delta_str
                content = (
                    (microjournal_entry.content + " - " + microjournal_entry.description)
                    if microjournal_entry.description is not None or ""
                    else microjournal_entry.content
                )
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                happened_at = date_added.strftime("%Y-%m-%d")
                activities_values = tuple(
                    (
                        uuid4(),
                        DEFAULT_ACCOUNT_ID,
                        title,
                        content,
                        happened_at,
                        timestamp,
                        timestamp,
                    )
                )
                cursor.execute(
                    "INSERT INTO activities (uuid, account_id, summary, description, happened_at, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    activities_values,
                )
                connection.commit()
                last_row_id = cursor.lastrowid

                activity_contact_values = tuple((last_row_id, MICROJOURNAL_CONTACT_ID, DEFAULT_ACCOUNT_ID))
                cursor.execute(
                    "INSERT INTO activity_contact (activity_id, contact_id, account_id) VALUES (%s, %s, %s)",
                    activity_contact_values,
                )
                connection.commit()
        except pymysql.err.IntegrityError as e:
            logger.error("IntegrityError: {error}".format(error=e))
            continue
    close_server_connection(connection)


def update_archive():
    connection = create_server_connection("monica")
    tomorrow = (datetime.now() + timedelta(days=1))
    df = pd.read_sql_query('SELECT * FROM activities WHERE happened_at = "{happened_at}" AND summary ="TBD"'.format(
        happened_at=tomorrow.strftime("%Y-%m-%d")), connection)
    with connection.cursor() as cursor:
        for index, row in df.iterrows():
            try:
                cursor.execute(
                    'UPDATE activities SET happened_at = "{new_date}" WHERE id = {id}'.format(
                        new_date=(tomorrow + timedelta(days=5)).strftime("%Y-%m-%d"), id=row["id"])
                )
                connection.commit()
            except pymysql.err.IntegrityError as e:
                logger.error("IntegrityError: {error}".format(error=e))
                continue
    close_server_connection(connection)
