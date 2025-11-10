import pandas as pd
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

from src.helper.database_helper import close_server_connection, \
	create_postgres_server_connection

BASE_URL = get_secrets(["tandoor/base_url"])

logger = setup_logging(__name__)


def get_recipes_from_db() -> dict:
	connection = create_postgres_server_connection("tandoor")
	df = pd.read_sql_query('''SELECT id, "name" FROM cookbook_recipe''', connection)
	close_server_connection(connection)
	df["link"] = BASE_URL + "/recipe/" + df["id"].astype(str)
	result = df.set_index("id").to_dict(orient="index")
	return result

def get_cook_log_from_db() -> pd.DataFrame:
	connection = create_postgres_server_connection("tandoor")
	df = pd.read_sql_query('''SELECT id, recipe_id, "comment" FROM cookbook_cooklog ORDER BY id desc''', connection)
	close_server_connection(connection)
	return df