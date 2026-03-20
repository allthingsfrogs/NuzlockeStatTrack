# NuzlockeStatTrack

A data pipeline which takes Pokemon save data from Delta Emulator and outputs your caught Pokemon's stats, moves, and nature in a format useable in the Showdown Damage Calculator. Updates automatically as you progress through a game and gives a master sheet of all your Pokemon, which makes damage calculations and boss fight preparations less tedious.

On Delta emulator with DropBox sync enabled, your save file should sync with the latest game data everytime you pause the game via the menu button.

A high level overview of this pipeline:

.sav file → parser → raw Python dicts → Pandas DataFrame → Postgresql database
↘ Showdown format .txt file

1. Detect if a change occurred in your save data from DropBox via the DropBox API
2. Parse .sav file, record all party Pokemon and box Pokemon data
   3a. Export Pokemon data into a showdown damage calc format in a compiled master sheet for quickly importing the Pokemon data into damage calculators
   3b. Pass Pokemon data into a Pandas DataFrame
3. Update and maintain a database recording all changes in Nuzlocke runs so far.

Must be used with the DropBox sync feature on Delta Emulator. Google Drive is an option for syncing and saving game data on the cloud, but it doesn't let you view or manipulate your uploaded .sav files.
