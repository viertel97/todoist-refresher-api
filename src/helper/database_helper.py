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


def close_server_connection(connection, alchemy=False):
	if alchemy:
		connection.dispose()
	else:
		connection.close()
