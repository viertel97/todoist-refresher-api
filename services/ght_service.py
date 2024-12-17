import os

from loguru import logger
from quarter_lib_old.todoist import update_due

from services.database_service import get_ght_results
from services.todoist_service import TODOIST_API

logger.add(
	os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
	format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
	backtrace=True,
	diagnose=True,
)


def update_ght():
	logger.info("start update_good_habit_tracker")
	ght, total, kw = get_ght_results()
	total_text = "Total: " + str(total) + "€"
	total_text = ght.to_string(index=False, header=False) + "\n\n" + total_text
	due = {"string": "Monday 10am"}
	item = TODOIST_API.add_task(
		content="{total}€ überweisen (KW {kw})".format(total=total, kw=kw),
		description=total_text,
		project_id="2244466904",
		label=["Digital"],
	)
	update_due(item.id, due, add_reminder=True)
	logger.info("end update_good_habit_tracker")
