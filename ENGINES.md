# Grading engines

Nexarch's training data is graded by other engines. They run as separate programs and Nexarch talks to
them over UCI. None of them are included in this repository, because most are GPL or AGPL licensed.
Download them from their own projects.

The roles come from what each engine is known for, using the CCRL rating lists, Stefan Pohl's EAS
aggressiveness list and the engines' own documentation. The config is `nets/graders.json`, and every
role has a `why` field.

| Role | Engine | License | Project |
|---|---|---|---|
| referee (every position) | Stockfish 19 | GPL-3.0 | https://github.com/official-stockfish/Stockfish |
| accuracy | Reckless 0.9.0 | AGPL-3.0 | https://github.com/codedeliveryservice/Reckless |
| accuracy | Triumviratus 8.0 | GPL-3.0 | https://github.com/Tors3/Triumviratus |
| tactics | Berserk 14 | GPL-3.0 | https://github.com/jhonnold/berserk |
| tactics | Stormphrax 8.0.0 | GPL-3.0 | https://github.com/Ciekce/Stormphrax |
| tactics | Obsidian 16.0 | GPL-3.0 | https://github.com/gab8192/Obsidian |
| sacrifices | ShashChess 42.3 (Middle Tal) | GPL-3.0 | https://github.com/amchess/ShashChess |
| sacrifices | Cinder 0.6.1 | GPL-3.0 | https://github.com/brunocodutra/cinder |
| sacrifices | Tarnished 6.0 | GPL-3.0 | https://github.com/Bobingstern/Tarnished |
| sacrifices | Quanticade Cronus 3.0 | GPL-3.0 | https://github.com/Quanticade/Quanticade |
| attack | ShashChess 42.3 (High Tal) | GPL-3.0 | https://github.com/amchess/ShashChess |
| attack | Arasan 26.1 | see project | https://github.com/jdart1/arasan-chess |
| attack | Raphael 4.2.0 | AGPL-3.0 | https://github.com/Orbital-Web/Raphael |
| defence | ShashChess 42.3 (High Petrosian) | GPL-3.0 | https://github.com/amchess/ShashChess |
| defence | Hobbes 3.0 | MIT | https://github.com/kelseyde/hobbes-chess-engine |
| defence | Viridithas 20.0.0 | AGPL-3.0 | https://github.com/cosmobobak/viridithas |
| defence | Halogen 16 | GPL-3.0 | https://github.com/KierenP/Halogen |
| endgames | Integral v8 | not stated on GitHub | https://github.com/aronpetko/integral |
| endgames | Caissa 2.0 | MIT | https://github.com/Witek902/Caissa |
| endgames | Seer 2.8.0 | GPL-3.0 | https://github.com/connormcmonigle/seer-nnue |
| positional | pawnocchio 2.0.1 | GPL-3.0 | https://github.com/JonathanHallstrom/pawnocchio |
| positional | Astra 7.0 | GPL-3.0 | https://github.com/h1me01/Astra |
| positional | Devre 7.0 | GPL-3.0 | https://github.com/OmerFarukTutkun/Devre |
| positional | Clover 9.1 | GPL-3.0 | https://github.com/lucametehau/CloverEngine |
| openings | Renegade 1.3.1 | MIT | https://github.com/pkrisz99/Renegade |
| openings | PZChessBot 7.1 | AGPL-3.0 | https://github.com/kevlu8/PZChessBot |
| human-like moves | Maia 1900 (runs in Lc0) | GPL-3.0 | https://github.com/CSSLab/maia-chess |
| second opinion | PlentyChess 8.0.0 | GPL-3.0 | https://github.com/Yoshie2000/PlentyChess |
| second opinion | Coda 0.9.4 | GPL-3.0 | https://github.com/adamtwiss/coda |
| second opinion | Alexandria 9.1.0 | GPL-3.0 | https://github.com/PGG106/Alexandria |
| veteran | RubiChess 20240817 | GPL-3.0 | https://github.com/Matthies/RubiChess |
| veteran | Koivisto 9.0 | GPL-3.0 | https://github.com/Luecx/Koivisto |
| veteran | Ethereal 14.40 (free build, classical eval) | GPL-3.0 | https://github.com/AndyGrant/Ethereal |
| GPU, positional (network only) | Lc0 0.32.1 + BT4 network | GPL-3.0 | https://github.com/LeelaChessZero/lc0 |

Engines I wanted but couldn't use: Gaia (no public release), Torch (Chess.com, closed), Dragon by Komodo,
Houdini, Fritz, Shredder and HIARCS (commercial), and AlphaZero and Deep Blue, which were never released.
