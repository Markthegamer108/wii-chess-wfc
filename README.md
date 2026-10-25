# Wii Chess WFC

Got a Wii Chess PAL (`RTYP01`) image? This rebuilds it as a WBFS pointed at `158.180.55.245`. It changes `DATA/sys/main.dol`; your input stays put.

## What it changes

`main.dol` has 22 Nintendo WFC service addresses and six WiiConnect24 `naswii` URLs. The tool points them at `158.180.55.245`; the URLs become `http://158.180.55.245/ac` or `http://158.180.55.245/pr`. The patched file stays the same size. The server is fixed.

If the fields are missing, duplicated, or don't match the format it expects, the tool stops. It won't guess at a different DOL layout.

## Run it

Install [Wiimms ISO Tools](https://wit.wiimm.de/) for `wit.exe`. For `.rvz` images, you'll also need `DolphinTool.exe` from Dolphin. If either tool isn't found, the program asks you to select it. You can also set `WIT_EXE` or `DOLPHIN_TOOL_EXE`.

On Windows, double-click `Run WFC Modder.bat`. It runs `WFC Modder.exe` if you've built it; otherwise it starts the Python script. You can also run `py -3 wfc_modder.py`.

Choose a `.rvz`, `.iso`, or `.wbfs` input and a new `.wbfs` output. The server is always `158.180.55.245`. Type `BUILD` to start.

`.rvz` files are converted to a temporary ISO first, which needs about 5 GB of free space. The input image is never overwritten, and the tool won't overwrite an existing output file.

## What gets checked

The tool checks the game ID, extracts the image, patches `main.dol`, and builds a WBFS. It extracts the result again to check the patched file and compare the other DATA and UPDATE game files. It also checks that the source image hasn't changed.

WIT rebuilds the WBFS and its metadata, so the output won't match the input byte for byte.

## Build and test

To build `WFC Modder.exe`, install Python 3 and PyInstaller, then run `Build EXE.bat`.

Run the tests with:

```sh
py -3 -m unittest discover -s tests -v
```
