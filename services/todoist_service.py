from datetime import datetime, timedelta

import pandas as pd
from dateutil import parser
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging
from quarter_lib_old.todoist import (
    add_reminder,
    get_activity,
    get_user_karma_vacation,
    get_user_state,
    move_item_to_project,
    get_items_by_label,
    move_item_to_section,
    update_due,
)
from todoist_api_python.api import TodoistAPI

logger = setup_logging(__file__)
DEFAULT_OFFSET = timedelta(hours=2)

TODOIST_TOKEN = get_secrets(['todoist/token'])

TODOIST_API = TodoistAPI(TODOIST_TOKEN)

PROJECT_LIST = [
    "THIS WEEK",
    "NEXT WEEK",
    "IN 3-4 WEEKS",
    "IN 5-8 WEEKS",
    "LONG-TERM | ON HOLD",
]
HABITS_PROJECT_ID = "2244708745"
DAILY_SECTION_ID = "18496174"

THIS_WEEK_PROJECT_ID = "2244725398"
NEXT_WEEK_PROJECT_ID = "2244725594"

PROJECT_DICT = {
    "THIS WEEK": [],
    "NEXT WEEK": [],
    "IN 3-4 WEEKS": [],
    "IN 5-8 WEEKS": [],
    "LONG-TERM | ON HOLD": [],
}

TO_NOTION_DONE_LABEL_ID = "2160732007"
NOTION_DONE_SECTION_ID = "100014109"

TO_MICROJOURNAL_DONE_LABEL_ID = "2161902457"
MICROJOURNAL_DONE_SECTION_ID = "100014120"

STORAGE_PROJECT_ID = "2298105794"
RETHINK_PROJECT_ID = "2296630360"
TO_RETHINK_DONE_LABEL_ID = "2163807453"

OBSIDIAN_REWORK_PROJECT_ID = "2304525222"


def get_projects():
    projects = TODOIST_API.get_projects()
    df_projects = pd.DataFrame(projects)
    df_projects = df_projects[df_projects.name.isin(PROJECT_LIST)]
    return df_projects


def get_default_offset():
    tz_info = get_user_state()
    delta = timedelta(hours=tz_info["hours"], minutes=tz_info["minutes"])
    return delta, tz_info["gmt_string"]


def get_data():
    df_items = pd.DataFrame(item.__dict__ for item in TODOIST_API.get_tasks())
    df_projects = pd.DataFrame(item.__dict__ for item in TODOIST_API.get_projects())

    df_projects = df_projects[df_projects.name.isin(PROJECT_LIST)]
    df_items_due = df_items.loc[~df_items.due.isna()]
    df_items_due = df_items_due.loc[df_items_due.project_id.isin(df_projects.id)]

    df_items_no_due = df_items.loc[df_items.due.isna()]
    df_items_next_week = df_items_no_due[df_items_no_due.project_id == NEXT_WEEK_PROJECT_ID]

    return df_items_due, df_projects, df_items_next_week


def check_due(task_id, due, project_id, week_list, df_projects, project_dict):
    # check if year is the same
    due_date = parser.parse(due.date)

    if due_date.year == datetime.today().year:
        due_date_week = due_date.isocalendar()[1]
        if (
                week_list[0] == due_date_week or week_list[0] - 1 == due_date_week
        ):  # second condition because tasks on sunday or day at execution
            return check_and_add(project_id, task_id, 0, df_projects, project_dict)
        elif week_list[1] == due_date_week:
            return check_and_add(project_id, task_id, 1, df_projects, project_dict)
        elif week_list[2] <= due_date_week <= week_list[2] + 1:
            return check_and_add(project_id, task_id, 2, df_projects, project_dict)
        elif week_list[3] <= due_date_week <= week_list[3] + 3:
            return check_and_add(project_id, task_id, 3, df_projects, project_dict)
    check_and_add(project_id, task_id, 4, df_projects, project_dict)


def check_and_add(project_id, task_id, index, df_projects, project_dict):
    new_project = df_projects[df_projects.name == PROJECT_LIST[index]].iloc[0]
    if project_id != new_project.id:
        project_dict[PROJECT_LIST[index]].append(task_id)


def check_next_week(task_id, project_id, df_projects, project_dict):
    check_and_add(project_id, task_id, 0, df_projects, project_dict)


def move_items(project_dict, df_projects):
    for project in project_dict.keys():
        for task_id in project_dict[project]:
            project_to_move = df_projects[df_projects.name == project].iloc[0]
            move_item_to_project(task_id=task_id, project_id=project_to_move["id"])


def get_timestamps():
    today = datetime.today()
    start_of_week = today + timedelta(days=-today.weekday(), weeks=0)
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = today + timedelta(days=-today.weekday(), weeks=1)
    end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=0)
    return start_of_week, end_of_week


def get_dates():
    today = datetime.today()  # + timedelta(days=3)
    offset = 1
    this_week_start_week = (today + timedelta(days=int(0 + offset))).isocalendar()[1]
    next_week_start_week = (today + timedelta(days=int(8 + offset))).isocalendar()[1]
    three_to_four_weeks_start_week = (today + timedelta(days=int(16 + offset))).isocalendar()[1]
    five_to_eight_weeks_start_week = (today + timedelta(days=int(28 + offset))).isocalendar()[1]
    long_term_start_week = (today + timedelta(days=int(56 + offset))).isocalendar()[1]
    return [
        this_week_start_week,
        next_week_start_week,
        three_to_four_weeks_start_week,
        five_to_eight_weeks_start_week,
        long_term_start_week,
    ]


def generate_reminders(item, due):
    max_date = int("".join(filter(str.isdigit, due["string"])))
    new_date = datetime.today().replace(hour=20, minute=0, second=0, microsecond=0)
    add_reminder(item, {"string": new_date.strftime("21:15 %d.%m.%Y")})

    for i in range(15):
        new_date = new_date + timedelta(days=1)
        if new_date.day == max_date:
            break
        if (i + 1) % 2 == 0:
            add_reminder(item.id, new_date)

    due = {"string": new_date.strftime("%d.%m.%Y")}
    item = TODOIST_API.add_task(
        "Neuen Paper auf eBook Reader laden",
        project_id=int(2244466904),
        due_string=due,
    )
    add_reminder(item.id, due)


def add_before_tasks(activities, events_tomorrow):
    for event, pre_list in events_tomorrow:
        try:
            start = parser.parse(event["start"]["dateTime"])
        except KeyError:
            continue
        new_start_string = (start - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M")
        description_string = get_description(activities, pre_list)

        due = {"date": new_start_string}
        item = TODOIST_API.add_task(
            "* " + event["summary"] + " - Vorbereitung",
            project_id="2271705443",
            description=description_string,
        )
        update_due(item.id, due, add_reminder=True)


def get_description(activities, calendar_description=None):
    description_string = ""
    for activity in activities:
        description_string += "* " + activity["summary"] + ": \n"
        description_string += activity["description"].replace("*", "  *")
        description_string += "\n\n"
    if calendar_description is not None:
        description_string += "  * Kalender: \n"
        description_string += calendar_description.replace("*", "    *")
    return description_string


def get_vacation_mode():
    return bool(get_user_karma_vacation())


def get_items_by_todoist_label(label_id):
    return get_items_by_label(label_id)


def get_items_by_content(content_list):
    tasks = TODOIST_API.get_tasks()
    result = [task for task in tasks if any(content in task.content for content in content_list)]
    result = [task for task in result if not any(label in task.labels for label in ["To-Rethink-Done"])]
    return result


def move_item_to_notion_done(item):
    move_item_to_section(item.id, section_id=NOTION_DONE_SECTION_ID)
    set_label(item.id, label_id=TO_NOTION_DONE_LABEL_ID)


def move_item_to_microjournal_done(item):
    move_item_to_section(item.id, section_id=MICROJOURNAL_DONE_SECTION_ID)
    set_label(item.id, label_id=TO_MICROJOURNAL_DONE_LABEL_ID)


def move_item_to_rethink(item):
    move_item_to_project(item.id, project_id=RETHINK_PROJECT_ID)
    set_label(item.id, label_id=TO_RETHINK_DONE_LABEL_ID)


# 2. Value is the offset
supplements = {
    "Gold Omega 3 D3+K2 Sport Edition - Olimp": [60, 155],
    "Zinc Citrate Health Line - GN Laboratories": [120 * 2, 340],
}
time_to_order = 10


def check_order_supplements(df):
    used_this_year = df["properties~Supplements~checkbox"].value_counts().to_dict()[True]
    for key in supplements.keys():
        logger.info(
            "if ({used_this_year}-{offset}) % ({default_size} - {time_to_order}) == 0".format(
                used_this_year=used_this_year,
                default_size=supplements[key][0],
                time_to_order=time_to_order,
                offset=supplements[key][1],
            )
        )

        if (used_this_year - supplements[key][1]) % supplements[key][0] - time_to_order == 0:
            item = TODOIST_API.add_task(
                key + " bestellen",
                project_id="2244725398",
                due_string="tomorrow",
            )


def add_after_vacation_tasks():
    after_vacation_tasks = ["Monica mit Erblebnissen aus Urlaub pflegen", ""]
    [add_item_and_reminder(task_content, "2244725398", {"string": "tomorrow"}) for task_content in after_vacation_tasks]


def add_item_and_reminder(content, project_id, due):
    item = TODOIST_API.add_task(
        content,
        project_id=project_id,
        due_string=due,
    )
    add_reminder(item.id, due)


def get_items_by_todoist_project(project_id):
    return TODOIST_API.get_tasks(project_id=project_id)


def set_label(item_id, label_id):
    label = TODOIST_API.get_label(label_id)
    TODOIST_API.update_task(item_id, labels=[label.name])


def update_task_due(item, due):
    update_due(item.id, due)


def get_todoist_activity(**kwargs):
    logger.info("Getting Todoist activity with kwargs: {}".format(kwargs))
    activitiy = get_activity(**kwargs)
    # logger.info("Got Todoist activity: {}".format(activitiy))
    return activitiy


def check_if_last_item(book_title, items):
    for item in items:
        if item["book"] == book_title:
            return
    task = TODOIST_API.add_task(
        "Buch-Notizen zusammenfassen - {book} - Obsidian-Eintrag überdenken".format(book=book_title),
        project_id="2300202317", due_string="tomorrow")


def add_obsidian_task(file, description=None):
    content = "{file_name} §§§ Obsidian-Notiz überarbeiten".format(file_name=file.name)
    task = TODOIST_API.add_task(content=content, project_id=OBSIDIAN_REWORK_PROJECT_ID, description=description,
                                due_string="tomorrow")
    return task


def update_obsidian_task(item):
    new_content = "{content} §§§ Obsidian-Notiz überarbeiten".format(content=item.content)
    task = TODOIST_API.update_task(item.id, content=new_content, due_string="tomorrow")
    return task


def add_task(**kwargs):
    TODOIST_API.add_task(kwargs)


def add_not_matched_task(not_found):
    TODOIST_API.add_task(
        "Nicht-Gematchte Kategorien updaten",
        description=not_found,
        project_id="2244708745",
        due_string="today 19:30",
    )


def get_tasks_by_filter(filter_name):
    return TODOIST_API.get_tasks(filter=filter_name)

def get_project_names_by_ids(project_ids):
    return [TODOIST_API.get_project(project_id).name for project_id in project_ids]