# Cute Chess

The Nexarch release uses [Cute Chess](https://github.com/cutechess/cutechess) 1.5.1 as its
desktop chess GUI. Cute Chess is a mature GPL-3.0 chess GUI with a board, clocks, PGN, engine
management, tournaments and a full settings dialog. Nexarch is shipped as a preconfigured
engine, and you can add Stockfish or any other UCI engine from Cute Chess's own engine settings.

The release GUI is **Cute Chess - Nexarch Remake**, built from the literal Cute Chess 1.5.1
source in `gui/cutechess-source/` with the Nexarch additions described in
`gui/arena/README.md`. The official binaries in this directory are kept as a reference and
for users who want the unmodified upstream client.

The binary is not stored in this git repository. Fetch the official Linux AppImage and the
Windows zip (and the matching source tarball) with:

```
python tools/fetch_cutechess.py
```

The script verifies the SHA-256 of each download. The Linux AppImage and Windows zip are
unmodified official releases. The Nexarch Remake build and its complete source are in
`gui/arena/` and `gui/cutechess-source/`. Cute Chess is licensed under GPL-3.0-or-later;
see `COPYING` and `SOURCE.md` in this directory. The Nexarch engine is a separate MIT program.
