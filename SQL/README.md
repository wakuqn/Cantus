# Cantus Music Library

This workspace contains the SQL schema and a helper script to create the database used by the music library application.

## Files

- `list.sql` – contains the SQLite schema for tracks, playlists, history, preferences, and related tables.
- `setup_db.py` – Python script that reads `list.sql` and applies it to an SQLite database (`cantus.db`).
- `index.html` – placeholder for the web interface (not yet implemented).

## Usage

1. Make sure you have Python 3 installed.
2. From the workspace directory, run:
   ```sh
   python setup_db.py
   ```
   This will create `cantus.db` in the same folder with all tables and indexes defined in `list.sql`.
3. Open `cantus.db` with any SQLite client to verify or make changes.

You can extend this project by adding application logic or a frontend that reads/writes from this database.
