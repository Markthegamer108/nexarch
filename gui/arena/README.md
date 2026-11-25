# Cute Chess - Nexarch Remake

This is the desktop GUI in the Nexarch release. It is built from the literal
[Cute Chess 1.5.1](https://github.com/cutechess/cutechess) source, which is included in
`../cutechess-source`, with a small set of Nexarch additions:

- a **Nexarch** menu with Play Online, Live Rankings, Settings and Credits
- anonymous game collection, off by default, with a fixed upload address
- online human-vs-human play through the Nexarch relay
- live Lichess and Chess.com blitz rankings
- a light palette when the desktop theme is dark, so the Cute Chess toolbar icons stay visible
- the window and About box are titled **Cute Chess - Nexarch Remake**

Everything else - the board, clocks, PGN, engine management, tournaments, opening books and
the full settings dialog - is Cute Chess.

## License and source

Cute Chess is free software under the GNU General Public License, version 3 or later.
The Nexarch modifications are released under the same license. The complete corresponding
source is in `gui/cutechess-source/`, and the original source is also available from the
Cute Chess project. See `COPYING` and `AUTHORS` in this directory.

The Nexarch engine is a separate MIT-licensed program. It is loaded as a UCI engine and is
not linked into Cute Chess.

## Building

```bash
sudo apt install qt6-base-dev qt6-svg-dev qt6-tools-dev qt6-network-dev cmake ninja-build
cd gui/cutechess-source
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DWITH_TESTS=OFF
cmake --build build -j$(nproc)
# binary: build/cutechess
```

On Windows install Qt 6.8+ and Visual Studio 2022, then configure with
`-DCMAKE_PREFIX_PATH=C:\Qt\6.8.0\msvc2022_64`. On macOS use `brew install qt6 cmake ninja`.
See `../cutechess/BUILD.md` for the upstream build notes.

## Online play

The official relay is `http://158.180.55.245:8090`. Create a room and share the six-character
code, or join a friend's room. The server only keeps moves and display names in memory for
24 hours. No accounts, email addresses or hardware IDs are used.
