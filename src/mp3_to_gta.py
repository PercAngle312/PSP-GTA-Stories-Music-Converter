#!/usr/bin/env python3
"""
MP3 -> .gta converter for GTA Liberty City Stories / Vice City Stories (PSP).

What it does, per file:
  1. Decodes the audio (MP3, WAV, FLAC, OGG) to 44.1 kHz 16-bit stereo.
  2. Encodes it to ATRAC3 at 66 kbps (the "LP4" mode the PSP plays) in a RIFF
     .at3 container using atracdenc (included as atracdenc.exe).
  3. Renames the result to .gta.
  4. Optionally copies the .gta files into the CUSTOMTRACKS folder on your
     PSP Memory Stick.

Usage:
  python mp3_to_gta.py song1.mp3 song2.mp3 folder_of_music
  python mp3_to_gta.py *.mp3 --out C:\\gta_out
  python mp3_to_gta.py *.mp3 --psp E: --game ULUS10041     (US Liberty City Stories)
  python mp3_to_gta.py *.mp3 --psp E: --game ULUS10160     (US Vice City Stories)

Requires:  pip install miniaudio
"""
import argparse
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

import track_names

AUDIO_EXTS = {".mp3", ".wav", ".flac", ".ogg"}
MAX_SECONDS = 120 * 60  # PSP audio playback limit per file


def find_encoder():
    dirs = []
    if getattr(sys, "_MEIPASS", None):  # running as a bundled .exe
        dirs.append(sys._MEIPASS)
    dirs.append(os.path.dirname(os.path.abspath(sys.executable)))
    dirs.append(os.path.dirname(os.path.abspath(__file__)))
    for here in dirs:
        for name in ("atracdenc.exe", "atracdenc"):
            p = os.path.join(here, name)
            if os.path.isfile(p):
                return p
    return shutil.which("atracdenc") or shutil.which("atracdenc.exe")


def decode_to_wav(src, dst_wav):
    """Decode any supported file to 44.1 kHz / 16-bit / stereo WAV. Returns seconds."""
    try:
        import miniaudio
    except ImportError as e:
        sys.exit(f"Audio decoder (miniaudio) could not be loaded: {e}")
    dec = miniaudio.decode_file(
        src,
        output_format=miniaudio.SampleFormat.SIGNED16,
        nchannels=2,
        sample_rate=44100,
    )
    with wave.open(dst_wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(dec.samples.tobytes())
    return len(dec.samples) / 2 / 44100


def fix_header(path):
    """Rewrite the RIFF header the way Sony's at3tool does (needed for GTA LCS/VCS to play it):
    average bytes/sec = 8269 and a fact chunk of frames*1024-1152 samples."""
    d = open(path, "rb").read()
    chunks, i = {}, 12
    while i < len(d) - 8:
        cid, sz = d[i:i + 4], struct.unpack("<I", d[i + 4:i + 8])[0]
        chunks[cid] = d[i + 8:i + 8 + sz]
        i += 8 + sz + (sz & 1)
    fmt, data = bytearray(chunks[b"fmt "]), chunks[b"data"]
    fmt[8:12] = struct.pack("<I", 8269)
    frames = len(data) // 192
    body = (b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + bytes(fmt)
            + b"fact" + struct.pack("<III", 8, max(frames * 1024 - 1152, 0), 1024)
            + b"data" + struct.pack("<I", len(data)) + data)
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", len(body)) + body)


def collect(inputs):
    files = []
    for item in inputs:
        if os.path.isdir(item):
            for n in sorted(os.listdir(item)):
                if os.path.splitext(n)[1].lower() in AUDIO_EXTS:
                    files.append(os.path.join(item, n))
        elif os.path.isfile(item):
            files.append(item)
        else:
            print(f"  skipping (not found): {item}")
    return files


def convert_one(src, out_dir, encoder, name):
    """Convert `src` to out_dir/<name>.gta. `name` is the final in-game name (no extension)."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "in.wav")
        at3 = os.path.join(tmp, "out.at3")
        secs = decode_to_wav(src, wav)
        if secs > MAX_SECONDS:
            print(f"  WARNING: {secs/60:.0f} min is over the PSP's 120-minute limit; "
                  f"this track probably won't play. Split it into smaller files.")
        r = subprocess.run(
            [encoder, "-e", "atrac3_lp4", "--container", "riff", "-i", wav, "-o", at3],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if r.returncode != 0 or not os.path.isfile(at3):
            tail = r.stdout.decode(errors="replace")[-400:]
            raise RuntimeError(f"encoder failed: {tail}")
        fix_header(at3)
        dest = os.path.join(out_dir, name + ".gta")
        shutil.move(at3, dest)
    return dest, secs


def main():
    ap = argparse.ArgumentParser(description="Convert audio to .gta for GTA LCS/VCS (PSP)")
    ap.add_argument("inputs", nargs="+", help="audio files and/or folders")
    ap.add_argument("--out", default="gta_output", help="output folder (default: gta_output)")
    ap.add_argument("--psp", help="PSP Memory Stick drive/root, e.g. E: or /media/psp")
    ap.add_argument("--game", help="game ID, e.g. ULUS10041 (LCS US), ULUS10160 (VCS US)")
    ap.add_argument("--name-style", choices=track_names.STYLES, default="artist-title",
                    help="how in-game names are built (default: artist-title, from tags when present)")
    ap.add_argument("--keep-punctuation", action="store_true",
                    help="keep ' & , . ! ( ) in names (default: letters, digits, spaces and hyphens only)")
    ap.add_argument("--max-length", type=int, default=40, help="longest in-game name (default 40)")
    ap.add_argument("--fix-caps", action="store_true", help="fix ALL CAPS / all lowercase names")
    ap.add_argument("--number", action="store_true", help='prefix names with "01 - ", "02 - " in input order')
    ap.add_argument("--dry-run", action="store_true", help="only show the in-game names, convert nothing")
    args = ap.parse_args()

    enc = find_encoder()
    if not enc:
        sys.exit("Could not find atracdenc.exe. Keep it in the same folder as this script.")

    files = collect(args.inputs)
    if not files:
        sys.exit("No audio files found.")

    out_dir = args.out
    if args.psp:
        if not args.game:
            sys.exit("--psp needs --game (for example --game ULUS10041).")
        out_dir = os.path.join(args.psp, "PSP", "SAVEDATA", args.game.upper() + "CUSTOMTRACKS")
        print(f"Writing straight to: {out_dir}")

    suggested = [track_names.suggest_name(f, args.name_style, args.keep_punctuation,
                                          args.max_length, args.fix_caps) for f in files]
    names = track_names.number_and_dedupe(suggested, args.keep_punctuation, args.max_length, args.number)
    if args.dry_run:
        for f, n in zip(files, names):
            print(f"{os.path.basename(f)}  ->  {n}.gta")
        return
    os.makedirs(out_dir, exist_ok=True)

    ok, total_secs = 0, 0
    for i, (f, name) in enumerate(zip(files, names), 1):
        print(f"[{i}/{len(files)}] {os.path.basename(f)}  ->  {name}")
        try:
            dest, secs = convert_one(f, out_dir, enc, name)
            total_secs += secs
            ok += 1
            print(f"  -> {os.path.basename(dest)}  ({secs/60:.1f} min, "
                  f"{os.path.getsize(dest)/1e6:.1f} MB)")
        except Exception as e:  # keep going on a bad file
            print(f"  FAILED: {e}")
    print(f"\nDone: {ok}/{len(files)} converted, {total_secs/60:.1f} min total.")
    print(f"Output folder: {os.path.abspath(out_dir)}")
    if not args.psp:
        print("Copy the .gta files into PSP/SAVEDATA/<GAMEID>CUSTOMTRACKS/ on your Memory Stick.")
    print("In game: Pause > Audio > My Songs ON, then get in a vehicle.")


if __name__ == "__main__":
    main()
