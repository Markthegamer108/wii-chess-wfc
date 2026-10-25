# Wii Chess WFC

Turn a Wii Chess Europe image into a new WBFS that connects to the WFC server you choose. The tool changes `DATA/sys/main.dol` inside the image; your original file stays untouched.

## What it changes

It finds 22 Nintendo WFC service addresses and six WiiConnect24 `naswii` URLs in `main.dol`. It points the service addresses at your server and changes the URLs to `http://<server>/ac` or `http://<server>/pr`. The patched `main.dol` stays the same size.

The tool checks the fields before it changes anything. If they're missing, duplicated, or in a format it doesn't recognize, it stops instead of guessing. It only accepts Wii Chess Europe (`RTYP01`).

## Run it

Install [Wiimms ISO Tools](https://wit.wiimm.de/) for `wit.exe`. For `.rvz` images, you'll also need `DolphinTool.exe` from Dolphin. If either tool isn't found, the program asks you to select it. You can also set `WIT_EXE` or `DOLPHIN_TOOL_EXE`.

On Windows, double-click `Run WFC Modder.bat`. It runs `WFC Modder.exe` if you've built it; otherwise it starts the Python script. You can also run `py -3 wfc_modder.py`.

Choose a `.rvz`, `.iso`, or `.wbfs` input, then choose a new `.wbfs` output. Enter a server IPv4 address or press Enter for `158.180.55.245`. The address must be valid and 14 characters long so it fits the game's fields. Type `BUILD` to start.

`.rvz` files are converted to a temporary ISO first, which needs about 5 GB of free space. The input image is never overwritten, and the tool won't overwrite an existing output file.

## What gets checked

The tool checks the game ID, extracts the image, patches `main.dol`, and builds a new WBFS. It then extracts that WBFS again, verifies the patched `main.dol`, and compares the other game files in the DATA and UPDATE partitions. It also checks that the source image hasn't changed.

WIT rebuilds the WBFS container and regenerates its metadata, so the output won't be byte-for-byte identical to the input.

## Build and test

To build `WFC Modder.exe`, install Python 3 and PyInstaller, then run `Build EXE.bat`.

Run the tests with:

```sh
py -3 -m unittest discover -s tests -v
```
