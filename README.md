# Nexarch

Nexarch is a chess engine I'm writing from scratch. The goal is to beat Stockfish 19 at full strength,
and the other top engines too.

It's nowhere near that yet. Right now it's a small engine with a small network, but everything needed
to make it stronger is in this repo: the engine, the self-play code, the grading setup and the trainer.
Every generation learns from the games of the one before it, and I keep going until it's good enough.

## The engine

It's an alpha-beta engine with an NNUE evaluation, which is basically what all the strong CPU engines
do now.

- bitboards and magic bitboards for move generation (it passes the standard perft tests)
- iterative deepening, PVS, transposition table, quiescence search
- null move pruning, futility pruning, late move reductions
- NNUE network `(768 -> H) x 2 -> 1` with SCReLU, quantized to integers

The network gets trained on a GPU but the engine only needs a CPU. I wanted it to run on any laptop or PC,
not just on a PC with a graphics card.

## How a new generation gets made

1. Self-play. The current network plays a lot of games against itself with `nexarch datagen`.
2. Grading. Other engines go over those positions and say how good they really are. Each one has a
   job depending on what it's good at, for example tactics, sacrifices, attacking, defending,
   endgames or quiet positions. Stockfish 19 checks every position, and Lc0 looks at the positional
   ones on a GPU. All of that gets averaged into one score per position (`tools/grade.py` and
   `tools/lc0_batch_grade.py`).
3. Training. `trainer/train.py` trains the next network on those scores.
4. Testing. The new network plays the old one (`nexarch match`). It only counts if it wins.

The other engines aren't in this repo. Nexarch just talks to them over UCI. [ENGINES.md](ENGINES.md)
has the list, what each one does, their licenses and where to download them.

## Progress

| Generation | Trained on | Result |
|---|---|---|
| Gen 0 | nothing, it just counts material | starting point |
| Gen 1 | Gen 0's self-play games | +124 Elo vs Gen 0 |
| Gen 2 | Gen 0's games, scored by Stockfish | +129 Elo vs Gen 1 |
| Gen 3 | Gen 2's games (33.5M positions), scored by the whole panel and Lc0 | +300 Elo vs Gen 2: 84.9% in 400 timed games (84.2% at 5,000 nodes), 512 neurons |
| Gen 4 | 560M positions: Gen 2's graded games, Leela's public training data and the Lichess evaluations | **+271 Elo vs Gen 3: 82.6% in 400 timed games, 1024 neurons** |
| Gen 5 | 2.04B positions available: graded games, Leela T80, Lichess and fishnet evaluations, and self-play | h2048 primary run in progress; frozen-holdout audit passed (2,042,685,943 training positions, 0 malformed, 201,517 eval positions unseen); h4096 deferred until the quota covers a full run. Not promoted; no match result yet. |

Gen 1 and Gen 2 were tested with 400 games at 5,000 nodes per move. From Gen 3 on, every candidate plays
the previous generation with a fixed time per move instead, so a bigger, slower network has to earn its
size. Either way, take the exact numbers with a grain of salt.
For reference, Stockfish 19 is about 3650 on CCRL. If Nexarch ever gets close, I'll submit it to CCRL
so it gets tested properly, instead of me just saying it's strong.

## Plan

Gen 5 is the current experiment: one h2048 candidate trained on 2.04B positions. h4096 only starts after
the GPU quota can cover a complete run with its checkpoints, and never while the h2048 candidate is still
running.

Training finishing is not the same as Gen 5 being done. A candidate is called Gen 5 only after it clears
all of these:

- the frozen-holdout audit finds no training positions in the evaluation set;
- it beats Gen 4 in 400 timed games by a gain in line with the earlier generations (roughly +200 Elo or
  more), with the 95% interval clearly above zero;
- the 33-engine panel and Lc0 show the same gain, not just one lucky opponent.

If it misses that bar, the next step is more or better training for the same generation, not Gen 6
self-play. Gen 6 only starts after Gen 5 has been verified and published.

## Building

You need a compiler with C++20.

```
cd engine
make                     # optimized for your CPU
make ARCH=x86-64-v3      # works on any CPU with AVX2
```

On Windows you can use `engine/build.ps1`, which builds with MSVC.

## Playing against it

It's a UCI engine, so you can load it into Cute Chess, Arena, BanksiaGUI or any other chess GUI.

Options:

- `Hash`: hash table size in MB
- `Move Overhead`: how many milliseconds it keeps as a safety margin each move
- `EvalFile`: which `.nnue` network to use (`material` turns the network off)

The newest promoted network is `nets/nexarch-g4.nnue`.

There are also some extra commands I use while working on it:

```
./nexarch perftsuite [deep]     # checks move generation on six tricky positions
./nexarch bench 12              # speed test
./nexarch datagen threads=8 nodes=5000 seconds=3600 net=nets/nexarch-g4.nnue out=data.bin
./nexarch match a=new.nnue b=old.nnue games=400 nodes=5000 threads=8
```

## Training a network yourself

```
pip install numpy torch chess
./engine/nexarch datagen threads=8 nodes=5000 seconds=3600 net=nets/nexarch-g4.nnue out=data/selfplay.bin
python tools/grade.py --config nets/graders.json --data data/selfplay.bin --out data/graded.bin --workers 2
python trainer/train.py --data data/graded.bin --out nets/my-net.nnue --hidden 128 --epochs 40
./engine/nexarch match a=nets/my-net.nnue b=nets/nexarch-g4.nnue games=400 nodes=5000 threads=8
```

Grading takes the longest. Every worker runs around 30 engines at once and uses about 3 GB of RAM, so
don't start too many. I do most of the heavy stuff on Kaggle, and the scripts for that are in
`kaggle/`.

## Credits

A lot of other people's work goes into Nexarch: the 33 engines and networks that grade its training data,
Leela Chess Zero's public training data, the Lichess evaluation database, Stockfish's data tools, and the
libraries and free computers it all runs on. [CREDITS.md](CREDITS.md) lists every one of them.

From Gen 4 on, Nexarch's networks contain information from the Leela Chess Zero training data, which is made
available under the [ODbL v1.0](https://opendatacommons.org/licenses/odbl/1-0/).

## License

MIT, see [LICENSE](LICENSE).

The only exception is `tools/lc0_batch_grade.py`. It loads Lc0's Python module, which is GPL-3.0, so
that file is GPL-3.0 too.
