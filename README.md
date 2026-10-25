# Wii Chess WFC Modder

This is a small converter for Wii Chess Europe. It takes a game image you already have and rebuilds it as a new WBFS with the WFC patch applied. It does not include a game image or overwrite the input.

The project only supports the Europe release (`RTYP01`) with stock `main.dol` SHA-256 `04292ff831f2e699be0edee09010a89bf62bc39250e595485d21385c3ca82d43`.

## Before you run it

- Use your own Wii Chess Europe image in `.rvz`, `.iso`, or `.wbfs` format.
- Install Wiimms ISO Tools (WIT). RVZ files also need Dolphin's `DolphinTool.exe`.
- Obtain an authorized copy of `wii_chess_europe.ips` separately and put it in `patches\wii_chess_europe.ips`. The patch is intentionally not included here because it contains replacement game code. Its SHA-256 must be `42791c7093e26943b1e02c436c891acb78e2722133725de2fc5857f7182e927a`. See [patches/README.md](patches/README.md).

Without that patch file, the app stops with an error before processing an image. This repository by itself is not enough to make a converted game.

## Run it

On Windows, double-click `Run WFC Modder.bat`, or run:

```text
py -3 wfc_modder.py
```

Choose the input image, a new output filename, and the WIT/DolphinTool executables when asked. The output is a newly rebuilt WBFS; it will not be byte-for-byte identical to the input container. The tool checks the game ID and stock executable hash and verifies the rebuilt files. Only `DATA/sys/main.dol` is patched; the source image is left alone.

The default server is `158.180.55.245`. A custom IPv4 address must be 14 characters long; shorter or longer addresses are rejected.

## Build and tests

Install Python 3 and PyInstaller:

```text
py -3 -m pip install pyinstaller
```

With the separately obtained patch file in place, run `Build EXE.bat`. The generated executable is for your own use and is not part of this repository.

Run the tests with:

```text
py -3 -m unittest discover -s tests -v
```

The optional integration test needs stock and patched DOL files from your own copy of the game. Set `WII_CHESS_TEST_STOCK_DOL` and `WII_CHESS_TEST_PATCHED_DOL` to their paths before running the test suite.
