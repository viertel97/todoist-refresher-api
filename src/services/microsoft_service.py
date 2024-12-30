import json
import os

import msal
import requests
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)

base_url = "https://graph.microsoft.com/v1.0/"
endpoint = base_url + "me"

AUTHORITY_URL = "https://login.microsoftonline.com/consumers/"

SCOPES = ["User.Read", "Files.Read.All"]

CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN = get_secrets(["microsoft/client_id", "microsoft/client_secret", "microsoft/refresh_token"])

client_instance = msal.ConfidentialClientApplication(client_id=CLIENT_ID, client_credential=CLIENT_SECRET, authority=AUTHORITY_URL)


def get_access_token():
	token = client_instance.acquire_token_by_refresh_token(refresh_token=REFRESH_TOKEN, scopes=SCOPES)
	return token["access_token"]


def get_files(path):
	access_token = get_access_token()
	headers = {"Authorization": "Bearer " + access_token}
	url = base_url + "me/drive/root:/" + path + ":/children"
	response = requests.get(url, headers=headers)
	return response.json()


def get_zettelkasten_from_onedrive():
	files = get_files("Documents/PARA/3. Resources/Obsidian/My Vault/0000_Zettelkasten")
	files = sorted(files["value"], key=lambda x: x["lastModifiedDateTime"])
	return files


def get_koreader_from_onedrive():
	files = get_files("Anwendungen/KOreader/settings")
	file = [file for file in files["value"] if file["name"] == "statistics.sqlite3"][0]
	return file


def get_koreader_settings():
	koreader_file = get_koreader_from_onedrive()
	logger.info(koreader_file)
	download_link = koreader_file["@microsoft.graph.downloadUrl"]
	r = requests.get(download_link)
	with open("statistics.sqlite3", "wb") as f:
		f.write(r.content)


def get_file_list(path, access_token):
	headers = {
		"Authorization": f"Bearer {access_token}",
		"Content-Type": "application/json",
	}

	url = base_url + "me/drive/root:/" + "/".join(path.split("/")) + ":/"
	logger.info("get file list from path: " + url)
	response = requests.get(url, headers=headers)
	if response.status_code != 200:
		raise Exception("Error getting file list", response.text)
	destination_folder_id = response.json()["id"]
	list_files_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{destination_folder_id}/children"

	response = requests.get(list_files_url, headers=headers)
	return response.json(), destination_folder_id


def create_backup(path, access_token):
	folder_path = os.path.dirname(path)
	logger.info("folder path: " + folder_path)
	file_list, destination_folder_id = get_file_list(folder_path, access_token)
	return destination_folder_id


def upload_file(local_file_path, access_token, destination_folder_id):
	file_name = os.path.basename(local_file_path)
	upload_url = f"https://graph.microsoft.com/v1.0/drive/items/{destination_folder_id}:/{file_name}:/content"

	headers = {
		"Authorization": f"Bearer {access_token}",
		"Content-Type": "application/octet-stream",
	}

	with open(local_file_path, "rb") as file:
		response = requests.put(upload_url, headers=headers, data=file)
	if response.status_code == 200 or response.status_code == 201:
		logger.info("Successfully uploaded file " + file_name)
		return response.json()
	logger.error(response.json())
	raise Exception("Error uploading file")


def create_folder(folder_name, access_token):
	destination_folder_id = "4DFC7D9FFC3F99E3!1611011"
	upload_url = f"https://graph.microsoft.com/v1.0/drive/items/{destination_folder_id}/children"

	headers = {
		"Authorization": f"Bearer {access_token}",
		"Content-Type": "application/json",
	}
	data = {
		"name": folder_name,
		"folder": {},
		"@microsoft.graph.conflictBehavior": "replace",
	}
	response = requests.post(upload_url, headers=headers, data=json.dumps(data))
	if response.status_code == 200 or response.status_code == 201:
		logger.info("Successfully created new folder " + folder_name)
		return response.json()
	logger.error(response.json())
	raise Exception("Error creating new folder")


def upload_transcribed_article_to_onedrive(local_file_path, folder_name):
	access_token = get_access_token()
	create_folder_response = create_folder(folder_name, access_token)
	upload_file_response = upload_file(local_file_path, access_token, create_folder_response["id"])
	os.remove(local_file_path)
	return upload_file_response
