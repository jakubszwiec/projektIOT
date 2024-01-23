import sqlite3
import time
import os


def create_database():
    if os.path.exists("workers.db"):
        os.remove("workers.db")
        print("An old database removed.")
    connection = sqlite3.connect("workers.db")
    cursor = connection.cursor()
    cursor.execute(""" CREATE TABLE workers_log (
        log_time text,
        worker text,
        terminal_id text,
        allowed text
    )""")
    cursor.execute(""" CREATE TABLE workers_allowed (
        worker text
    )""")
    connection.commit()
    connection.close()
    print("The new database created.")


if __name__ == "__main__":
    create_database()