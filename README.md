# NuzlockeStatTrack

A data pipeline for tracking Pokémon save data during Nuzlocke runs. Parses binary `.sav` / `.dsv` files from Delta Emulator, stores team snapshots in a PostgreSQL database, tracks stat and move changes across sessions, and provides a .txt with all up-to-date Pokémon ready for easy export to a damage calculator.

On Delta Emulator with Dropbox sync enabled, your save file syncs automatically every time you pause via the menu button.

```
.sav file → parser → Python dicts → Pandas DataFrame → PostgreSQL database
                                  ↘ Showdown format .txt file
```

1. Detect save file changes via the Dropbox API
2. Parse the `.sav` file — record all party and box Pokémon data
   - 3a. Export to Showdown Damage Calculator format (master sheet)
   - 3b. Push data into a Pandas DataFrame
3. Update the PostgreSQL database with snapshots and a change log

> **Note:** Requires Dropbox sync on Delta Emulator. Google Drive does not allow access to raw `.sav` files.

---

## Features

- **Binary save file parsing** — reads raw Gen IV NDS `.sav` / `.dsv` files, extracting IVs, EVs, moves, nature, ability, held item, location met, and level
- **Dropbox auto-sync** — polls your remote save every 5 seconds and triggers the pipeline automatically on change
- **Session-based change tracking** — diffs consecutive saves to log level ups, move changes, evolutions, and party joins/leaves
- **PostgreSQL persistence** — full session history with party/box snapshots and a detailed change log
- **Showdown export** — resulting all_pokemon.txt provides easy place to export party/box pokemon onto Showdown Damage Calculator

---

## Project Structure

```
NuzlockeStatTrack/
├── pipeline/
│   ├── pipeline.py                  # Main orchestration: parse → DataFrame → DB → change log
│   ├── storm_silver_party_reader.py # Party parser for Storm Silver (HGSS-based)
│   ├── storm_silver_box_reader.py   # Box parser for Storm Silver
│   ├── reader_utils.py              # Shared utilities: exp-to-level, growth rate lookup
│   ├── changes.py                   # Session diff logic: detects what changed between saves
│   ├── observer.py                  # Dropbox polling daemon
│   └── db_refresh.py                # Dropbox OAuth token helper
│
├── resources/
│   ├── species.txt                  # Pokémon names indexed by dex number
│   ├── types_by_species.csv         # Type and growth rate lookup per species
│   ├── abilities.txt                # Ability names indexed by ability ID
│   ├── moves.txt                    # Move names indexed by move ID
│   ├── items.txt                    # Item names indexed by item ID
│   ├── locations.txt                # Location names indexed by location ID
│   └── species_abilities.csv        # Species-to-ability mapping
│
├── assets/
│   └── sprites/                     # Local Pokémon sprite PNGs (lowercase, e.g. charizard.png)
│
├── showdown/                        # Output directory for Showdown-format text exports
├── schema.sql                       # PostgreSQL schema
├── setup.py                         # Bootstrap script for initialising a new run in the DB
└── requirements.txt
```

---

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL
- Dropbox account with Delta Emulator save sync enabled
- Delta Emulator on iOS

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-username/NuzlockeStatTrack.git
cd NuzlockeStatTrack
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create the database

```bash
psql -d your_database_name -f schema.sql
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
# Path to your local save file
SAV=path/to/your/save.dsv

# PostgreSQL connection string
DATABASE_URL=postgresql://user:password@localhost:0000/your_database_name

# Dropbox API credentials (https://www.dropbox.com/developers)
DROPBOX_APP_KEY=your_app_key
DROPBOX_APP_SECRET=your_app_secret
DROPBOX_REFRESH_TOKEN=your_refresh_token

# Dropbox path to your Delta save file
DROPBOX_PATH=/path/to/save/on/dropbox.dsv

# Run ID — set this after running setup.py
RUN_ID=1
```

To generate your Dropbox refresh token:

```bash
python pipeline/db_refresh.py
```

### 4. Initialise a new Nuzlocke run

```bash
python setup.py
```

This inserts a row into the `runs` table and prints the `RUN_ID` to add to your `.env`.

---

## Usage

### Auto-pipeline via Dropbox observer

Watches your Dropbox save file and runs the full pipeline automatically on every change:

```bash
python pipeline/observer.py
```

### Run the pipeline manually

Parses the save at `SAV` and updates the database:

```bash
python pipeline/pipeline.py
```

---

## Database Schema

| Table              | Description                                                                      |
| ------------------ | -------------------------------------------------------------------------------- |
| `runs`             | One row per playthrough. Tracks game name, save filename, and active status.     |
| `pokemon_identity` | Unique record per individual Pokémon, identified by `personality_value`.         |
| `game_session`     | One row per save file update. Records save hash and timestamp.                   |
| `party_snapshot`   | Full party state at each session — all stats, moves, EVs, IVs.                   |
| `box_snapshot`     | Full box state at each session.                                                  |
| `change_log`       | Diffs between sessions: level ups, move changes, evolutions, party joins/leaves. |

---

## Supported Games

| Game                             | Readers                                                      |
| -------------------------------- | ------------------------------------------------------------ |
| Pokémon Storm Silver (HGSS hack) | `storm_silver_party_reader.py`, `storm_silver_box_reader.py` |

---

## Dependencies

| Package                          | Purpose                               |
| -------------------------------- | ------------------------------------- |
| `pandas`                         | DataFrame operations and CSV lookups  |
| `SQLAlchemy` + `psycopg2-binary` | PostgreSQL ORM and driver             |
| `dropbox`                        | Dropbox API client for save file sync |
| `python-dotenv`                  | `.env` file loading                   |
