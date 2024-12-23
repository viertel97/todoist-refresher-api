import pymysql
from quarter_lib.akeyless import get_target

DB_USER_NAME, DB_HOST_NAME, DB_PASSWORD, DB_PORT, DB_NAME = get_target("private")
(
	DB_USER_NAME_MONICA,
	DB_HOST_NAME_MONICA,
	DB_PASSWORD_MONICA,
	DB_PORT_MONICA,
	DB_NAME_MONICA,
) = get_target("monica")


def create_server_connection(target):
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
	return pymysql.connect(
		user=db_user_name,
		host=db_host_name,
		password=db_password,
		port=int(db_port),
		database=db_name,
		cursorclass=pymysql.cursors.DictCursor,
	)


def close_server_connection(connection):
	connection.close()
