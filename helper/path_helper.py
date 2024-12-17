import re
import unicodedata


def slugify(value):
	value = str(value)
	value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
	value = re.sub(r"[^\w\s-]", "", value)
	return re.sub(r"[-\s]+", "-", value).strip("-_")
