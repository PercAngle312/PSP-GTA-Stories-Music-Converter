# GTA Stories Music Converter

Convert your own music (MP3, WAV, FLAC, OGG) into `.gta` custom-track files for
**Grand Theft Auto: Vice City Stories** and **Liberty City Stories** on the PSP, on a modern
Windows PC. No CD, no PSP connection and no Windows XP needed.

Rockstar's original *Custom Tracks* tool only runs on old Windows, needs an audio CD and only
works while it can detect a connected PSP. This tool does the same conversion directly from files.

> Unofficial fan project. Not affiliated with or endorsed by Rockstar Games, Take-Two, Sony
> or the authors of Exact Audio Copy. Only convert music you have the right to use.

## Status

- Files with this header were confirmed playing in-game in **Vice City Stories (US)** on real PSP hardware. The current release build reproduces that header byte for byte (checked against the files that played).
- Liberty City Stories uses the same mechanism and has been reported to work by other users,
  but I have not tested it myself.
- Output is checked against a real `.gta` file: same container, same header values.

## Download

Get the installer or the portable exe from the
[Releases](../../releases) page. Both are 32-bit Windows programs and need nothing else installed.
Windows SmartScreen may warn about an unknown publisher because the files are not code-signed.

## Use

1. Add songs (files or a whole folder).
2. Choose an output folder, or your PSP Memory Stick plus the game.
3. Press **Convert**.

If you copy the files yourself, put the `.gta` files in
`PSP/SAVEDATA/<GAME ID>CUSTOMTRACKS/` on the Memory Stick.

| Game | Folder |
|---|---|
| Liberty City Stories (US) | `ULUS10041CUSTOMTRACKS` |
| Vice City Stories (US) | `ULUS10160CUSTOMTRACKS` |
| Liberty City Stories (EU) | `ULES00182CUSTOMTRACKS` |
| Vice City Stories (EU) | `ULES00503CUSTOMTRACKS` |

The ID is the first nine characters of your game's save folder (for example `ULUS10160S92F0`
becomes `ULUS10160`). The game needs an existing save. In game: **Pause > Audio > Custom Tracks /
My Songs ON**, then get in a vehicle; D-pad left/right changes track.
The EU IDs come from community guides and have not been tested here.

## Command line

```
python src/mp3_to_gta.py song1.mp3 song2.mp3 "C:\Music\Folder" --out gta_output
python src/mp3_to_gta.py "C:\Music\Folder" --psp E: --game ULUS10160
```

Run from source: `pip install -r requirements.txt`, put `atracdenc.exe` next to the scripts
(download it from Releases, or see [docs/BUILD.md](docs/BUILD.md)), then `python src/gta_music_gui.py`.

## How it works

Each song is decoded to 44.1 kHz 16-bit stereo, encoded to ATRAC3 at 66 kbps with
[atracdenc](https://github.com/dcherednik/atracdenc), given a RIFF header matching Sony's
`at3tool` output, and saved with a `.gta` extension. Details, including the header detail that
makes the game play the files, are in [docs/FORMAT.md](docs/FORMAT.md).

Limits: each file must be under 120 minutes (PSP playback limit).

## Known issues / help wanted

- Testing on Liberty City Stories and on EU copies.
- A 64-bit or signed build, and a CI workflow for reproducible releases.

## License

MIT for this project's code (see [LICENSE](LICENSE)). Bundled third-party components are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md); the ATRAC3 encoder is LGPL-2.1.
