import sqlite3

import pandas as pd


def get_koreader_book():
    sqlite_conn = sqlite3.connect("statistics.sqlite3")
    return pd.read_sql_query("SELECT * FROM book", sqlite_conn)

def get_koreader_page_stat():
    sqlite_conn = sqlite3.connect("statistics.sqlite3")
    return pd.read_sql_query("SELECT * FROM page_stat", sqlite_conn)