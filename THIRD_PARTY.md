# Third-party software and data

Nexarch's engine, trainer and tools are MIT licensed (see `LICENSE`). The desktop GUI and
some data are separate programs or separate works with their own licenses. This file is the
map; the full credits are in `CREDITS.md`, and the grading-engine table is in `ENGINES.md`.

## The desktop GUI

| Component | License | Source |
|---|---|---|
| Cute Chess 1.5.1 | GPL-3.0-or-later | https://github.com/cutechess/cutechess/tree/v1.5.1 |
| Cute Chess icons and logo | GPL-3.0-or-later | same repository, `projects/gui/res/icons` |
| python-chess (used by Nexarch Arena) | GPL-3.0 | https://github.com/niklasf/python-chess |
| Qt 6 (bundled with Cute Chess) | LGPL-3.0 / GPL-3.0 | https://www.qt.io/ |
| Cburnett chess pieces | CC BY-SA 3.0 | via Wikimedia Commons |

The official Cute Chess Linux AppImage and Windows zip are redistributed unmodified. The
complete corresponding source is the v1.5.1 tag above and is included with the release as
`gui/cutechess/cutechess-1.5.1.tar.gz`. Nexarch only adds an `engines.json` configuration
file, which is data. The Nexarch Arena (`gui/nexarch_gui.py`) is a separate GPL-3.0 program
because it imports python-chess and uses the Cute Chess assets; the engine and the rest of
this repository remain MIT.

## The optional OpenCL backend

The OpenCL headers under `third_party/opencl` are from the Khronos Group and are Apache-2.0.
The OpenCL ICD loader and the vendor drivers (ocl-icd, Mesa rusticl, Intel, AMD, NVIDIA) are
loaded at runtime and are not distributed with Nexarch.

## Grading engines

The engines used to grade training data are listed in `ENGINES.md`, with their licenses and
project links. None of them are included in this repository or in the Nexarch installer.
They are separate programs that the grading scripts start over UCI. If you redistribute any
of them yourself, you must comply with that engine's license; the AGPL-3.0 engines are used
locally only and are not part of a network service.

The networks are trained on evaluations and game results, not on engine source code. No
engine code is linked into or copied into Nexarch.

## Training data and converted files

| Data | License | Notes |
|---|---|---|
| Leela Chess Zero T80 | ODbL-1.0 + DbCL-1.0 | converted files keep the source license |
| Stockfish `master-binpacks` | ODbL-1.0 | converted files keep the source license |
| Lichess evaluation database and fishnet evals | CC0-1.0 | Nexarch conversions are MIT |
| Nexarch self-play and graded sets | MIT | Mark Ivanovskyy |
| Gen 5 frozen evaluation set | MIT | Mark Ivanovskyy |

See `CREDITS.md` for the links and attribution. If a third-party license and this summary
differ, the third-party license wins for that component.
