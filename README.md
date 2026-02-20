# NuzlockeStatTrack

A data pipeline which takes Pokemon save data from Delta Emulator and outputs your caught Pokemon's stats, moves, and nature in a format useable in the Showdown Damage Calculator. Updates automatically as you progress through a game and gives a master sheet of all your Pokemon, which makes damage calculations and boss fight preparations less tedious.

How it (should) work:

On Delta emulator with DropBox sync enabled, your save file should sync with the latest game data everytime you pause the game via the menu button.

A high level overview of this pipeline:

1. Detect if a change occurred in your save data from DropBox via the DropBox API
2. Use PKHex to extract the latest level, stats, move, and nature data from the pokemon in your party and in your box
3. transform this data into a showdown damage calc format amd compile into a master sheet for quickly importing the data into damage calculators
4. produce a summary of the changes which occured since the last game update

For now, this will work only for Delta Emulator, and only using the sync feature with DropBox. Google Drive is an option for syncing and saving game data on the cloud, but it doesn't let you view or manipulate your uploaded .sav files.
