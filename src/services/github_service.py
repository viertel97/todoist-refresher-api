import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import git
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
	desc = previous_desc.split("---")
	if len(desc) > 1:
		temp_desc = desc[1]
		temp_desc = temp_desc.replace("\r", "").replace("\n", "").replace("\t", "").replace("  ", "")
		temp_desc = temp_desc.replace(",}", "}")
		temp_json = json.loads(temp_desc)
		# remove two first characters from desc
		return {k: v for k, v in temp_json.items() if v}, desc[2][1:]
	return None, previous_desc


def generate_metadata(
	summary,
	people: list,
	emotions: list,
	happened_at,
	created_at,
	updated_at,
	uuid,
	original_description,
	drugs,
):
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

	additional_metadata, cleaned_description = get_previous_description(original_description)
	if additional_metadata:
		metadata_json.update(additional_metadata)

	return_string = "---\n"
	return_string += json.dumps(metadata_json, indent=4, sort_keys=True, ensure_ascii=False)
	return_string += "\n---\n\n"
	return_string += "# People\n"
	for person in people:
		return_string += f"- [[{person}]]\n"
	return_string += "\n"

	return return_string, cleaned_description


def generate_file_content(summary, description):
	return_string = f"# {summary}\n\n"
	if description:
		return_string += f"{description}\n\n"
	return return_string


def get_files_with_modification_date(path):
	try:
		logger.info(f"Cloning repo {ssh_url} to {repo_clone_dir} and branch {branch_name} and gathering last modified date for {path}")
		logger.info(f"git_ssh_cmd: {git_ssh_cmd}")
		local_repo = git.Repo.clone_from(
			ssh_url,
			to_path=repo_clone_dir,
			branch=branch_name,
			env=dict(GIT_SSH_COMMAND=git_ssh_cmd),
		)

		file_last_modified = {}
		for commit in local_repo.iter_commits(rev=branch_name):
			for file_path in commit.stats.files:
				if path in file_path:
					path_to_check = os.path.join(repo_clone_dir, file_path)
					if file_path not in file_last_modified and os.path.exists(path_to_check):
						file_last_modified[file_path] = commit.committed_date

		contents = [{"path": k, "last_modified_date": v} for k, v in file_last_modified.items()]
	finally:
		shutil.rmtree("temp_repo")
	contents = [content for content in contents if content["path"].endswith(".md")]
	return contents


def get_files(path):
	repo = g.get_repo("viertel97/obsidian")
	contents = repo.get_contents(path)
	content_list = []
	while contents:
		file_content = contents.pop(0)
		if file_content.type == "dir":
			contents.extend(repo.get_contents(file_content.path))
		else:
			content_list.append(file_content.path)
	content_list = [file for file in content_list if file.endswith(".md")]
	return content_list


async def create_obsidian_markdown_in_git(sql_entry, run_timestamp, drug_date_dict):
	repo = g.get_repo("viertel97/obsidian")

	# check if the file already exists
	file_name = slugify(sql_entry["filename"]) + ".md"
	file_path = (
		f"0300_Spaces/Social Circle/Activities/{sql_entry['happened_at'].year!s}/{sql_entry['happened_at'].strftime('%m-%B')!s}/{file_name}"
	)

	if file_path in get_files("0300_Spaces/Social Circle/Activities"):
		logger.info(f"File {file_name} already exists in github")
		await send_to_telegram(f"File {file_name} already exists in github")
		return

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

	logger.info(f"Changing filename from {sql_entry['filename']} to {file_name}")

	metadata, cleaned_description = generate_metadata(
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
	logger.info(f"Creating {file_name} in github with content:\n{metadata + file_content}")
	repo.create_file(
		path=file_path,
		message=f"obsidian-refresher: {run_timestamp}",
		content=metadata + file_content,
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
