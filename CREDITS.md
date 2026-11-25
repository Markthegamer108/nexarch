# Credits

Nexarch is my engine, but it would be nowhere without other people's work. Thank you to all of them.

## The engines that grade Nexarch's training data

Since Gen 2, every position Nexarch learns from is judged by a panel of engines. They run as separate
programs, and none of their code is part of Nexarch. What each one judges, and its license, is in
[ENGINES.md](ENGINES.md).

| Engine | By | License |
|---|---|---|
| Stockfish 19 | [official-stockfish](https://github.com/official-stockfish/Stockfish) | GPL-3.0 |
| Reckless 0.9.0 | [codedeliveryservice](https://github.com/codedeliveryservice/Reckless) | AGPL-3.0 |
| Triumviratus 8.0 | [Tors3](https://github.com/Tors3/Triumviratus) | GPL-3.0 |
| Berserk 14 | [jhonnold](https://github.com/jhonnold/berserk) | GPL-3.0 |
| Stormphrax 8.0.0 | [Ciekce](https://github.com/Ciekce/Stormphrax) | GPL-3.0 |
| Obsidian 16.0 | [gab8192](https://github.com/gab8192/Obsidian) | GPL-3.0 |
| ShashChess 42.3 | [amchess](https://github.com/amchess/ShashChess) | GPL-3.0 |
| Cinder 0.6.1 | [brunocodutra](https://github.com/brunocodutra/cinder) | GPL-3.0 |
| Tarnished 6.0 | [Bobingstern](https://github.com/Bobingstern/Tarnished) | GPL-3.0 |
| Quanticade Cronus 3.0 | [Quanticade](https://github.com/Quanticade/Quanticade) | GPL-3.0 |
| Arasan 26.1 | [jdart1](https://github.com/jdart1/arasan-chess) | see project |
| Raphael 4.2.0 | [Orbital-Web](https://github.com/Orbital-Web/Raphael) | AGPL-3.0 |
| Hobbes 3.0 | [kelseyde](https://github.com/kelseyde/hobbes-chess-engine) | MIT |
| Viridithas 20.0.0 | [cosmobobak](https://github.com/cosmobobak/viridithas) | AGPL-3.0 |
| Halogen 16 | [KierenP](https://github.com/KierenP/Halogen) | GPL-3.0 |
| Integral v8 | [aronpetko](https://github.com/aronpetko/integral) | not stated on GitHub |
| Caissa 2.0 | [Witek902](https://github.com/Witek902/Caissa) | MIT |
| Seer 2.8.0 | [connormcmonigle](https://github.com/connormcmonigle/seer-nnue) | GPL-3.0 |
| pawnocchio 2.0.1 | [JonathanHallstrom](https://github.com/JonathanHallstrom/pawnocchio) | GPL-3.0 |
| Astra 7.0 | [h1me01](https://github.com/h1me01/Astra) | GPL-3.0 |
| Devre 7.0 | [OmerFarukTutkun](https://github.com/OmerFarukTutkun/Devre) | GPL-3.0 |
| Clover 9.1 | [lucametehau](https://github.com/lucametehau/CloverEngine) | GPL-3.0 |
| Renegade 1.3.1 | [pkrisz99](https://github.com/pkrisz99/Renegade) | MIT |
| PZChessBot 7.1 | [kevlu8](https://github.com/kevlu8/PZChessBot) | AGPL-3.0 |
| Maia 1900 | [CSSLab](https://github.com/CSSLab/maia-chess) | GPL-3.0 |
| PlentyChess 8.0.0 | [Yoshie2000](https://github.com/Yoshie2000/PlentyChess) | GPL-3.0 |
| Coda 0.9.4 | [adamtwiss](https://github.com/adamtwiss/coda) | GPL-3.0 |
| Alexandria 9.1.0 | [PGG106](https://github.com/PGG106/Alexandria) | GPL-3.0 |
| RubiChess 20240817 | [Matthies](https://github.com/Matthies/RubiChess) | GPL-3.0 |
| Koivisto 9.0 | [Luecx](https://github.com/Luecx/Koivisto) | GPL-3.0 |
| Ethereal 14.40 | [AndyGrant](https://github.com/AndyGrant/Ethereal) | GPL-3.0 |
| Lc0 0.32.1 | [LeelaChessZero](https://github.com/LeelaChessZero/lc0) | GPL-3.0 |

## Networks

- The BT4 network (`BT4-1024x15x32h-swa-6147500-policytune-332`) by the Leela Chess Zero project. Lc0 runs it
  to give its verdict on every position.
- Maia 1900 by the CSSLab at the University of Toronto, the panel's "how would a strong human play" judge.

## Training data

- **Leela Chess Zero training data (the T80 run)**, by the Leela Chess Zero project and everyone who donated
  computer time to it. Nexarch's networks from Gen 4 on contain information from this data, which is made
  available under the [Open Database License (ODbL) v1.0](https://opendatacommons.org/licenses/odbl/1-0/); its
  individual contents are under the [Database Contents License (DbCL) v1.0](https://opendatacommons.org/licenses/dbcl/1-0/).
  I use the binpack conversion that linrock publishes at
  [huggingface.co/datasets/linrock/test80-2024](https://huggingface.co/datasets/linrock/test80-2024).
- **The Lichess evaluation database**, by [Lichess](https://database.lichess.org/) and everyone who analyses
  positions on the Lichess analysis board. Released under CC0.
- **The Lichess fishnet evaluation database**, the raw 34.5-billion-position set behind the evaluation
  database, computed by Lichess's distributed Stockfish analysis (fishnet) and released under CC0 at
  [huggingface.co/datasets/Lichess/fishnet-evals](https://huggingface.co/datasets/Lichess/fishnet-evals).
  Nexarch streams monthly slices of it instead of holding the whole thing.
- **The Stockfish binpack collection**, by the Stockfish project and its contributors, at
  [huggingface.co/datasets/official-stockfish/master-binpacks](https://huggingface.co/datasets/official-stockfish/master-binpacks).
  Released under the Open Database License (ODbL) v1.0. Nexarch converts the `fishpack32` and
  `farseerT76` binpacks to its own format with `tools/binpack/binpack2nexarch` and keeps the converted
  files under the same license. The `farseerT76` conversion is a prefix of the source because of the
  laptop's disk budget; its manifest records the exact range.
- **Nexarch's own data conversions, manifests and evaluation sets**, by Mark Ivanovskyy, are MIT licensed
  unless the source data requires a different license. The Gen 5 unseen evaluation set is MIT; the
  fishpack32 conversion stays ODbL because its source does.

## Testing

- The [UHO 8-move opening book](https://github.com/official-stockfish/books) (`8mvs_+90_+99.epd`)
  from the Stockfish project's book collection, released under CC0. The panel benchmark starts every
  engine from these balanced positions so the result does not depend on one opening.

## Tools and libraries

- Tomasz Sobczyk's binpack library (MIT), from
  [official-stockfish/nnue-pytorch](https://github.com/official-stockfish/nnue-pytorch), reads Stockfish's
  training data format (`tools/binpack`).
- [PyTorch](https://pytorch.org/), [NumPy](https://numpy.org/), [python-chess](https://github.com/niklasf/python-chess)
  by Niklas Fiekas, [Apache Arrow](https://arrow.apache.org/) (pyarrow), [Zstandard](https://github.com/facebook/zstd)
  and the [Kaggle CLI](https://github.com/Kaggle/kaggle-cli).

## Interface

- **Cute Chess 1.5.1**, by Ilari Pihlajisto, Arto Jonsson and contributors, at
  [github.com/cutechess/cutechess](https://github.com/cutechess/cutechess), GPL-3.0-or-later.
  It is the desktop GUI in the Nexarch release. The build is titled **Cute Chess - Nexarch
  Remake** and adds online play, live rankings, the anonymous game setting and a Nexarch menu.
  The complete corresponding source is in `gui/cutechess-source/`; the original source is also
  at `gui/cutechess/SOURCE.md`. The Nexarch engine remains a separate MIT program.
- The Cute Chess application icon and toolbar icons, from the same repository, GPL-3.0-or-later.
- **python-chess**, by Niklas Fiekas, at
  [github.com/niklasf/python-chess](https://github.com/niklasf/python-chess), GPL-3.0. It powers
  the online relay server and the web Arena companion; the engine remains MIT.
- The Cburnett chess piece SVG set (CC BY-SA 3.0), via Wikimedia Commons, for the board's pieces
  (`gui/pieces`).
- Qt 6, bundled with Cute Chess, LGPL-3.0 / GPL-3.0; see the Qt project for the corresponding source.

## Ideas

- NNUE, invented by Yu Nasu for shogi and brought to chess by the Stockfish project.
- The [CCRL](https://computerchess.org.uk/ccrl/) rating lists and Stefan Pohl's EAS aggressiveness list, which I
  used to decide what each grading engine judges.

## Compute and hosting

- [Kaggle](https://www.kaggle.com/), for the free GPUs and CPUs that do most of the grading and all of the training.
- GitHub, for hosting Nexarch and for Actions.
- Hugging Face, for hosting the Leela and Lichess data.
