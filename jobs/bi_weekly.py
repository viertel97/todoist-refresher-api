import os
import random
from datetime import datetime, timedelta

from fastapi import APIRouter
from loguru import logger

from services.github_service import get_files, get_files_with_modification_date
from services.todoist_service import (
    get_items_by_todoist_project,
    update_task_due, add_obsidian_task_for_note, check_if_last_item, add_obsidian_task_for_activity, get_rework_projects
)

router = APIRouter(prefix="/bi_weekly", tags=["bi_weekly"])

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)

RETHINK_PROJECT_ID = "2296630360"


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

    files = get_files("0000_Zettelkasten")

    file = random.choice(files)
    add_obsidian_task_for_note(file, "Random file")
    logger.info("selected random file '{}'".format(file))

    logger.info("end bi-daily - obsidian - random note")


@logger.catch
@router.post("/obsidian_oldest_note")
def obsidian_oldest_note():
    logger.info("start bi-daily - obsidian - oldest note")

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

    files = get_files("0300_Spaces/Social Circle/Activities")

    file = random.choice(files)
    add_obsidian_task_for_activity(file, "Random activity file")
    logger.info("selected random activity file '{}'".format(file))

    logger.info("end bi-daily - obsidian - random activity")


@logger.catch
@router.post("/update_book_rework")
def update_book_rework():
    logger.info("start - daily update book rework")

    rework_projects = get_rework_projects()

    items = []
    for project in rework_projects:
        items.extend(get_items_by_todoist_project(project.id))

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
    raise "TBD"
