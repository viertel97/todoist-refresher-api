from quarter_lib.logging import setup_logging
from quarter_lib_old.todoist import update_due

from src.services.database_service import get_ght_results
from src.services.todoist_service import TODOIST_API

logger = setup_logging(__file__)


async def update_ght():
	logger.info("start update_good_habit_tracker")
	ght, total, kw = await get_ght_results()
	if len(ght) <= 0:
		logger.info("No results found for week {}".format(kw))
		return
	total_text = "Total: " + str(total) + "€"
	total_text = ght.to_string(index=False, header=False) + "\n\n" + total_text
	due = {"string": "Monday 10am"}
	item = TODOIST_API.add_task(
		content=f"{total}€ überweisen (KW {kw})",
		description=total_text,
		project_id="2244466904",
		labels=["Digital"],
	)
	update_due(item.id, due, add_reminder=True)
	logger.info("end update_good_habit_tracker")
