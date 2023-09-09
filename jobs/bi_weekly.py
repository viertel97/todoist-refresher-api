import os
import random
from datetime import datetime, timedelta

import requests
from fastapi import APIRouter
from loguru import logger

from helper.caching import ttl_cache
from services.github_service import get_files, get_files_with_modification_date
from services.todoist_service import (
    update_obsidian_task,
    get_items_by_todoist_project,
    update_task_due, add_obsidian_task_for_note, OBSIDIAN_REWORK_PROJECT_ID, check_if_last_item, get_tasks_by_filter,
    get_project_names_by_ids, add_obsidian_task_for_activity
)

router = APIRouter(prefix="/bi_weekly", tags=["bi_weekly"])

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)

RETHINK_PROJECT_ID = "2296630360"

PROJECT_IDS_URL = "https://viertel-it.de/files/rework_project_ids.json"


@ttl_cache(ttl=60 * 60)
def get_ids_from_web():
    logger.info("getting ids from web")
    response = requests.get(PROJECT_IDS_URL, headers={'User-Agent': 'Mozilla/5.0'}, verify=False)
    data = response.json()
    return data


@logger.catch
@router.post("/update_to_think_about")
def update_to_think_about():
    logger.info("start - bi daily update to think about")
    items = get_items_by_todoist_project(RETHINK_PROJECT_ID)
    if len(items) > 0:
        due_items = [item for item in items if item.due is not None]
        tomorrow = {"date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")}
        if len(due_items) > 0:
            update_task_due(due_items[0], tomorrow)
        else:
            item = items[0]
            update_task_due(item, tomorrow)
    else:
        logger.info("no book entries to review")
    logger.info("end - bi daily update to think about")


@logger.catch
@router.post("/obsidian_random_note")
def obsidian_random_note():

    logger.info("start bi-daily - obsidian - random note")

    obsidian_rework_items = get_items_by_todoist_project(OBSIDIAN_REWORK_PROJECT_ID)
    without_due = [item for item in obsidian_rework_items if not item.due]
    with_due = [item for item in obsidian_rework_items if item.due]

    if with_due:
        tomorrow = {"date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")}
        for item in with_due:
            update_task_due(item, tomorrow)
    else:
        if without_due:
            item = without_due[0]
            update_obsidian_task(item)
        else:
            files = get_files("0000_Zettelkasten")

            file = random.choice(files)
            add_obsidian_task_for_note(file.name, "Random file")
            logger.info("selected random file '{}'".format(file.name))

            logger.info("end bi-daily - obsidian - random note")


@logger.catch
@router.post("/obsidian_oldest_note")
def obsidian_oldest_note():

    logger.info("start bi-daily - obsidian - oldest note")

    obsidian_rework_items = get_items_by_todoist_project(OBSIDIAN_REWORK_PROJECT_ID)
    without_due = [item for item in obsidian_rework_items if not item.due]
    with_due = [item for item in obsidian_rework_items if item.due]

    if with_due:
        tomorrow = {"date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")}
        for item in with_due:
            update_task_due(item, tomorrow)
    else:
        if without_due:
            item = without_due[0]
            update_obsidian_task(item)
        else:
            files = get_files_with_modification_date("0000_Zettelkasten")
            sorted_files = sorted(files, key=lambda x: x['last_modified_date'], reverse=False)
            file = sorted_files[0]
            add_obsidian_task_for_note(file['path'], "Oldest file")
            logger.info("selected oldest file '{}'".format(file['path']))

            logger.info("end bi-daily - obsidian - oldest note")

@logger.catch
@router.post("/obsidian_random_activity")
def obsidian_random_activity():

    logger.info("start bi-daily - obsidian - random activity")

    obsidian_rework_items = get_items_by_todoist_project(OBSIDIAN_REWORK_PROJECT_ID)
    without_due = [item for item in obsidian_rework_items if not item.due]
    with_due = [item for item in obsidian_rework_items if item.due]

    if with_due:
        tomorrow = {"date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")}
        for item in with_due:
            update_task_due(item, tomorrow)
    else:
        if without_due:
            item = without_due[0]
            update_obsidian_task(item)
        else:
            files = get_files("0300_Spaces/Social Circle/Activities")

            file = random.choice(files)
            add_obsidian_task_for_activity(file.name, "Random activity file")
            logger.info("selected random activity file '{}'".format(file.name))

            logger.info("end bi-daily - obsidian - random activity")


@logger.catch
@router.post("/update_book_rework")
def update_book_rework():
    logger.info("start - daily update book rework")

    project_ids = get_ids_from_web()
    project_names = get_project_names_by_ids(project_ids)
    project_names_concatenated = ','.join(['#' + name for name in project_names])

    items = get_tasks_by_filter(project_names_concatenated)

    items = [{'orig_item': item} for item in items]
    for item in items:
        content = item['orig_item'].content
        split_content = content.split(' - ')
        if (len(split_content) != 3):
            if split_content[len(split_content) - 1] == "Obsidian-Eintrag überdenken":
                item['annotation'] = "".join(split_content[0:len(split_content) - 2])
                item['book'] = split_content[len(split_content) - 2]
            else:
                logger.error("item with content '{}' has no book".format(content))
        else:
            item['annotation'] = split_content[0]
            item['book'] = split_content[1]

    items = [item for item in items if "book" in item.keys()]

    if len(items) > 0:
        due_items = [item['orig_item'] for item in items if item['orig_item'].due is not None]
        tomorrow = {"date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")}
        if len(due_items) > 0:
            update_task_due(due_items[0], tomorrow)
        else:
            selected_entry = random.choice(items)
            update_task_due(selected_entry['orig_item'], tomorrow)
            # items.remove(selected_entry)
            check_if_last_item(selected_entry['book'], items)
    else:
        logger.info("no book entries to review")
    logger.info("end - daily update book rework")


def article_routine():
    logger.info("start - daily update book rework")

    project_ids = get_ids_from_web()
    project_names = get_project_names_by_ids(project_ids)
    project_names_concatenated = ','.join(['#' + name for name in project_names])

    items = get_tasks_by_filter(project_names_concatenated)

    items = [{'orig_item': item} for item in items]
    for item in items:
        content = item['orig_item'].content
        split_content = content.split(' - ')
        if (len(split_content) < 2):
            logger.error("item with content '{}' has no book".format(content))
            items.remove(item)
            continue
        item['annotation'] = split_content[0]
        item['book'] = split_content[1]

    if len(items) > 0:
        due_items = [item['orig_item'] for item in items if item['orig_item'].due is not None]
        tomorrow = {"date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")}
        if len(due_items) > 0:
            update_task_due(due_items[0], tomorrow)
        else:
            selected_entry = random.choice(items)
            update_task_due(selected_entry['orig_item'], tomorrow)
            # items.remove(selected_entry)
            check_if_last_item(selected_entry['book'], items)
    else:
        logger.info("no book entries to review")
    logger.info("end - daily update book rework")
