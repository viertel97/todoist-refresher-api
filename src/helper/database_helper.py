import psycopg
import pymysql
from quarter_lib.akeyless import get_target
from sqlalchemy import create_engine

DB_USER_NAME, DB_HOST_NAME, DB_PASSWORD, DB_PORT, DB_NAME = get_target("private")
(
	DB_USER_NAME_MONICA,
	DB_HOST_NAME_MONICA,
	DB_PASSWORD_MONICA,
	DB_PORT_MONICA,
	DB_NAME_MONICA,
) = get_target("monica")

DB_USER_NAME_TANDOOR, DB_HOST_NAME_TANDOOR, DB_PASSWORD_TANDOOR, DB_PORT_TANDOOR, DB_NAME_TANDOOR = get_target("tandoor")


def create_server_connection(target, alchemy=False):
	if target == "private":
		db_user_name = DB_USER_NAME
		db_host_name = DB_HOST_NAME
		db_password = DB_PASSWORD
		db_port = DB_PORT
		db_name = DB_NAME
	elif target == "monica":
		db_user_name = DB_USER_NAME_MONICA
		db_host_name = DB_HOST_NAME_MONICA
		db_password = DB_PASSWORD_MONICA
		db_port = DB_PORT_MONICA
		db_name = DB_NAME_MONICA
	elif target == "tandoor":
		db_user_name = DB_USER_NAME_TANDOOR
		db_host_name = DB_HOST_NAME_TANDOOR
		db_password = DB_PASSWORD_TANDOOR
		db_port = DB_PORT_TANDOOR
		db_name = DB_NAME_TANDOOR
	else:
		raise Exception("Unknown target")
	if alchemy:
		return create_engine(f"mysql+pymysql://{db_user_name}:{db_password}@{db_host_name}:{db_port}/{db_name}")

	return pymysql.connect(
		user=db_user_name,
		host=db_host_name,
		password=db_password,
		port=int(db_port),
		database=db_name,
		cursorclass=pymysql.cursors.DictCursor,
	)

def create_postgres_server_connection(target, alchemy=False):
	if target == "tandoor":
		db_user_name = DB_USER_NAME_TANDOOR
		db_host_name = DB_HOST_NAME_TANDOOR
		db_password = DB_PASSWORD_TANDOOR
		db_port = DB_PORT_TANDOOR
		db_name = DB_NAME_TANDOOR
	else:
		raise Exception("Unknown target")
	if alchemy:
		return create_engine(f"postgresql+psycopg2://{db_user_name}:{db_password}@{db_host_name}:{db_port}/{db_name}")

	return psycopg.connect(
		user=db_user_name,
		host=db_host_name,
		password=db_password,
		port=int(db_port),
		dbname=db_name,
	)


def close_server_connection(connection, alchemy=False):
	if alchemy:
		connection.dispose()
	else:
		connection.close()
