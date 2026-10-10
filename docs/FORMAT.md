# The .gta format (as far as it is understood)

A `.gta` custom-track file is a normal **ATRAC3 RIFF/WAVE (`.at3`) file with a different extension**.
Nothing is encrypted or wrapped. Rockstar's converter writes `.toc`, which is renamed to `.gta`.

## Layout of a working file (66 kbps stereo)

```
RIFF <size> WAVE
fmt  (32 bytes)
  70 02            format tag 0x0270 (ATRAC3)
  02 00            channels = 2
  44 AC 00 00      sample rate = 44100
  4D 20 00 00      average bytes/sec = 8269
  C0 00            block align = 192  (66 kbps "LP4")
  00 00            bits per sample = 0
  0E 00            extra data size = 14
  01 00 00 10 00 00 01 00 01 00 01 00 00 00   extra data
fact (8 bytes)
  <samples: u32> 00 04 00 00                  second value = 1024
data <frames * 192 bytes>
```

## What mattered

A file made with the same encoder but with the encoder's default header was **listed in the game
but played silent** (the same symptom is reported in old GTAForums threads). Rewriting two header
values to match Sony's `at3tool` made the same audio play:

- average bytes/sec: `8269` instead of `8268`
- `fact` sample count: `frames * 1024 - 1152` (the one reference file examined is consistent with `frames = ceil((samples + 1105) / 1024)`)

Both were changed together, so it is not known which of the two the game checks.
The audio stream itself does not need to come from Sony's encoder: output from
atracdenc and from Sony's own ACM codec both played once the header was fixed.

## Other facts

- 66 kbps (block align 192) is what the reference file uses. Other bitrates were not retested after the header fix.
- Sample rate 44100 Hz, stereo.
- PSP playback limit: 120 minutes per file.
