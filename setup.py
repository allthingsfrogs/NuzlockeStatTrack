from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

GAME_SAV = os.getenv("SAV")

engine = create_engine(os.getenv("DATABASE_URL"))

def create_run(engine, game_name, sav_filename):
    with engine.connect() as conn:
        result = conn.execute(
            text("INSERT INTO runs (game, sav_filename, is_active) "
                 "VALUES (:game, :sav, true) RETURNING run_id"),
            {"game": game_name, "sav": sav_filename}
        )
        conn.commit()
        return result.scalar()

def setup_new_run(game_name, sav_filename):
    with engine.connect() as conn:
        conn.execute(text("UPDATE runs SET is_active = false"))
        conn.commit()

    run_id = create_run(engine, game_name, sav_filename)
    print(f"Run created with ID: {run_id}")
    print(f"Add this to your .env file: RUN_ID={run_id}")
    return run_id

if __name__ == "__main__":
    setup_new_run("Storm Silver", GAME_SAV)
