import os 
import sys
import hashlib
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from storm_silver_party_reader import read_party, export_party
from storm_silver_box_reader import read_boxes, print_boxes, export_boxes
from changes import compute_changes, record_changes

'''if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "save.sav"
    
    party = read_party(path)
    boxes = read_boxes(path)
    
    #print_party(party)
    export_party(party)
    
    print_boxes(boxes)
    export_boxes(boxes)'''

DATABASE_URL = os.getenv("DATABASE_URL")
GAME_SAV = os.getenv("SAV")
RUN_ID = 1  # set once when you create_run(), then hardcode it here

engine = create_engine(DATABASE_URL)

def create_run(engine, game_name, sav_filename):
    with engine.connect() as conn:
        result = conn.execute(
            text("INSERT INTO runs (game, sav_filename, is_active) "
                 "VALUES (:game, :sav, now(), true) RETURNING run_id"),
            {"game": game_name, "sav": sav_filename}
        )
        conn.commit()
        return result.scalar()

def get_sav_hash(sav_path):
    with open(sav_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def already_processed(engine, run_id, sav_hash):
    with engine.connect() as conn:
        last = conn.execute(
            text("SELECT sav_file_hash FROM game_session WHERE run_id = :run_id "
                 "ORDER BY updated_at DESC LIMIT 1"),
            {"run_id": run_id}
        ).scalar()
    return last == sav_hash

def create_session(engine, run_id, sav_hash):
    with engine.connect() as conn:
        result = conn.execute(
            text("INSERT INTO game_session (run_id, sav_file_hash, updated_at) "
                 "VALUES (:run_id, :hash, now()) RETURNING session_id"),
            {"run_id": run_id, "hash": sav_hash}
        )
        conn.commit()
        return result.scalar()

def get_or_create_pokemon_id(engine, run_id, pv):
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT pokemon_id FROM pokemon_identity "
                 "WHERE run_id = :run_id AND personality_value = :pv"),
            {"run_id": run_id, "pv": pv}
        ).scalar()
        if existing:
            return existing
        result = conn.execute(
            text("INSERT INTO pokemon_identity (run_id, personality_value) "
                 "VALUES (:run_id, :pv) RETURNING pokemon_id"),
            {"run_id": run_id, "pv": pv}
        )
        conn.commit()
        return result.scalar()

def build_party_df(party, session_id, engine, run_id):
    rows = []
    for mon in party:
        pokemon_id = get_or_create_pokemon_id(engine, run_id, mon['personality_value'])
        moves = mon['moves'] + [None] * (4 - len(mon['moves']))  # pad to 4
        rows.append({
            'session_id':   session_id,
            'pokemon_id':   pokemon_id,
            'species':      mon['species'],
            'type1': mon['type1'],
            'type2': mon['type2'],
            'exp_level':    mon['exp_level'],
            'nature':       mon['nature'],
            'ability':      mon['ability'],
            'held_item':    mon['held_item'],
            'location_met': mon['location_met'],
            'move1':        moves[0],
            'move2':        moves[1],
            'move3':        moves[2],
            'move4':        moves[3],
            'ev_hp':        mon['ev_hp'],
            'ev_atk':       mon['ev_atk'],
            'ev_def':       mon['ev_def'],
            'ev_spe':       mon['ev_spe'],
            'ev_spa':       mon['ev_spa'],
            'ev_spd':       mon['ev_spd'],
            'iv_hp':        mon['iv_hp'],
            'iv_atk':       mon['iv_atk'],
            'iv_def':       mon['iv_def'],
            'iv_spe':       mon['iv_spe'],
            'iv_spa':       mon['iv_spa'],
            'iv_spd':       mon['iv_spd'],
            'personality_value': mon['personality_value'],
            'growth_rate':  mon['growth_rate'],
        })
    return pd.DataFrame(rows)

def build_box_df(boxes, session_id, engine, run_id):
    rows = []
    for box_num, box in enumerate(boxes, start=1):
        for slot_num, mon in enumerate(box, start=1):
            if mon is None or mon['is_egg']:
                continue
            pokemon_id = get_or_create_pokemon_id(engine, run_id, mon['personality_value'])
            moves = mon['moves'] + [None] * (4 - len(mon['moves']))  # pad to 4
            rows.append({
                'session_id':   session_id,
                'pokemon_id':   pokemon_id,
                'species':      mon['species'],
                'type1': mon['type1'],
                'type2': mon['type2'],
                'exp_level':    mon['exp_level'],
                'nature':       mon['nature'],
                'ability':      mon['ability'],
                'held_item':    mon['held_item'],
                'location_met': mon['location_met'],
                'move1':        moves[0],
                'move2':        moves[1],
                'move3':        moves[2],
                'move4':        moves[3],
                'ev_hp':        mon['ev_hp'],
                'ev_atk':       mon['ev_atk'],
                'ev_def':       mon['ev_def'],
                'ev_spe':       mon['ev_spe'],
                'ev_spa':       mon['ev_spa'],
                'ev_spd':       mon['ev_spd'],
                'iv_hp':        mon['iv_hp'],
                'iv_atk':       mon['iv_atk'],
                'iv_def':       mon['iv_def'],
                'iv_spe':       mon['iv_spe'],
                'iv_spa':       mon['iv_spa'],
                'iv_spd':       mon['iv_spd'],
                'personality_value': mon['personality_value'],
                'growth_rate':  mon['growth_rate'],
                #'box':          box_num,
                #'slot':         slot_num,
                
            })
    return pd.DataFrame(rows)

def write_to_db(df, table_name, engine):
    df.to_sql(table_name, engine, if_exists='append', index=False)


def run_pipeline(sav_path):
    sav_hash = get_sav_hash(sav_path)
    
    if already_processed(engine, RUN_ID, sav_hash):
        print("No changes detected, skipping.")
        return

    session_id = create_session(engine, RUN_ID, sav_hash)
    print(f"Created session {session_id}")

    party = read_party(sav_path)
    boxes = read_boxes(sav_path)

    party_df = build_party_df(party, session_id, engine, RUN_ID)
    box_df = build_box_df(boxes, session_id, engine, RUN_ID)

    write_to_db(party_df, 'party_snapshot', engine)
    print(f"Wrote {len(party_df)} party rows to database")

    write_to_db(box_df, 'box_snapshot', engine)
    print(f"Wrote {len(box_df)} box rows to database")

    changes = compute_changes(engine, RUN_ID, session_id)
    for c in changes:
        print(c)
    record_changes(engine, session_id, changes)

if __name__ == "__main__":
    run_pipeline(GAME_SAV)