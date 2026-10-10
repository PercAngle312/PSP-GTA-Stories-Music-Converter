# Building

## From source (any OS)

```
pip install -r requirements.txt
```
Put an `atracdenc` binary (`atracdenc.exe` on Windows) in `src/`, then run `python src/gta_music_gui.py`.
(`tkinter` is needed for the GUI; it ships with Python on Windows.)

## atracdenc for Windows (what the Releases use)

Built unmodified from <https://github.com/dcherednik/atracdenc> at commit
`cb170709f836cb43dc0312455188c791159d81dc`, cross-compiled with MinGW-w64 (32-bit, static) on Linux.

```
# static libsndfile, no external codecs
git clone --depth 1 https://github.com/libsndfile/libsndfile.git
cmake -S libsndfile -B lsf-build -DCMAKE_TOOLCHAIN_FILE=mingw32.cmake -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF -DENABLE_EXTERNAL_LIBS=OFF -DENABLE_MPEG=OFF -DBUILD_PROGRAMS=OFF \
  -DBUILD_EXAMPLES=OFF -DBUILD_TESTING=OFF -DCMAKE_INSTALL_PREFIX=$PWD/lsf-install
cmake --build lsf-build && cmake --install lsf-build

# atracdenc
git clone https://github.com/dcherednik/atracdenc.git && cd atracdenc
git checkout cb170709f836cb43dc0312455188c791159d81dc && git submodule update --init --recursive
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=../mingw32.cmake -DCMAKE_BUILD_TYPE=Release \
  -DATRACDENC_PCM_IO_BACKEND=libsndfile -DCMAKE_PREFIX_PATH=$PWD/../lsf-install \
  -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH
cmake --build build --target atracdenc
i686-w64-mingw32-strip -o atracdenc.exe build/src/atracdenc.exe
```

`mingw32.cmake`:
```
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_C_COMPILER i686-w64-mingw32-gcc-posix)
set(CMAKE_CXX_COMPILER i686-w64-mingw32-g++-posix)
set(CMAKE_RC_COMPILER i686-w64-mingw32-windres)
set(CMAKE_EXE_LINKER_FLAGS "-static -static-libgcc -static-libstdc++")
```
On Windows you can alternatively build atracdenc with MSVC using its Media Foundation backend (not tried here).

## Standalone exe (32-bit Windows Python 3.12)

```
pip install pyinstaller miniaudio
cd src
pyinstaller --noconfirm --onefile --windowed --name "GTA Stories Music Converter" ^
  --add-binary "atracdenc.exe;." --collect-all miniaudio ^
  --hidden-import _cffi_backend --hidden-import _miniaudio --hidden-import miniaudio --hidden-import cffi ^
  gta_music_gui.py
```

## Installer (NSIS)

Copy the built exe to `installer/app.exe`, then `makensis installer/installer.nsi`
(it also expects `README.txt` and `ATRACDENC_LICENSE.txt` in `installer/`, which are included).
