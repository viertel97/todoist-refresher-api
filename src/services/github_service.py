import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import git
import yaml
from github import Github, InputGitTreeElement
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

from src.helper.path_helper import slugify
from src.services.telegram_service import send_to_telegram

logger = setup_logging(__file__)

github_token = get_secrets(["github/pat_obsidian"])

g = Github(github_token)

temp = Path("/ssh/id_rsa")
git_ssh_cmd = "ssh -i %s" % temp
branch_name = "main"
repo_clone_dir = "temp_repo"
ssh_url = "git@github.com:viertel97/obsidian.git"

WORK_INBOX_FILE_PATH = "/0300_Spaces/Work/Index.md"


def get_previous_description(previous_desc):
	if previous_desc is None:
		return None, None
	desc = previous_desc.split("---")
	if len(desc) > 1:
		desc_dict = yaml.load(desc[1], Loader=yaml.FullLoader)
		return desc_dict, desc[2]
	return None, previous_desc


def generate_metadata(
	summary: str,
	people: list,
	emotions: list,
	happened_at: datetime,
	created_at: datetime,
	updated_at: datetime,
	uuid: str,
	original_description: str,
	drugs,
) -> tuple[dict, str]:
	metadata_json = {
		"summary": summary,
		"created_at": created_at.strftime("%Y-%m-%dT%H:%M:%S"),
		"happened_at": happened_at.strftime("%Y-%m-%d"),
		"updated_at": updated_at.strftime("%Y-%m-%dT%H:%M:%S"),
		"uuid": uuid,
		"people": [f"[[{person}]]" for person in people],
		"emotions": emotions,
		"drugs": drugs,
	}

	additional_metadata, cleaned_description = get_previous_description(original_description)
	if additional_metadata:
		metadata_json.update(additional_metadata)

	return metadata_json, cleaned_description


def generate_file_content(summary:str, description:str) -> str:
	return_string = f"# {summary}\n\n"
	if description:
		return_string += f"{description}\n\n"
	return return_string


def get_files_with_modification_date(path):
	try:
		logger.info(
			f"Cloning repo {ssh_url} to {repo_clone_dir} and branch {branch_name} and gathering created and last modified dates for {path}"
		)
		logger.info(f"git_ssh_cmd: {git_ssh_cmd}")
		local_repo = git.Repo.clone_from(
			ssh_url,
			to_path=repo_clone_dir,
			branch=branch_name,
			env=dict(GIT_SSH_COMMAND=git_ssh_cmd),
		)

		file_dates = {}

		# Get commits in chronological order (oldest first)
		for commit in reversed(list(local_repo.iter_commits(rev=branch_name))):
			for file_path in commit.stats.files:
				if path in file_path:
					full_path = os.path.join(repo_clone_dir, file_path)
					if not os.path.exists(full_path):
						continue

					# Initialize dictionary if seeing file for the first time
					if file_path not in file_dates:
						file_dates[file_path] = {
							"created_date": commit.committed_date,
							"last_modified_date": commit.committed_date,
						}
					else:
						file_dates[file_path]["last_modified_date"] = commit.committed_date

		contents = [
			{
				"path": k,
				"created_date": v["created_date"],
				"last_modified_date": v["last_modified_date"],
			}
			for k, v in file_dates.items()
			if k.endswith(".md")
		]
	finally:
		shutil.rmtree("temp_repo")

	return contents


def get_files(path):
	repo = g.get_repo("viertel97/obsidian")
	logger.info(f"Getting files in {path}")
	contents = repo.get_contents(path)
	content_list = []
	while contents:
		file_content = contents.pop(0)
		if file_content.type == "dir":
			contents.extend(repo.get_contents(file_content.path))
		else:
			content_list.append(file_content.path)
	content_list = [file for file in content_list if file.endswith(".md")]
	logger.info(f"Found {len(content_list)} files in {path}")
	return content_list


async def create_obsidian_markdown_in_git(sql_entry, run_timestamp, drug_date_dict, files_in_repo):
	repo = g.get_repo("viertel97/obsidian")
	file_name = slugify(sql_entry["filename"]) + ".md"
	file_path = (
		f"0300_Spaces/Social Circle/Activities/{sql_entry['happened_at'].year!s}/{sql_entry['happened_at'].strftime('%m-%B')!s}/{file_name}"
	)

	people = "" if sql_entry["people"] is None else sorted(sql_entry["people"].split("~"))
	# remove "Inbox" from people if it exists
	if "Inbox" in people:
		people.remove("Inbox")
	emotions = "" if sql_entry["emotions"] is None else sorted(sql_entry["emotions"].split("~"))
	summary = sql_entry["summary"]
	happened_at = sql_entry["happened_at"]
	created_at = sql_entry["created_at"]
	updated_at = sql_entry["updated_at"]
	uuid = sql_entry["uuid"]
	description = sql_entry["description"]
	drugs = drug_date_dict.get(happened_at, [])

	metadata_dict, cleaned_description = generate_metadata(
		summary,
		people,
		emotions,
		happened_at,
		created_at,
		updated_at,
		uuid,
		description,
		drugs,
	)

	file_content = generate_file_content(summary, cleaned_description)


	if file_path in files_in_repo:
		old_file = repo.get_contents(file_path)
		old_file_content = old_file.decoded_content.decode("utf-8")
		logger.info(f"File {file_name} already exists in github but with different content")
		old_metadata, old_content = get_previous_description(old_file_content)
		if old_metadata:
			old_metadata = {k: v for k, v in old_metadata.items() if v is not None and v != ""}
			old_metadata.update(metadata_dict)

		metadata_str = "---\n"
		metadata_str += yaml.dump(old_metadata, allow_unicode=False, default_flow_style=False)
		metadata_str += "\n---\n\n"

		repo.update_file(
			path=file_path,
			message=f"obsidian-refresher: {run_timestamp}",
			content=metadata_str + old_content + file_content,
			sha=old_file.sha,
		)
		logger.info(f"Updated {file_name} in github")
		await send_to_telegram(f"{file_name} already exists - updating it with new content")
	else:
		metadata_str = "---\n"
		metadata_str += yaml.dump(metadata_dict, allow_unicode=False, default_flow_style=False)
		metadata_str += "\n---\n\n"

		logger.info(f"Changing filename from {sql_entry['filename']} to {file_name}")

		logger.info(f"Creating {file_name} in github with content:\n{metadata_str + file_content}")
		repo.create_file(
			path=file_path,
			message=f"obsidian-refresher: {run_timestamp}",
			content=metadata_str + file_content,
		)
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
	repo.update_file(
		file.path,
		f"obsidian-refresher (work): {run_timestamp}",
		f"{old_content} /n/n{content_to_add}",
		file.sha,
	)


def add_files_to_repository(list_of_files, commit_message, subpath, repository_name="obsidian", branch_name="main"):
	repo = g.get_repo(g.get_user().login + "/" + repository_name)
	logger.info(f"repo: {repo}")

	blobs = []
	for file in list_of_files:
		blob = repo.create_git_blob(
			content=file["content"],
			encoding="utf-8",
		)
		blobs.append(blob)
		logger.info(f"Created blob for {file['filename']}: {blob}")

	tree_elements = [
		InputGitTreeElement(
			path=subpath + file["filename"],
			mode="100644",
			type="blob",
			sha=blob.sha,
		)
		for file, blob in zip(list_of_files, blobs)
	]

	base_tree = repo.get_git_tree(sha=repo.get_branch(branch_name).commit.sha)
	new_tree = repo.create_git_tree(tree=tree_elements, base_tree=base_tree)
	logger.info(f"new_tree: {new_tree}")

	commit = repo.create_git_commit(
		message=commit_message,
		tree=new_tree,
		parents=[repo.get_git_commit(repo.get_branch(branch_name).commit.sha)],
	)
	logger.info(f"commit: {commit}")

	hello_world_ref = repo.get_git_ref(ref="heads/" + branch_name)
	hello_world_ref.edit(sha=commit.sha)
	logger.info("DONE")
