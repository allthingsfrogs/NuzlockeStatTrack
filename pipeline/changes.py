import os
import math
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()
RUN_ID = int(os.getenv("RUN_ID"))

def compute_changes(engine, run_id, session_id, table='party_snapshot'):
    df = pd.read_sql(text(f"""
        SELECT 
            ps.pokemon_id,
            ps.species,
            ps.exp_level,
            ps.ev_hp, ps.ev_atk, ps.ev_def, ps.ev_spe, ps.ev_spa, ps.ev_spd,
            ps.move1, ps.move2, ps.move3, ps.move4,
            ps.type1, ps.type2,
            s.session_id
        FROM {table} ps
        JOIN game_session s USING (session_id)
        WHERE s.run_id = :run_id
        AND s.session_id IN (
            SELECT session_id FROM game_session
            WHERE run_id = :run_id
            ORDER BY updated_at DESC
            LIMIT 2
        )
    """), engine, params={"run_id": run_id})

    sessions = sorted(df['session_id'].unique())
    if len(sessions) < 2:
        print(f"No previous session to compare against for {table}.")
        return []

    prev = df[df['session_id'] == sessions[0]].set_index('pokemon_id')
    curr = df[df['session_id'] == sessions[1]].set_index('pokemon_id')

    tracked = [
        'species', 'exp_level',
        'ev_hp', 'ev_atk', 'ev_def', 'ev_spe', 'ev_spa', 'ev_spd',
        'move1', 'move2', 'move3', 'move4',
        'type1', 'type2'
    ]

    # box pokemon have no level, skip it for box_snapshot
    if table == 'box_snapshot':
        tracked = [f for f in tracked if f != 'exp_level']

    changes = []

    for pokemon_id in curr.index:
        if pokemon_id not in prev.index:
            changes.append({
                'pokemon_id':  pokemon_id,
                'change_type': 'party_join' if table == 'party_snapshot' else 'box_join',
                'field':       None,
                'old_value':   None,
                'new_value':   curr.loc[pokemon_id, 'species']
            })
            continue

        for field in tracked:
            old = prev.loc[pokemon_id, field]
            new = curr.loc[pokemon_id, field]

            # treat nan and None as equal so null type2 doesn't trigger false changes
            old_is_null = old is None or (isinstance(old, float) and math.isnan(old))
            new_is_null = new is None or (isinstance(new, float) and math.isnan(new))

            if old_is_null and new_is_null:
                continue  # both null, no change

            if old != new:
                change_type = (
                    'level'     if field == 'exp_level' else
                    'move'      if 'move' in field else
                    'evolution' if field in ('species', 'type1', 'type2') else
                    'ev'
                )
                changes.append({
                    'pokemon_id':  pokemon_id,
                    'change_type': change_type,
                    'field':       field,
                    'old_value':   str(old),
                    'new_value':   str(new)
                })

    for pokemon_id in prev.index:
        if pokemon_id not in curr.index:
            changes.append({
                'pokemon_id':  pokemon_id,
                'change_type': 'party_leave' if table == 'party_snapshot' else 'box_leave',
                'field':       None,
                'old_value':   prev.loc[pokemon_id, 'species'],
                'new_value':   None
            })

    return changes


def record_changes(engine, session_id, changes):
    if not changes:
        print("No changes to record.")
        return

    rows = [{
        'session_id':  session_id,
        'pokemon_id':  c['pokemon_id'],
        'change_type': c['change_type'],
        'field':       c['field'],
        'old_value':   c['old_value'],
        'new_value':   c['new_value']
    } for c in changes]

    pd.DataFrame(rows).to_sql('change_log', engine, if_exists='append', index=False)
    print(f"Recorded {len(rows)} changes to change_log")
