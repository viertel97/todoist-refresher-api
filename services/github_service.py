import json
from datetime import datetime

from github import Github
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

from helper.path_helper import slugify

logger = setup_logging(__file__)

github_token = get_secrets(
    ["github/pat_obsidian"]
)

g = Github(github_token)

WORK_INBOX_FILE_PATH = "/0300_Spaces/Work/Index.md"


def get_previous_description(previous_desc):
    desc = previous_desc.split("---")
    if len(desc) > 1:
        desc = desc[1]
        desc = desc.replace('\r', '').replace('\n', '').replace('\t', '').replace("  ", "")
        desc = desc.replace(",}", "}")
        temp_json = json.loads(desc)
        return {k: v for k, v in temp_json.items() if v}
    else:
        return None


def generate_metadata(summary, people: list, emotions: list, happened_at, created_at, updated_at, uuid,
                      original_description, drugs):
    metadata_json = {
        "summary": summary,
        "created_at": created_at.strftime("%d-%m-%Y %H:%M:%S"),
        "happened_at": happened_at.strftime("%Y-%m-%d"),
        "updated_at": updated_at.strftime("%d-%m-%Y %H:%M:%S"),
        "uuid": uuid,
        "people": people,
        "emotions": emotions,
        "drugs": drugs,
    }

    previous_description = get_previous_description(original_description)
    if previous_description:
        metadata_json.update(previous_description)
        cleaned_description = original_description.split("---")[2]
    else:
        cleaned_description = None

    return_string = "---\n"
    return_string += json.dumps(metadata_json, indent=4, sort_keys=True, ensure_ascii=False)
    return_string += "\n---\n\n"
    return_string += f"# People\n"
    for person in people:
        return_string += f"- [[{person}]]\n"
    return_string += "\n"

    return return_string, cleaned_description or original_description


def generate_file_content(summary, description):
    return_string = f"# {summary}\n\n"
    if description:
        return_string += f"{description}\n\n"
    return return_string


def get_files(path):
    g = Github(github_token)
    repo = g.get_repo("viertel97/obsidian")
    contents = repo.get_contents(path)
    return contents


def get_zettelkasten_from_github():
    files = get_files("0000_Zettelkasten")
    # sorted_files = sorted(files, key=lambda x: x.last_modified_date)
    return files


def create_obsidian_markdown_in_git(sql_entry, run_timestamp, drug_date_dict):
    repo = g.get_repo("viertel97/obsidian")

    people = "" if sql_entry["people"] is None else sorted(sql_entry["people"].split("~"))
    emotions = "" if sql_entry["emotions"] is None else sorted(sql_entry["emotions"].split("~"))
    summary = sql_entry["summary"]
    happened_at = sql_entry["happened_at"]
    created_at = sql_entry["created_at"]
    updated_at = sql_entry["updated_at"]
    uuid = sql_entry["uuid"]
    description = sql_entry["description"]

    drugs = drug_date_dict.get(happened_at, [])

    file_name = slugify(sql_entry['filename']) + ".md"
    logger.info(f"Changing filename from {sql_entry['filename']} to {file_name}")

    metadata, cleaned_description = generate_metadata(summary, people, emotions, happened_at, created_at, updated_at,
                                                      uuid,
                                                      description, drugs)

    file_content = generate_file_content(summary, cleaned_description)
    logger.info(f"Creating {file_name} in github with content:\n{metadata + file_content}")
    repo.create_file(path="0300_Spaces/Social Circle/Activities/" + file_name,
                     message=f"obsidian-refresher: {run_timestamp}", content=metadata + file_content)
    logger.info(f"Created {file_name} in github")

def add_to_work_inbox(work_list):
    run_timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    repo = g.get_repo("viertel97/obsidian")
    file = repo.get_contents(WORK_INBOX_FILE_PATH)
    old_content = file.decoded_content.decode("utf-8")
    content_to_add = f"\n\n## {run_timestamp}\n"
    for item in work_list:
        if item.description:
            content_to_add += f"- {item.content} - {item.description}\n"
        else:
            content_to_add += f"- {item.content}\n"
    # update
    repo.update_file(file.path, f"obsidian-refresher (work): {run_timestamp}",f"{old_content} /n/n{content_to_add}", file.sha)