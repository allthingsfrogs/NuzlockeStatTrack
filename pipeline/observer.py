import dropbox
import time
from dotenv import load_dotenv
import os 
from dropbox import DropboxOAuth2FlowNoRedirect
from pipeline.storm_silver_party_reader import export_party

load_dotenv()

TOKEN = os.getenv("REFRESH")
A_K = os.getenv("A_K")
A_S = os.getenv("A_S")

dbx = dropbox.Dropbox(
    oauth2_refresh_token=TOKEN,
    app_key=A_K,
    app_secret=A_S
)

DB_PATH = os.getenv("DB_PATH")
LOCAL_PATH = os.getenv("LOCAL")

# get initial state
metadata = dbx.files_get_metadata(DB_PATH)
last_hash = metadata.content_hash

 # poll every 5 seconds
while True:
    time.sleep(5)

    metadata = dbx.files_get_metadata(DB_PATH)

    if metadata.content_hash != last_hash:
        print("Game Updated, downloading. . .")
        _, response = dbx.files_download(DB_PATH)

        with open(LOCAL_PATH, "wb") as f:
            f.write(response.content)

        #export_party(LOCAL_PATH)

        last_hash = metadata.content_hash
        print(f"Downloadednew version (rev: {metadata.rev})")

    else:
        print("Polling...")
