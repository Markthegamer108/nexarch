# Cute Chess source

Nexarch keeps the official Cute Chess 1.5.1 binaries and source here:

- Linux: `Cute_Chess-1.5.1-x86_64.AppImage`
- Windows: `cutechess-1.5.1-win64.zip`
- Upstream source: https://github.com/cutechess/cutechess/archive/refs/tags/v1.5.1.tar.gz
- Nexarch Remake source: `gui/cutechess-source/` (the literal v1.5.1 tree plus Nexarch changes)

Cute Chess is free software under the GNU General Public License, version 3 or later
(GPL-3.0-or-later). The complete corresponding source is the v1.5.1 tag above, and the
source tarball is fetched by `tools/fetch_cutechess.py` into this directory. The binaries
here are unmodified official releases. The release GUI is the Nexarch Remake build in
`gui/arena/`, whose complete source is `gui/cutechess-source/`; it adds online play, live
rankings, the anonymous game setting and a Nexarch menu, and is GPL-3.0-or-later.

To rebuild on Linux:

```
sudo apt install qt6-base-dev qt6-svg-dev qt6-tools-dev cmake ninja-build
cmake -S cutechess-1.5.1 -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

Cute Chess was written by Ilari Pihlajisto, Arto Jonsson and contributors. See
`AUTHORS` and `COPYING`.
