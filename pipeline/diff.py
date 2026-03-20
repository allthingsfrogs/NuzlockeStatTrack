import os 
import sys
import hashlib
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from pipeline.storm_silver_party_reader import read_party, export_party
from pipeline.storm_silver_box_reader import read_boxes, print_boxes, export_boxes

load_dotenv()
RUN_ID = int(os.getenv("RUN_ID"))

def compute_diff(engine, RUN_ID):
    df = pd.read_sql("""
        SELECT 
            ps.pokemon_id,
            ps.species,
            ps.level,
            ps.ev_hp, ps.ev_atk, ps.ev_def, ps.ev_spe, ps.ev_spa, ps.ev_spd,
            ps.move1, ps.move2, ps.move3, ps.move4,
            s.session_id,
            s.parsed_at
        FROM party_snapshot ps
        JOIN game_sessions s USING (session_id)
        WHERE s.run_id = :run_id
        AND s.session_id IN (
            SELECT session_id FROM game_session 
            WHERE run_id = :run_id 
            ORDER BY updated_at DESC 
            LIMIT 2
        )
    """, engine, params={"run_id": RUN_ID})

    sessions = sorted(df['session_id'].unique())
    if len(sessions) < 2:
        print("No previous session to compare against.")
        return

    prev = df[df['session_id'] == sessions[0]].set_index('pokemon_id')
    curr = df[df['session_id'] == sessions[1]].set_index('pokemon_id')
    tracked = ['level', 'ev_hp', 'ev_atk', 'ev_def', 'ev_spe', 'ev_spa', 'ev_spd',
               'move1', 'move2', 'move3', 'move4']
    
    changes = []
    for pokemon_id in curr.index:
        if pokemon_id not in prev.index:
            changes.append(f"NEW: {curr.loc[pokemon_id, 'species']} joined the party")
            continue
        for field in tracked:
            old = prev.loc[pokemon_id, field]
            new = curr.loc[pokemon_id, field]
            if old != new:
                species = curr.loc[pokemon_id, 'species']
                changes.append(f"{species}: {field} {old} → {new}")
    
    # Pokemon that left the party
    for pokemon_id in prev.index:
        if pokemon_id not in curr.index:
            changes.append(f"GONE: {prev.loc[pokemon_id, 'species']} left the party")
    
    return changes


def record_diff(engine, RUN_ID, session_id):
    # ... same comparison logic as before ...
    df = pd.read_sql("""
        SELECT 
            ps.pokemon_id,
            ps.species,
            ps.level,
            ps.ev_hp, ps.ev_atk, ps.ev_def, ps.ev_spe, ps.ev_spa, ps.ev_spd,
            ps.move1, ps.move2, ps.move3, ps.move4,
            s.session_id,
            s.parsed_at
        FROM party_snapshot ps
        JOIN sessions s USING (session_id)
        WHERE s.run_id = :run_id
        AND s.session_id IN (
            SELECT session_id FROM sessions 
            WHERE run_id = :run_id 
            ORDER BY parsed_at DESC 
            LIMIT 2
        )
    """, engine, params={"run_id": RUN_ID})

    sessions = sorted(df['session_id'].unique())
    if len(sessions) < 2:
        print("No previous session to compare against.")
        return

    prev = df[df['session_id'] == sessions[0]].set_index('pokemon_id')
    curr = df[df['session_id'] == sessions[1]].set_index('pokemon_id')
    tracked = ['level', 'ev_hp', 'ev_atk', 'ev_def', 'ev_spe', 'ev_spa', 'ev_spd',
               'move1', 'move2', 'move3', 'move4']
    
    rows = []
    for pokemon_id in curr.index:
        for field in tracked:
            old = prev.loc[pokemon_id, field]
            new = curr.loc[pokemon_id, field]
            if old != new:
                rows.append({
                    'session_id': session_id,
                    'pokemon_id': pokemon_id,
                    'change_type': 'level' if field == 'level' else 'move' if 'move' in field else 'ev',
                    'field': field,
                    'old_value': str(old),
                    'new_value': str(new)
                })
    
    if rows:
        pd.DataFrame(rows).to_sql('change_log', engine, if_exists='append', index=False)