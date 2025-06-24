import time

from quarter_lib.logging import setup_logging

from src.services.telegram_service import send_to_telegram
from src.services.todoist_service import (
	get_items_by_todoist_project,
	get_rework_projects,
	run_todoist_sync_commands,
)

logger = setup_logging(__file__)

OBSIDIAN_AUTOSTART_TRIGGER = "Obsidian-Eintrag überdenken"

NUMBER_OF_ITEMS_PER_CHUNK = 40

def get_smallest_project():
	rework_projects = get_rework_projects()
	project_sizes = [len(get_items_by_todoist_project(project.id)) for project in rework_projects]
	min_size = min(project_sizes)
	idx = project_sizes.index(min_size)
	return rework_projects[idx], min_size, idx


def split_str_to_chars(text, chars=2047):
	return [text[i : i + chars] for i in range(0, len(text), chars)][0]


async def add_rework_tasks(tasks):
	project, min_size, idx = get_smallest_project()
	await send_to_telegram(f"List {idx + 1} ({project.id}) was chosen as the smallest project with {min_size} items")
	if min_size + len(tasks) <= 300:
		command_list = []
		for task in tasks:
			if type(task) == tuple:
				temp_task = list(task)
				temp_task[0] = split_str_to_chars(temp_task[0])
				command_list.append(
					{
						"type": "item_add",
						"args": {
							"content": temp_task[0],
							"description": temp_task[1],
							"project_id": project.id,
						},
					},
				)
			else:
				task = split_str_to_chars(task)
				command_list.append(
					{
						"type": "item_add",
						"args": {"content": task, "project_id": project.id},
					},
				)
		logger.info(f"adding batch of {len(command_list)} tasks")
		chunks_of_40 = list(chunks(command_list, NUMBER_OF_ITEMS_PER_CHUNK))
		for chunk in chunks_of_40:
			logger.info(f"adding chunk of {len(chunk)} tasks")
			response = run_todoist_sync_commands(chunk)
			logger.info(f"response code {response.status_code}")
			if response.status_code != 200:
				logger.error(f"response body {response.text}")
				raise Exception("Error while adding to Todoist " + response.text)
			logger.info(f"response:\n{response.json()}")
			await send_to_telegram(f"Added {len(chunk)} tasks")
			if len(chunk) == NUMBER_OF_ITEMS_PER_CHUNK:
				logger.info("sleeping for 10 seconds")
				time.sleep(10)
	else:
		error_message = f"Project {project.id} is full and cannot handle {len(tasks)} more tasks"
		await send_to_telegram(error_message)
		raise Exception(error_message)


def chunks(lst, n):
	for i in range(0, len(lst), n):
		yield lst[i : i + n]
