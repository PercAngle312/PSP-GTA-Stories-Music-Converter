GTA Stories Music Converter
===========================
Turns your MP3 (also WAV/FLAC/OGG) files into .gta files for GTA Liberty City Stories
and Vice City Stories on the PSP.

1. Add your songs.
2. Pick an output folder, or your PSP Memory Stick and the game.
3. Press Convert.

Put the .gta files in:  PSP\SAVEDATA\<GAMEID>CUSTOMTRACKS\  on the Memory Stick
  Liberty City Stories (US): ULUS10041CUSTOMTRACKS
  Vice City Stories (US):    ULUS10160CUSTOMTRACKS (check against your save folder's ID)
The game needs an existing save. Then: Pause > Audio > My Songs ON, get in a vehicle,
D-pad left/right changes track.

Output is ATRAC3 at 66 kbps renamed to .gta. Each file must be under 120 minutes.
Uses the open-source atracdenc encoder (LGPL): https://github.com/dcherednik/atracdenc
