import json
import re
import unicodedata

from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)


def slugify(value, allow_unicode=False):
	value = str(value)
	if allow_unicode:
		value = unicodedata.normalize("NFKC", value)
	else:
		value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
	value = re.sub(r"[^\w\s-]", "", value.lower())
	# add max length which then triggers generate title
	value = re.sub(r"[-\s]+", "-", value).strip("-_")
	if len(value) > 40:
		return value[:40]
	else:
		return value


def generate_front_matter(hierarchy_dict):
	metadata_json = {
		"created": hierarchy_dict["created_at"].strftime("%Y-%m-%dT%H:%M:%S"),
		"slugified_title": slugify(hierarchy_dict["created_at"].strftime("%Y-%m-%dT%H:%M:%S") + "-" + hierarchy_dict["summary"]),
		"content": hierarchy_dict["content"],
		"summary": hierarchy_dict["summary"],
		"description": hierarchy_dict["description"],
		"tags": hierarchy_dict["labels"],
		"people": ["[[Microjournal]]"],
	}

	# Remove keys with None values
	metadata_json = {k: v for k, v in metadata_json.items()}

	return_string = "---\n"
	return_string += json.dumps(metadata_json, indent=4, sort_keys=True, ensure_ascii=False)
	return_string += "\n---\n\n"

	return return_string, metadata_json["slugified_title"]


def create_file_from_dict(hierarchy_dict):
	content, filename = generate_front_matter(hierarchy_dict)

	content += f"# {hierarchy_dict['content']}\n\n{hierarchy_dict['description']}\n\n"

	return {"filename": filename + ".md", "content": content}
