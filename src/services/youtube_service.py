import random

import pytube

from src.services.todoist_service import THIS_WEEK_PROJECT_ID, TODOIST_API

TO_TRANSCRIBE_PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLC9ZZKXI-p0DmAey733oUFb9D0S7WeLN3"
TO_ANNOTATE_PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLC9ZZKXI-p0ArOZggeHvKV8fATjEbxhhb"


def add_video_annotate_task():
	playlist = pytube.Playlist(TO_ANNOTATE_PLAYLIST_URL)
	if playlist:
		item = random.choice(playlist.video_urls)
		yt = pytube.YouTube(item)
		TODOIST_API.add_task(
			content=f'Annotate "[{yt.title}]({yt.watch_url})" in Zotero + Remove from [Playlist]({TO_ANNOTATE_PLAYLIST_URL})',
			project_id=THIS_WEEK_PROJECT_ID,
		)
		return True
	return False


def add_video_transcribe_tasks():
	playlist = pytube.Playlist(TO_TRANSCRIBE_PLAYLIST_URL)
	if playlist:
		for item in playlist.video_urls:
			yt = pytube.YouTube(item)
			TODOIST_API.add_task(
				content=f'Transcribe "[{yt.title}]({yt.watch_url})" and add to Zotero + Remove from [Playlist]({TO_TRANSCRIBE_PLAYLIST_URL})',
				project_id=THIS_WEEK_PROJECT_ID,
				labels=["Digital"],
			)
			return True
	return False
