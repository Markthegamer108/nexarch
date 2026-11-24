# Roadmap

Nexarch is MIT licensed. Everything in this repository that was written for Nexarch is
copyright (c) 2026 Mark Ivanovskyy and released under the MIT license in [LICENSE](LICENSE).
Third-party engines, datasets, opening books and tools keep their own licenses; see
[CREDITS.md](CREDITS.md).

## Gen 5

Gen 5 is the current generation. It is not finished when the first h2048 training run ends.

- Train h2048 on the 2.04B-position Gen 5 set.
- Keep feeding the same generation more data: the converted Stockfish binpacks
  (`fishpack32` first), then more self-play and more Lichess/T80/fishnet months.
- Grow the network (h4096 and beyond) only when the extra width pays for its speed in
  timed matches. A bigger network that is slower at the same clock is not an upgrade.
- Consume the available data to the brim before calling Gen 5 done. If the quota only
  covers part of the data in one week, continue the next week from the checkpoint.

Gen 5 is released only when all of these are true:

- the frozen-holdout audit reports no training positions in the evaluation set;
- it beats Gen 4 by roughly +200 Elo or more in 400 timed games, with the 95% interval
  clearly above zero;
- the 33-engine panel and Lc0 show the same gain, not one lucky opponent;
- the CPU build, GPU build, GUI, installer and Kaggle notebook are ready;
- every engine, network, dataset, book and tool is credited.

No Gen 6 self-play starts before Gen 5 is verified and released.

## Release builds

Two builds of the same engine and network:

- **CPU build** - the current portable build. It must run on ordinary laptops and older
  PCs without a graphics card, and it stays the reference for match results.
- **GPU build** - the same UCI engine with NNUE inference on the GPU. It must work on
  NVIDIA (CUDA), AMD (ROCm/HIP) and Intel (oneAPI/SYCL or OpenCL), detect the available
  backend at startup, and fall back to the CPU build when no supported GPU is present.
  The GPU and CPU builds must return the same evaluations within quantization tolerance.

Both builds speak UCI, so they work in Cute Chess and other standard chess GUIs.

## GUI and installer

- A cross-platform GUI that launches when the engine is started manually. It should feel
  like Cute Chess: board, clocks, move list, PGN, engine log, analysis, engine options,
  opening book, and a credits/about panel. Cute Chess itself is GPL-3.0; if its code is
  reused it stays a separate GPL-3.0 program, not part of the MIT engine.
- A chess-themed installer for Windows, macOS and Linux with an optional desktop
  shortcut, an uninstall entry in the system's normal place, and a clear license page.
- The installer offers anonymous game collection, **off by default**. When enabled it
  sends only games played against Nexarch, with no account name, email or hardware ID.
  The setting can be changed later and the collected data is described in the GUI.
- A credits screen in the GUI and a credits section on GitHub, covering every engine,
  network, dataset, book, library and free compute provider.

## Kaggle notebook

A public Kaggle notebook that anyone can open and run:

1. installs the engine and the GUI dependencies;
2. downloads the released network;
3. explains how to play against Nexarch in the notebook and in a normal GUI;
4. shows how to run a short match and read the result;
5. links to the CPU and GPU builds, the installer and the credits.

The notebook is a tutorial first, not a benchmark. It must work on Kaggle's free CPU
notebooks and explain the GPU option separately.

## Search and training work

- Search changes are tested with SPRT, not single games: SEE pruning, singular
  extensions, continuation history, better LMR and time management.
- Data pipeline: download one Stockfish binpack at a time, convert it with
  `kaggle/convert-binpack.sh`, audit the output, upload it to
  `mark43233/nexarch-binpacks`, and delete the local copy. The laptop has limited disk
  space, so the pipeline never keeps two large binpacks at once. If the converted file
  would not fit, the conversion stops at the disk budget and the manifest marks the
  result as `capped`; that file is a prefix of the source, not a random sample.
- Every promoted network gets a manifest with the data files, their hashes, the trainer
  command and the match protocol.
