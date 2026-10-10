# Song names in game

The game shows each track by its `.gta` file name, so the converter builds a clean file name for every song.

## Where the name comes from

| Name style | Result |
|---|---|
| **Artist - Title** (default) | Read from the song's tags (MP3 ID3v1/v2.2/v2.3/v2.4, FLAC). Falls back to the title alone, then to the tidied file name. |
| **Title only** | Tag title, else the tidied file name. |
| **Keep file name** | The file name, tidied. |

Files without tags (WAV, OGG, untagged MP3s) use the file name.

## Tidying

- Underscores become spaces; a leading track number (`21_`, `04 - `) is removed.
- Trailing `_44_1k` and 8-character hash tokens (like `F2e4f082`) are removed.
- Bracketed junk such as `(Official Video)`, `[HD]`, `(Lyrics)`, `(Remastered)` is removed.
- Accents are folded to plain letters (`Björk` becomes `Bjork`); other non-ASCII characters are dropped.
- Optional **Fix ALL CAPS / lowercase** title-cases a name only when it is entirely upper or lower case.
- Optional **Number tracks** adds `01 - `, `02 - ` in list order.
- Names longer than the maximum (default 40) are shortened at a word boundary; if "Artist - Title" is too long, the title alone is used.
- Duplicate names get ` 2`, ` 3` appended.

In the GUI you can double-click any row to type a name yourself, and use Up/Down to set the order.

## Why the default is conservative

By default only letters, digits, spaces and hyphens are kept. The option **Keep punctuation** also allows
`' & , . ! ( )`. Those are valid on the PSP's FAT Memory Stick, but how the game's font and name display handle them
(and how long a name it will show) has not been verified on hardware, so it is off by default.
If you test it, please report the result in an issue.

Characters that FAT forbids (`\ / : * ? " < > |`) are never used.

## Command line

```
python src/mp3_to_gta.py "C:\Music" --dry-run                       # preview names only
python src/mp3_to_gta.py "C:\Music" --name-style title --number
python src/mp3_to_gta.py "C:\Music" --keep-punctuation --fix-caps --max-length 32
```
