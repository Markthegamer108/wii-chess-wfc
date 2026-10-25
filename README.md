# Wii Chess WFC

Convert a Wii Chess Europe image (RTYP01) into a new WBFS configured for a WFC server. Your original image is never changed.

## Use it

1. Install [Wiimms ISO Tools](https://wit.wiimm.de/). For `.rvz` files, install Dolphin and use `DolphinTool.exe`.
2. On Windows, run `Run WFC Modder.bat`. Or run `py -3 wfc_modder.py`.
3. Choose an `.rvz`, `.iso`, or `.wbfs` input and a new `.wbfs` output. Press Enter to use the default server, `158.180.55.245`.

## Requirements

- Wii Chess Europe only. Other releases or unexpected file layouts are rejected.
- Python 3 to run from source. Install PyInstaller and run `Build EXE.bat` to build a Windows executable.

## Tests

```sh
py -3 -m unittest discover -s tests -v
```
