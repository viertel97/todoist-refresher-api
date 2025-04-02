from dateutil import parser


def get_date_or_datetime(event, key):
	if event["status"] != "cancelled":
		date_or_datetime = event[key]
		if "date" in date_or_datetime:
			date_or_datetime = date_or_datetime["date"]
		elif "dateTime" in date_or_datetime:
			date_or_datetime = date_or_datetime["dateTime"]
		return parser.parse(date_or_datetime).replace(tzinfo=None)
