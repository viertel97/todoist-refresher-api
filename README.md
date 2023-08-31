# todoist-refresher

Todoist-Refresher is a scheduler that automates various tasks related to Todoist, Notion, Monica, and other tools. The
scheduler is designed to run on a server and is triggered via CronJobs.

## Features

### Hourly

- A separate routine for moving new Todoist Tasks to Notion, Microjournal in Monica or another To-Rethink Todoist List.
- A routine to remove the Inbox-User from Monica activities where other participants has been added

### Daily

- Check if there has been an event in the Google Calendar or in Monica which needs to be reworked. Also adds a
  preparation task to Todoist if there has been made notes before the event.
- Moves archive activities in Monica to a later date.
- Updates the Habit Tracker in Notion.
- Updates the "Vacation" field in Notion.

### Bi-Weekly

- Creates Todoist tasks from a special "To-Think-About"-Todoist Project.
- Creates Todoist task from the oldest and a random Obsidian Note in my Vault.
- Creates Todoist task from an annotation made in a book and processed by the Telegram
  Assistant (https://github.com/viertel97/telegram-assistant)

### Weekly

- Creates Todoist task from my TPT Notion Database for the implementation of new function to my projects.
- Task to annotate a YouTube video I added to a special playlist.
- Analyzes my habits tracked by my Good-Habit-Tracker (https://github.com/viertel97/GHT) and creates a
  reward-task from it.