# Wii Chess WFC

Point a Wii Chess Europe game at a different WFC server. Pick an `.rvz`, `.iso`, or `.wbfs` and the tool rebuilds it as a new `.wbfs`. Your original image stays put.

## Quick start

Install [Wiimms ISO Tools](https://wit.wiimm.de/). `.rvz` files need Dolphin's `DolphinTool.exe` too.

On Windows, double-click `Run WFC Modder.bat`. Or run `py -3 wfc_modder.py`. Choose your input and a new output file, then enter a server address when asked. Press Enter to use `158.180.55.245`.

The converter checks the game's `main.dol` before changing anything. If it can't find the fields it expects, it stops instead of guessing.

## Compatibility

Wii Chess Europe (`RTYP01`) only. Other releases or layouts may not work. Custom server addresses need to be 14-character IPv4 addresses.

## Build and test

To build the Windows executable, install Python 3 and PyInstaller, then run `Build EXE.bat`.

Run the tests with:

```sh
py -3 -m unittest discover -s tests -v
```
