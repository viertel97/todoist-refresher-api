import os

import msal
import requests
from loguru import logger
from quarter_lib.akeyless import get_secrets

base_url = "https://graph.microsoft.com/v1.0/"
endpoint = base_url + "me"

AUTHORITY_URL = "https://login.microsoftonline.com/consumers/"

SCOPES = ["User.Read", "Files.Read.All"]

CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN = get_secrets(
    ['microsoft/client_id', 'microsoft/client_secret', 'microsoft/refresh_token'])

client_instance = msal.ConfidentialClientApplication(
    client_id=CLIENT_ID,
    client_credential=CLIENT_SECRET,
    authority=AUTHORITY_URL
)

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def get_access_token():
    token = client_instance.acquire_token_by_refresh_token(
        refresh_token=REFRESH_TOKEN,
        scopes=SCOPES)
    return token['access_token']


def get_files(path):
    access_token = get_access_token()
    headers = {'Authorization': 'Bearer ' + access_token}
    url = base_url + "me/drive/root:/" + path + ":/children"
    response = requests.get(url, headers=headers)
    return response.json()


def get_zettelkasten_from_onedrive():
    files = get_files("Documents/PARA/3. Resources/Obsidian/My Vault/0000_Zettelkasten")
    files = sorted(files['value'], key=lambda x: x['lastModifiedDateTime'])
    return files


def get_koreader_from_onedrive():
    files = get_files("Anwendungen/KOreader/settings")
    file = [file for file in files['value'] if file['name'] == 'statistics.sqlite3'][0]
    return file


def get_koreader_settings():
    koreader_file = get_koreader_from_onedrive()
    logger.info(koreader_file)
    download_link = koreader_file["@microsoft.graph.downloadUrl"]
    r = requests.get(download_link)
    with open("statistics.sqlite3", "wb") as f:
        f.write(r.content)
