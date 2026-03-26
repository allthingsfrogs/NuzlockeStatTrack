-- NuzlockeStatTrack Schema
-- Run with: psql -d nuzlockestattrack -f schema.sql

-- ── Runs 
-- One row per playthrough / .sav file
CREATE TABLE IF NOT EXISTS runs (
    run_id          SERIAL PRIMARY KEY,
    game            VARCHAR(50)  NOT NULL,  -- e.g. 'Storm Silver'
    sav_filename    VARCHAR(255) NOT NULL,  -- e.g. 'storm_silver.sav'
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    ended_at        TIMESTAMP,              -- NULL if run is still active
    notes           TEXT                    -- GOATED FUTURE FEATURE: NOTES FOR MONS HIGHLIGHTS/MOMENTS
);

CREATE TABLE IF NOT EXISTS pokemon_identity (
    pokemon_id      SERIAL PRIMARY KEY,
    dex_number      INT,
    run_id          INT                 NOT NULL REFERENCES runs(run_id),     
    personality_value BIGINT            NOT NULL, -- hex PV, never changes for a given Pokemon
    location_met    VARCHAR(50),
    UNIQUE (personality_value, run_id)     
);

CREATE TABLE IF NOT EXISTS game_session (
    session_id      SERIAL PRIMARY KEY,
    run_id          INT                 NOT NULL REFERENCES runs(run_id),
    sav_file_hash   VARCHAR(64),
    -- created_at      TIMESTAMP           NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP           NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS party_snapshot (
    snapshot_id     SERIAL PRIMARY KEY,
    session_id      INT          NOT NULL REFERENCES game_session(session_id),
    pokemon_id      INT          NOT NULL REFERENCES pokemon_identity(pokemon_id),
    species         VARCHAR(50)  NOT NULL,
    type1           VARCHAR(25)  NOT NULL,
    type2           VARCHAR(25),
    nickname        VARCHAR(20),
    exp_level       SMALLINT     NOT NULL DEFAULT 1,
    held_item       VARCHAR(50),
    location_met    VARCHAR(50),
    ability         VARCHAR(50),
    nature          VARCHAR(20),
    personality_value BIGINT     NOT NULL,
    growth_rate     VARCHAR(25)  NOT NULL,
    is_egg          BOOLEAN      NOT NULL DEFAULT FALSE,
    -- EVs
    ev_hp           SMALLINT     NOT NULL DEFAULT 0,
    ev_atk          SMALLINT     NOT NULL DEFAULT 0,
    ev_def          SMALLINT     NOT NULL DEFAULT 0,
    ev_spd          SMALLINT     NOT NULL DEFAULT 0,
    ev_spa          SMALLINT     NOT NULL DEFAULT 0,
    ev_spe          SMALLINT     NOT NULL DEFAULT 0,
    ev_total        SMALLINT     GENERATED ALWAYS AS (ev_hp + ev_atk + ev_def + ev_spd + ev_spa + ev_spe) STORED,
    -- IVs
    iv_hp           SMALLINT     NOT NULL DEFAULT 0,
    iv_atk          SMALLINT     NOT NULL DEFAULT 0,
    iv_def          SMALLINT     NOT NULL DEFAULT 0,
    iv_spd          SMALLINT     NOT NULL DEFAULT 0,
    iv_spa          SMALLINT     NOT NULL DEFAULT 0,
    iv_spe          SMALLINT     NOT NULL DEFAULT 0,
    iv_total        SMALLINT     GENERATED ALWAYS AS (iv_hp + iv_atk + iv_def + iv_spd + iv_spa + iv_spe) STORED,
    -- Moves
    move1           VARCHAR(50),
    move2           VARCHAR(50),
    move3           VARCHAR(50),
    move4           VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS box_snapshot (
    snapshot_id     SERIAL PRIMARY KEY,
    session_id      INT          NOT NULL REFERENCES game_session(session_id),
    pokemon_id      INT          NOT NULL REFERENCES pokemon_identity(pokemon_id),
    species         VARCHAR(50)  NOT NULL,
    type1    VARCHAR(25) NOT NULL,
    type2    VARCHAR(25),
    nickname        VARCHAR(20),
    exp_level       SMALLINT     NOT NULL DEFAULT 1,
    held_item       VARCHAR(50),
    location_met    VARCHAR(50),
    ability         VARCHAR(50),
    nature          VARCHAR(20),
    growth_rate     VARCHAR(25) NOT NULL,
    is_egg          BOOLEAN      NOT NULL DEFAULT FALSE,
    personality_value BIGINT     NOT NULL,
    -- EVs
    ev_hp           SMALLINT     NOT NULL DEFAULT 0,
    ev_atk          SMALLINT     NOT NULL DEFAULT 0,
    ev_def          SMALLINT     NOT NULL DEFAULT 0,
    ev_spd          SMALLINT     NOT NULL DEFAULT 0,
    ev_spa          SMALLINT     NOT NULL DEFAULT 0,
    ev_spe          SMALLINT     NOT NULL DEFAULT 0,
    ev_total        SMALLINT     GENERATED ALWAYS AS (ev_hp + ev_atk + ev_def + ev_spd + ev_spa + ev_spe) STORED,
    -- IVs
    iv_hp           SMALLINT     NOT NULL DEFAULT 0,
    iv_atk          SMALLINT     NOT NULL DEFAULT 0,
    iv_def          SMALLINT     NOT NULL DEFAULT 0,
    iv_spd          SMALLINT     NOT NULL DEFAULT 0,
    iv_spa          SMALLINT     NOT NULL DEFAULT 0,
    iv_spe          SMALLINT     NOT NULL DEFAULT 0,
    iv_total        SMALLINT     GENERATED ALWAYS AS (iv_hp + iv_atk + iv_def + iv_spd + iv_spa + iv_spe) STORED,
    -- Moves
    move1           VARCHAR(50),
    move2           VARCHAR(50),
    move3           VARCHAR(50),
    move4           VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS change_log (
    change_id    SERIAL PRIMARY KEY,
    session_id   INT REFERENCES game_session(session_id),
    pokemon_id   INT REFERENCES pokemon_identity(pokemon_id),
    change_type  TEXT,  -- 'level', 'move', 'evolution', 'party_join', 'party_leave'
    field        TEXT,  -- which field changed, e.g. 'move3', 'ev_atk'
    old_value    TEXT,
    new_value    TEXT,
    recorded_at  TIMESTAMPTZ DEFAULT now()
);