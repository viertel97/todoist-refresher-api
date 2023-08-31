import os.path
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/fitness.activity.read", "https://www.googleapis.com/auth/calendar.readonly"]

if os.name == "nt":
    pickle_path = r"/config/token.pickle"
    creds_path = r"/config/cred7.json"
else:
    pickle_path = "/home/pi/python/todoist-refresher/config/token.pickle"
    creds_path = "/home/pi/python/todoist-refresher/config/cred7.json"


creds = None
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server()
    else:
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server()
    with open(pickle_path, "wb") as token:
        pickle.dump(creds, token)

calendar_service = build("calendar", "v3", credentials=creds)
calendar_list = calendar_service.calendarList().list().execute()
print(calendar_list)
