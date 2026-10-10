"""Work out a clean, in-game-friendly name for each song.

The game shows the .gta file name, so we build that name from the song's tags
(MP3 ID3 / FLAC) when available, otherwise from a tidied-up version of its file name.
Output uses plain ASCII so it is safe on the PSP's FAT Memory Stick.
"""
import functools
import os
import re
import struct
import unicodedata

STYLES = ("artist-title", "title", "filename")
SAFE_BASE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -")
SAFE_PUNCT = set("'&,.!()")

# "(Official Video)", "[HD]", "(Lyrics)", ... removed from names
_JUNK_BRACKET = re.compile(
    r"[\(\[][^\)\]]*\b(official|video|audio|lyrics?|visuali[sz]er|hd|hq|4k|remaster(ed)?|"
    r"music video|full album|explicit)\b[^\)\]]*[\)\]]", re.I)
_LEADING_TRACKNO = re.compile(r"^\s*\d{1,3}\s*[-_.)\s]+\s*(?=\D)")
_TRAILING_RATE = re.compile(r"[\s_-]+44[._ ]?1\s?k(hz)?\s*$", re.I)
_TRAILING_HASH = re.compile(r"[\s_-]+(?=[0-9A-Za-z]{8}$)(?=.*\d)(?=.*[A-Za-z])[0-9A-Fa-f]{8}$")


# ---------------------------------------------------------------- tags
def _decode(enc, b):
    try:
        if enc == 1:
            return b.decode("utf-16", "ignore")
        if enc == 2:
            return b.decode("utf-16-be", "ignore")
        if enc == 3:
            return b.decode("utf-8", "ignore")
        return b.decode("latin-1", "ignore")
    except Exception:
        return ""


def _syncsafe(b):
    return (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]


def _id3v2(data):
    """Return {'title':..,'artist':..} from the ID3v2 tag at the start of `data`."""
    out = {}
    if data[:3] != b"ID3" or len(data) < 10:
        return out
    ver = data[3]
    size = _syncsafe(data[6:10])
    tag = data[10:10 + size]
    pos = 0
    if data[5] & 0x40 and ver >= 3 and len(tag) >= 4:  # extended header
        ext = _syncsafe(tag[:4]) if ver == 4 else struct.unpack(">I", tag[:4])[0] + 4
        pos = ext
    ids = {b"TIT2": "title", b"TPE1": "artist", b"TT2": "title", b"TP1": "artist"}
    while pos + (6 if ver == 2 else 10) <= len(tag):
        if ver == 2:
            fid, fsize, hdr = tag[pos:pos + 3], int.from_bytes(tag[pos + 3:pos + 6], "big"), 6
        else:
            fid = tag[pos:pos + 4]
            raw = tag[pos + 4:pos + 8]
            fsize = _syncsafe(raw) if ver == 4 else struct.unpack(">I", raw)[0]
            hdr = 10
        if not fid.strip(b"\x00") or fsize <= 0:
            break
        body = tag[pos + hdr:pos + hdr + fsize]
        key = ids.get(fid)
        if key and body and key not in out:
            text = _decode(body[0], body[1:]).split("\x00")[0].strip()
            if text:
                out[key] = text
        pos += hdr + fsize
    return out


@functools.lru_cache(maxsize=4096)
def read_tags(path):
    """Return (artist, title); either may be ''."""
    ext = os.path.splitext(path)[1].lower()
    artist = title = ""
    try:
        with open(path, "rb") as f:
            head = f.read(1 << 20)
            if ext == ".mp3":
                t = _id3v2(head)
                artist, title = t.get("artist", ""), t.get("title", "")
                if not (artist and title):  # ID3v1 fallback
                    f.seek(-128, 2)
                    v1 = f.read(128)
                    if v1[:3] == b"TAG":
                        if not title:
                            title = v1[3:33].split(b"\x00")[0].decode("latin-1", "ignore").strip()
                        if not artist:
                            artist = v1[33:63].split(b"\x00")[0].decode("latin-1", "ignore").strip()
            elif ext == ".flac" and head[:4] == b"fLaC":
                pos = 4
                while pos + 4 <= len(head):
                    h = head[pos]
                    ln = int.from_bytes(head[pos + 1:pos + 4], "big")
                    if h & 0x7F == 4:  # VORBIS_COMMENT
                        b = head[pos + 4:pos + 4 + ln]
                        vl = struct.unpack("<I", b[:4])[0]
                        p = 4 + vl
                        n = struct.unpack("<I", b[p:p + 4])[0]
                        p += 4
                        for _ in range(n):
                            cl = struct.unpack("<I", b[p:p + 4])[0]
                            c = b[p + 4:p + 4 + cl].decode("utf-8", "ignore")
                            p += 4 + cl
                            k, _, v = c.partition("=")
                            if k.upper() == "TITLE" and not title:
                                title = v.strip()
                            elif k.upper() == "ARTIST" and not artist:
                                artist = v.strip()
                        break
                    pos += 4 + ln
                    if h & 0x80:
                        break
    except Exception:
        pass
    return artist, title


# ---------------------------------------------------------------- cleaning
def _ascii(s):
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("&amp;", "&")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if ord(c) < 128)


def tidy_caps(s):
    """Fix ALL CAPS / all lower case names only; leave mixed case alone."""
    letters = [c for c in s if c.isalpha()]
    if not letters or not (all(c.isupper() for c in letters) or all(c.islower() for c in letters)):
        return s
    small = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to", "vs"}
    words, out = s.split(" "), []
    for i, w in enumerate(words):
        lw = w.lower()
        out.append(lw if (i and lw in small) else re.sub(r"(^|[-(\"'])([a-z])", lambda m: m.group(1) + m.group(2).upper(), lw, count=1) if lw else lw)
    return " ".join(out)


def clean_text(s, from_filename=False):
    s = _ascii(s)
    if from_filename:
        s = s.replace("_", " ")
        s = _TRAILING_HASH.sub("", _TRAILING_RATE.sub("", s))
        s = _LEADING_TRACKNO.sub("", s)
    s = _JUNK_BRACKET.sub("", s)
    s = re.sub(r"\s+", " ", s).strip(" -.")
    return s


def finalize(name, keep_punct=False, max_len=40):
    """Make `name` safe: allowed characters only, trimmed, no longer than max_len."""
    allowed = SAFE_BASE | (SAFE_PUNCT if keep_punct else set())
    name = "".join(c for c in _ascii(name) if c in allowed)
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"(\s*-\s*){2,}", " - ", name).strip(" -.")
    if len(name) > max_len:
        cut = name[:max_len]
        if " " in cut and not name[max_len].isspace():
            cut = cut.rsplit(" ", 1)[0]
        name = cut.rstrip(" -.,(")
    return name or "Track"


def suggest_name(path, style="artist-title", keep_punct=False, max_len=40, fix_caps=False):
    """Name (no extension) for `path`, before numbering/de-duplication."""
    base = os.path.splitext(os.path.basename(path))[0]
    artist, title = read_tags(path)
    artist, title = clean_text(artist), clean_text(title)
    fallback = clean_text(base, from_filename=True)
    if style == "filename":
        name = fallback
    elif style == "title":
        name = title or fallback
    else:
        name = f"{artist} - {title}" if artist and title else (title or fallback)
    if fix_caps:
        name = tidy_caps(name)
    if len(finalize(name, keep_punct, 10**6)) > max_len and style == "artist-title" and title:
        name = tidy_caps(title) if fix_caps else title  # too long with artist: show the title alone
    return finalize(name, keep_punct, max_len)


def number_and_dedupe(names, keep_punct=False, max_len=40, number=False):
    """Final, unique file-name stems for `names` (in play order)."""
    out, used = [], set()
    for i, n in enumerate(names, 1):
        prefix = f"{i:02d} - " if number else ""
        room = max(max_len - len(prefix), 8)
        base = finalize(n, keep_punct, room)
        cand, k = prefix + base, 2
        while cand.lower() in used:
            suffix = f" {k}"
            cand = prefix + finalize(base, keep_punct, room - len(suffix)) + suffix
            k += 1
        used.add(cand.lower())
        out.append(cand)
    return out
