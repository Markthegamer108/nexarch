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
| Gen 3 | Gen 2's games (33.5M positions), scored by the whole panel and Lc0 | training now: four sizes, up to 2048 neurons |
| Gen 4 | Gen 2's and Gen 3's games, plus Leela's public training data | getting the data ready |

Gen 1 and Gen 2 were tested with 400 games at 5,000 nodes per move. From Gen 3 on, every candidate plays
the previous generation with a fixed time per move instead, so a bigger, slower network has to earn its
size. Either way, take the exact numbers with a grain of salt.
For reference, Stockfish 19 is about 3650 on CCRL. If Nexarch ever gets close, I'll submit it to CCRL
so it gets tested properly, instead of me just saying it's strong.

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

The newest network is `nets/nexarch-g2.nnue`.

There are also some extra commands I use while working on it:

```
./nexarch perftsuite [deep]     # checks move generation on six tricky positions
./nexarch bench 12              # speed test
./nexarch datagen threads=8 nodes=5000 seconds=3600 net=nets/nexarch-g2.nnue out=data.bin
./nexarch match a=new.nnue b=old.nnue games=400 nodes=5000 threads=8
```

## Training a network yourself

```
pip install numpy torch chess
./engine/nexarch datagen threads=8 nodes=5000 seconds=3600 net=nets/nexarch-g2.nnue out=data/selfplay.bin
python tools/grade.py --config nets/graders.json --data data/selfplay.bin --out data/graded.bin --workers 2
python trainer/train.py --data data/graded.bin --out nets/my-net.nnue --hidden 128 --epochs 40
./engine/nexarch match a=nets/my-net.nnue b=nets/nexarch-g2.nnue games=400 nodes=5000 threads=8
```

Grading takes the longest. Every worker runs around 30 engines at once and uses about 3 GB of RAM, so
don't start too many. I do most of the heavy stuff on Kaggle, and the scripts for that are in
`kaggle/`.

## Credits

A lot of other people's work goes into Nexarch: the 32 engines and networks that grade its training data,
Leela Chess Zero's public training data, the Lichess evaluation database, Stockfish's data tools, and the
libraries and free computers it all runs on. [CREDITS.md](CREDITS.md) lists every one of them.

From Gen 4 on, Nexarch's networks contain information from the Leela Chess Zero training data, which is made
available under the [ODbL v1.0](https://opendatacommons.org/licenses/odbl/1-0/).

## License

MIT, see [LICENSE](LICENSE).

The only exception is `tools/lc0_batch_grade.py`. It loads Lc0's Python module, which is GPL-3.0, so
that file is GPL-3.0 too.
