import time
import urllib.parse
from datetime import datetime, timedelta

import requests
from dateutil import parser
from quarter_lib.akeyless import get_secrets
from quarter_lib.google_calendar import build_calendar_service, get_dict
from quarter_lib.logging import setup_logging
from src.services.monica_service import get_events_from_calendar_for_days

MAPS_API_KEY, HOME_ADDRESS = get_secrets(["google/maps_api_key", "google/home_address"])

logger = setup_logging(__name__)

def calculate_travel_time(origin, destination, departure_time=None, mode="driving", traffic_model="best_guess"):
	"""
	Calculate travel time between two points using Google Maps Distance Matrix API

	Args:
		origin (str): Starting location (address, coordinates, place_id)
		destination (str): Destination location (address, coordinates, place_id)
		departure_time (datetime, optional): When to depart. If None, uses current time
		mode (str): Travel mode - 'driving', 'walking', 'bicycling', 'transit'
		traffic_model (str): Traffic model - 'best_guess', 'pessimistic', 'optimistic'

	Returns:
		dict: Travel information including duration, distance, and duration in traffic
	"""
	base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"

	# Convert departure_time to Unix timestamp
	if departure_time is None:
		departure_time = datetime.now()

	departure_timestamp = int(departure_time.timestamp())

	# Build parameters
	params = {
		"origins": origin,
		"destinations": destination,
		"mode": mode,
		"departure_time": departure_timestamp,
		"traffic_model": traffic_model,
		"key": MAPS_API_KEY,
	}

	# Only include traffic model for driving mode
	if mode != "driving":
		params.pop("traffic_model", None)

	try:
		response = requests.get(base_url, params=params)
		response.raise_for_status()

		data = response.json()

		if data["status"] != "OK":
			raise Exception(f"API Error: {data['status']}")

		if data["rows"][0]["elements"][0]["status"] != "OK":
			raise Exception(f"Route Error: {data['rows'][0]['elements'][0]['status']}")

		element = data["rows"][0]["elements"][0]

		result = {
			"distance": {
				"text": element["distance"]["text"],
				"value": element["distance"]["value"],  # in meters
			},
			"duration": {
				"text": element["duration"]["text"],
				"value": element["duration"]["value"],  # in seconds
			},
			"origin": data["origin_addresses"][0],
			"destination": data["destination_addresses"][0],
			"departure_time": departure_time.isoformat(),
		}

		# Add duration in traffic if available (only for driving mode)
		if "duration_in_traffic" in element:
			result["duration_in_traffic"] = {
				"text": element["duration_in_traffic"]["text"],
				"value": element["duration_in_traffic"]["value"],  # in seconds
			}

		return result

	except requests.exceptions.RequestException as e:
		raise Exception(f"Request failed: {e}")
	except KeyError as e:
		raise Exception(f"Unexpected API response format: {e}")


def get_travel_start_time(destination, event_start_time, origin="current_location", buffer_minutes=10, mode="driving", traffic_model="pessimistic"
):
	"""
	Calculate when to leave to arrive at destination by a specific time

	Args:
		destination (str): Destination address
		event_start_time (datetime): When you need to arrive
		origin (str): Starting location
		buffer_minutes (int): Extra buffer time in minutes
		mode (str): Travel mode
		traffic_model (str): Traffic model

	Returns:
		dict: Suggested departure time and travel info
	"""
	# Calculate travel time departing now
	travel_info = calculate_travel_time(origin, destination, event_start_time, mode, traffic_model)

	# Use duration_in_traffic if available, otherwise use regular duration
	if "duration_in_traffic" in travel_info:
		travel_seconds = travel_info["duration_in_traffic"]["value"]
	else:
		travel_seconds = travel_info["duration"]["value"]

	# Add buffer time
	total_seconds = travel_seconds + (buffer_minutes * 60)

	# Calculate departure time
	departure_time = event_start_time - timedelta(seconds=total_seconds)

	return {
		"departure_time": departure_time,
		"travel_duration": travel_seconds // 60,  # in minutes
		"buffer_minutes": buffer_minutes,
		"total_time_needed": total_seconds // 60,  # in minutes
		"travel_info": travel_info,
		"mode": mode,
		"traffic_model": traffic_model,
	}


def create_travel_events(travel_type, destination, event_start_time, origin="current_location", walking_buffer=5, driving_buffer=5):
	"""
	Create both walking and driving travel events for a calendar event

	Args:
		destination (str): Destination address
		event_start_time (datetime): When you need to arrive
		origin (str): Starting location
		walking_buffer (int): Buffer time for walking in minutes
		driving_buffer (int): Buffer time for driving in minutes

	Returns:
		dict: Both walking and driving travel information
	"""

	match travel_type:
		case "walking":
			walking_info = get_travel_start_time(
				destination=destination,
				event_start_time=event_start_time,
				origin=origin,
				buffer_minutes=walking_buffer,
				mode=travel_type,
			)
			return {"walking": walking_info}
		case "driving":
			driving_info = get_travel_start_time(
				destination=destination,
				event_start_time=event_start_time,
				origin=origin,
				buffer_minutes=driving_buffer,
				mode=travel_type,
				traffic_model="pessimistic",
			)
			return {"driving": driving_info}
		case "bicycling":
			bicycle_info = get_travel_start_time(
				destination=destination,
				event_start_time=event_start_time,
				origin=origin,
				buffer_minutes=walking_buffer,
				mode=travel_type
			)
			return {"bicycling": bicycle_info}
		case None:
			walking_info = get_travel_start_time(
				destination=destination,
				event_start_time=event_start_time,
				origin=origin,
				buffer_minutes=walking_buffer,
				mode="walking",
			)
			driving_info = get_travel_start_time(
				destination=destination,
				event_start_time=event_start_time,
				origin=origin,
				buffer_minutes=driving_buffer,
				mode="driving",
				traffic_model="pessimistic",
			)

			bicycle_info = get_travel_start_time(
				destination=destination,
				event_start_time=event_start_time,
				origin=origin,
				buffer_minutes=walking_buffer,
				mode="bicycling",
			)

			return {"walking": walking_info, "driving": driving_info, "bicycling": bicycle_info}

def format_travel_event_details(travel_info) -> dict:
	"""
	Format travel information into calendar event details

	Args:
		travel_info (dict): Travel information from get_travel_start_time

	Returns:
		dict: Formatted event information
	"""
	mode = travel_info["mode"].title()
	traffic_info = f" ({travel_info['traffic_model']})" if travel_info["mode"] == "driving" else ""

	if travel_info["mode"] == "driving":
		title = f"Drive to '{travel_info['travel_info']['destination']}' from '{travel_info['travel_info']['origin']}'"
	elif travel_info["mode"] == "walking":
		title = f"Walk to '{travel_info['travel_info']['destination']}' from '{travel_info['travel_info']['origin']}'"
	elif travel_info["mode"] == "bicycling":
		title = f"Bike to '{travel_info['travel_info']['destination']}' from '{travel_info['travel_info']['origin']}'"
	else:
		title = f"Travel to '{travel_info['travel_info']['destination']}' from '{travel_info['travel_info']['origin']}'"

	description = f"""
	Travel Information:
	• Mode: {mode}{traffic_info}
	• From: {travel_info["travel_info"]["origin"]}
	• To: {travel_info["travel_info"]["destination"]}
	• Distance: {travel_info["travel_info"]["distance"]["text"]}
	• Travel Time: {travel_info["travel_duration"]} minutes
	• Buffer Time: {travel_info["buffer_minutes"]} minutes
	• Total Time: {travel_info["total_time_needed"]} minutes""".strip()

	return {
		"title": title,
		"description": description,
		"start_time": travel_info["departure_time"],
		"end_time": travel_info["departure_time"] + timedelta(minutes=travel_info["total_time_needed"] + 1),
		"location": travel_info["travel_info"]["origin"],
		"maps_url": create_departure_maps_url(
			travel_info["travel_info"]["origin"],
			travel_info["travel_info"]["destination"],
			depart_at=travel_info["departure_time"],
			travel_mode=travel_info["mode"],
		),
	}


# Travel mode mapping for Google Maps URLs
TRAVEL_MODES = {
	"driving": "0",
	"car": "0",
	"walking": "2",
	"walk": "2",
	"bicycling": "1",
	"bike": "1",
	"cycling": "1",
	"transit": "3",
	"public_transport": "3",
	"flight": "4",
	"flying": "4",
}


def create_departure_maps_url(origin, destination, depart_at=None, arrival_time=None, travel_mode="driving"):
	base_url = "https://www.google.com/maps/dir/"
	origin_encoded = urllib.parse.quote(origin, safe="")
	destination_encoded = urllib.parse.quote(destination, safe="")

	url = (
		f"{base_url}{origin_encoded}/{destination_encoded}/data=!4m17!4m16!1m5!1m1!1s0x0:0x0!2m2!1d0!2d0!1m5!1m1!1s0x0:0x0!2m2!1d0!2d0!2m2"
	)

	# Add time parameters
	if arrival_time:
		# Convert to Unix timestamp
		timestamp = int(time.mktime(arrival_time.timetuple()))
		url += f"!6e1!8j{timestamp}"
	elif depart_at:
		# Convert to Unix timestamp
		timestamp = int(time.mktime(depart_at.timetuple()))
		url += f"!6e2!8j{timestamp}"

	# Add travel mode
	if travel_mode.lower() in TRAVEL_MODES:
		mode_code = TRAVEL_MODES[travel_mode.lower()]
		url += f"!3e{mode_code}"

	return url

def create_travel_calendar_event(event):
	calendar_service = build_calendar_service()

	calendar_event = {
		"summary": event["title"],
		"description": "#ignore\n\n" + event["description"],  # Already includes the maps link
		"location": event["location"],
		"start": {
			"dateTime": event["start_time"].isoformat(),
			"timeZone": "Europe/Berlin",
		},
		"end": {"dateTime": event["end_time"].isoformat(), "timeZone": "Europe/Berlin"},
		"source": {
			"title": "Google Maps directions",
			"url": event["maps_url"],
		},
	}

	event = calendar_service.events().insert(calendarId="primary", body=calendar_event).execute()
	logger.info("Event created: %s" % (event.get("htmlLink")))


def process_calendar_events_with_travel(with_locations) -> list:
	"""
	Process calendar events and create travel events for each

	Args:
		with_locations (list): List of calendar events with location information

	Returns:
		list: List of created travel events
	"""
	created_events = []
	for calendar_event in with_locations:
		if calendar_event.get("location"):
			description = calendar_event.get("description", "")

			# Determine travel type from tags in description
			travel_type = _extract_travel_type_from_description(description)

			if travel_type:
				# Create single specific travel event
				travel_event = _create_single_travel_event(
					calendar_event=calendar_event,
					travel_type=travel_type
				)

				if travel_event:
					create_travel_calendar_event(travel_event)
					created_events.append(travel_event)
			else:
				# No specific travel type found, create all three
				travel_events = _create_all_travel_events(calendar_event)
				for travel_event in travel_events:
					if travel_event:
						create_travel_calendar_event(travel_event)
						created_events.append(travel_event)

	return created_events


def _extract_travel_type_from_description(description: str) -> str | None:
	"""
	Extract travel type from event description tags

	Args:
		description (str): Event description text

	Returns:
		str | None: Travel type (walking, driving, bicycling) or None if not specified
	"""
	description_lower = description.lower()

	if any(tag in description_lower for tag in ["#walk", "#walking"]):
		return "walking"
	elif any(tag in description_lower for tag in ["#car", "#drive", "#driving"]):
		return "driving"
	elif any(tag in description_lower for tag in ["#bike", "#bicycle", "#bicycling", "#cycling"]):
		return "bicycling"
	else:
		# Return None if no specific tag is found - will create all three types
		return None


def _create_single_travel_event(calendar_event: dict, travel_type: str) -> dict | None:
	"""
	Create a single travel event for the specified travel type

	Args:
		calendar_event (dict): The calendar event with location
		travel_type (str): Type of travel (walking, driving, bicycling)

	Returns:
		dict | None: Formatted travel event or None if creation failed
	"""
	try:
		# Get travel information for the specific mode
		travel_info = get_travel_start_time(
			destination=calendar_event["location"],
			event_start_time=parser.parse(calendar_event["start"]["dateTime"]),
			origin=HOME_ADDRESS,
			buffer_minutes=5,  # Default buffer
			mode=travel_type,
			traffic_model="pessimistic" if travel_type == "driving" else None,
		)

		# Format the travel event details
		return format_travel_event_details(travel_info)

	except Exception as e:
		logger.error(f"Failed to create travel event: {e}")
		return None


def _create_all_travel_events(calendar_event: dict) -> list:
	"""
	Create all three travel events (walking, driving, bicycling) for a calendar event

	Args:
		calendar_event (dict): The calendar event with location

	Returns:
		list: List of formatted travel events
	"""
	travel_modes = ["walking", "driving", "bicycling"]
	travel_events = []

	for mode in travel_modes:
		travel_event = _create_single_travel_event(calendar_event, mode)
		if travel_event:
			travel_events.append(travel_event)

	return travel_events
def create_travel_events_for_upcoming_calendar_events(days=1) -> list:
	calendar_service = build_calendar_service()
	calendar_dict = get_dict(calendar_service)

	event_list = []
	event_list.extend(get_events_from_calendar_for_days("Janik's Kalender", calendar_dict, calendar_service, days))
	with_locations = [x for x in event_list if "location" in x and x["location"]]

	return process_calendar_events_with_travel(with_locations)
