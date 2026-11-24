# Building Cute Chess from source

The Cute Chess source is in `gui/cutechess-source/` (v1.5.1 tag).

## Linux

```bash
sudo apt install qt6-base-dev qt6-svg-dev qt6-tools-dev cmake ninja-build
cd gui/cutechess-source
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
# binary: build/cutechess
# cli: build/cutechess-cli
```

## Windows

Install Qt 6.8+ and Visual Studio 2022, then:

```cmd
cd gui\cutechess-source
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -G "Ninja" -DCMAKE_PREFIX_PATH="C:\Qt\6.8.0\msvc2022_64"
cmake --build build --config Release
```

## macOS

```bash
brew install qt6 cmake ninja
cd gui/cutechess-source
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

The built AppImage for Linux uses `linuxdeployqt`. The Windows installer uses NSIS.
