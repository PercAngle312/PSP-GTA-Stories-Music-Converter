# Third-party software

| Component | License | Use |
|---|---|---|
| [atracdenc](https://github.com/dcherednik/atracdenc) | LGPL-2.1 | ATRAC3 encoder, run as a separate program (`atracdenc.exe`). Release binaries are built from the unmodified upstream source at commit `cb170709f836cb43dc0312455188c791159d81dc`; see [docs/BUILD.md](docs/BUILD.md). Its license text is in `installer/ATRACDENC_LICENSE.txt`. |
| [libsndfile](https://github.com/libsndfile/libsndfile) | LGPL-2.1 | Linked statically into the Windows `atracdenc.exe` build. Source is available at the link. |
| [miniaudio (Python)](https://pypi.org/project/miniaudio/) | MIT | Decodes MP3/FLAC/OGG/WAV input. |
| [PyInstaller](https://pyinstaller.org) | GPL-2.0 with bootloader exception | Used to bundle the exe. |
| [NSIS](https://nsis.sourceforge.io) | zlib/libpng | Used to build the installer. |

This project does **not** include or redistribute Sony's `atrac3.acm` codec or any Rockstar software.
