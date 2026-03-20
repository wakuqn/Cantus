import sqlite3

"""Simple script to create the music library database from list.sql."""

def initialize_database(sql_file: str, db_file: str):
    '''Read the SQL schema from `sql_file` and execute it against `db_file`.'''
    with open(sql_file, 'r', encoding='utf-8') as f:
        schema = f.read()

    conn = sqlite3.connect(db_file)
    try:
        cursor = conn.cursor()
        cursor.executescript(schema)
        conn.commit()
        print(f"Database initialized at {db_file}")
    finally:
        conn.close()


if __name__ == '__main__':
    import os
    base = os.path.dirname(__file__)
    sql_path = os.path.join(base, 'list.sql')
    db_path = os.path.join(base, 'cantus.db')
    initialize_database(sql_path, db_path)

