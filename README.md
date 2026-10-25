# Wii Chess WFC

Convert a Wii Chess Europe image you already have into a new WBFS with the
WFC server fields changed. The source image is never overwritten. The
rebuilt WBFS is a new container and is not byte-for-byte identical to the
input.

## Quick start

1. Install [Wiimms ISO Tools](https://wit.wiimm.de/) (WIT). `.rvz` input also
   requires Dolphin's `DolphinTool.exe`.
2. Run `Run WFC Modder.bat` on Windows, or run `py -3 wfc_modder.py`.
3. Choose your `.rvz`, `.iso`, or `.wbfs` input, then choose a new `.wbfs`
   output. Select WIT/DolphinTool if they are not detected automatically.
   Press Enter at the server prompt to use `158.180.55.245`.

No separate IPS patch file is needed. The converter scans the extracted
`main.dol` for the expected Nintendo WFC service strings and WiiConnect24 URLs,
then replaces those fields in place. It requires 22 service-string fields and
six distinct URLs in the recognized format. Missing, duplicated, or
unrecognized fields stop conversion before an output is created.

## Compatibility

The image must be Wii Chess Europe (`RTYP01`). The content scanner was
validated against one local Europe sample; its default-server output exactly
matches the previously verified patched DOL. This does not establish support
for every Europe revision. Different executable layouts may be rejected; the
converter fails closed rather than guessing offsets.

A custom server must be a valid 14-character IPv4 address so it fits in the
detected fields without shifting the URL paths.

## Build and tests

Install Python 3 and PyInstaller, then run `Build EXE.bat`. The generated
executable is for your own use and is not included in this repository.

Run tests with:

```text
py -3 -m unittest discover -s tests -v
```

The optional sample integration test uses a local Europe `main.dol` when
`WII_CHESS_TEST_STOCK_DOL` is set to its path. No game files are needed for
the unit tests.
