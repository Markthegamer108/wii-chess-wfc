#!/usr/bin/env python3
"""Build a Wii Chess Europe WFC WBFS from a verified user-owned image."""

from __future__ import annotations

import ctypes
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


GAME_ID = "RTYP01"
DEFAULT_SERVER = "158.180.55.245"
SERVICE_STRING_COUNT = 22
NAS_URL_COUNT = 6
NAS_URL_PATTERN = re.compile(
    rb"https://naswii(?:\.test|\.dev)?\.nintendowifi\.net/(?:ac|pr)",
    re.IGNORECASE,
)


class ModderError(Exception):
    """A source image, executable, tool, or output failed validation."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_endpoint(endpoint: str) -> bytes:
    if endpoint.strip() != DEFAULT_SERVER:
        raise ModderError(f"This modder always uses {DEFAULT_SERVER}.")
    return DEFAULT_SERVER.encode("ascii")


def find_network_strings(
    dol: bytes,
) -> tuple[list[tuple[int, bytes]], list[tuple[int, bytes]]]:
    strings = [
        (match.start(), match.group()[:-1])
        for match in re.finditer(rb"[\x20-\x7e]+\x00", dol)
    ]
    service_strings = [
        (offset, value)
        for offset, value in strings
        if b".gs.nintendowifi.net" in value.lower()
    ]
    network_urls = [
        (offset, value)
        for offset, value in strings
        if b"https://" in value.lower() and b"nintendowifi.net" in value.lower()
    ]
    if len(service_strings) != SERVICE_STRING_COUNT:
        raise ModderError(
            f"Expected {SERVICE_STRING_COUNT} recognizable service fields; "
            f"found {len(service_strings)}. This executable revision is not verified."
        )
    if len(network_urls) != NAS_URL_COUNT:
        raise ModderError(
            f"Expected {NAS_URL_COUNT} recognizable WiiConnect24 URL fields; "
            f"found {len(network_urls)}. This executable revision is not verified."
        )
    if any(NAS_URL_PATTERN.fullmatch(value) is None for _, value in network_urls):
        raise ModderError(
            "A WiiConnect24 URL has an unrecognized format. "
            "This executable revision is not verified."
        )
    if len({value.lower() for _, value in network_urls}) != NAS_URL_COUNT:
        raise ModderError(
            "WiiConnect24 URL fields are duplicated or ambiguous. "
            "This executable revision is not verified."
        )
    return service_strings, network_urls


def rewrite_server_fields(stock_dol: bytes, endpoint: str) -> bytes:
    endpoint_bytes = validate_endpoint(endpoint)
    service_strings, network_urls = find_network_strings(stock_dol)
    replacements = [
        (offset, value, endpoint_bytes)
        for offset, value in service_strings
    ]
    replacements.extend(
        (offset, value, b"http://" + endpoint_bytes + b"/" + value.rsplit(b"/", 1)[1])
        for offset, value in network_urls
    )
    output = bytearray(stock_dol)
    for offset, original, replacement in replacements:
        if len(replacement) > len(original):
            raise ModderError("A replacement endpoint does not fit its executable field.")
        output[offset:offset + len(original)] = replacement + b"\x00" * (
            len(original) - len(replacement)
        )
    result = bytes(output)
    for offset, _, replacement in replacements:
        if result[offset:offset + len(replacement)] != replacement:
            raise ModderError("Endpoint replacement verification failed.")
    if len(result) != len(stock_dol):
        raise ModderError("Internal error: patched DOL size changed.")
    return result


def make_endpoint_dol(stock_dol: bytes, endpoint: str) -> bytes:
    return rewrite_server_fields(stock_dol, endpoint)


def run_tool(executable: Path, args: list[str], label: str) -> str:
    if not executable.is_file():
        raise ModderError(f"{label} executable not found: {executable}")
    try:
        completed = subprocess.run(
            [str(executable), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise ModderError(f"Could not start {label}: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        if len(detail) > 2400:
            detail = detail[-2400:]
        raise ModderError(
            f"{label} failed with exit code {completed.returncode}."
            + (f"\n{detail}" if detail else "")
        )
    return completed.stdout.strip()


def tool_path(path: Path) -> str:
    """Return a path usable by WIT's Windows/Cygwin command-line parser."""
    text = str(path)
    if " " not in text:
        return text
    if not path.exists():
        return str(Path(tool_path(path.parent)) / path.name)
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetShortPathNameW(text, buffer, len(buffer))
    if not length or length >= len(buffer) or " " in buffer.value:
        raise ModderError(
            f"Could not make a space-free path for WIT: {path}. "
            "Choose a temporary folder on a drive with 8.3 short paths enabled."
        )
    return buffer.value


def get_game_id(wit: Path, image: Path) -> str:
    output = run_tool(wit, ["ID6", tool_path(image)], "WIT ID check")
    ids = [line.strip() for line in output.splitlines() if line.strip()]
    if GAME_ID not in ids:
        raise ModderError(
            f"Unsupported game image. Expected Wii Chess Europe ({GAME_ID}); "
            f"WIT reported: {', '.join(ids) or '(no game ID)'}."
        )
    return GAME_ID


def compare_game_files(original_root: Path, output_root: Path) -> tuple[int, int]:
    """Compare extracted game files; WIT's partition packaging metadata is regenerated."""
    checked = 0
    for partition in ("DATA", "UPDATE"):
        original = original_root / partition
        rebuilt = output_root / partition
        if not original.exists() and not rebuilt.exists():
            continue
        if original.exists() != rebuilt.exists():
            raise ModderError(f"Rebuilt image changed the {partition} partition presence.")
        original_files = {
            path.relative_to(original).as_posix(): path
            for path in original.rglob("*")
            if path.is_file()
            and path.relative_to(original).parts[0].lower() in {"files", "sys", "disc"}
        }
        rebuilt_files = {
            path.relative_to(rebuilt).as_posix(): path
            for path in rebuilt.rglob("*")
            if path.is_file()
            and path.relative_to(rebuilt).parts[0].lower() in {"files", "sys", "disc"}
        }
        if original_files.keys() != rebuilt_files.keys():
            missing = sorted(original_files.keys() - rebuilt_files.keys())
            extra = sorted(rebuilt_files.keys() - original_files.keys())
            raise ModderError(
                f"Rebuilt {partition} file list differs. "
                f"Missing: {missing[:5]}; extra: {extra[:5]}."
            )
        for relative, source_file in original_files.items():
            output_file = rebuilt_files[relative]
            if source_file.stat().st_size != output_file.stat().st_size:
                raise ModderError(f"Rebuilt game file size differs: {partition}/{relative}")
            normalized = relative.lower()
            if partition == "DATA" and normalized == "sys/main.dol":
                continue
            if normalized in {"sys/fst.bin", "disc/region.bin"}:
                continue
            if sha256_file(source_file) != sha256_file(output_file):
                raise ModderError(f"Rebuilt game file content differs: {partition}/{relative}")
            checked += 1
    return checked, 1


def make_wbfs(
    source_image: Path,
    destination: Path,
    wit: Path,
    dolphin_tool: Path | None,
    endpoint: str,
    progress=print,
) -> dict[str, str | int]:
    source = source_image.resolve(strict=True)
    destination = destination.resolve()
    if not source.is_file():
        raise ModderError("Selected input is not a regular file.")
    if source.suffix.lower() not in {".rvz", ".iso", ".wbfs"}:
        raise ModderError("Choose a Wii Chess .rvz, .iso, or .wbfs image.")
    if source == destination:
        raise ModderError("Output path must differ from the source image.")
    if destination.suffix.lower() != ".wbfs":
        raise ModderError("Output filename must end in .wbfs.")
    if destination.exists():
        raise ModderError("Output already exists; choose a new filename to avoid overwriting.")
    if not wit.is_file():
        raise ModderError("Select a valid wit.exe from the Wiimms ISO Tools installation.")
    if source.suffix.lower() == ".rvz" and (dolphin_tool is None or not dolphin_tool.is_file()):
        raise ModderError("RVZ input requires DolphinTool.exe. Select it or use ISO/WBFS input.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="WiiChessWFC-"))
    temporary_output = destination.with_name(f".{destination.stem}.{uuid.uuid4().hex}.tmp.wbfs")
    source_digest = sha256_file(source)
    try:
        staged_input = work / f"source{source.suffix.lower()}"
        try:
            os.link(source, staged_input)
        except OSError:
            shutil.copy2(source, staged_input)
        current_image = staged_input
        if source.suffix.lower() == ".rvz":
            progress("Converting RVZ to a temporary ISO with DolphinTool...")
            current_image = work / "input.iso"
            run_tool(
                dolphin_tool,  # type: ignore[arg-type]
                [
                    "convert",
                    "-i",
                    tool_path(staged_input),
                    "-o",
                    tool_path(current_image),
                    "-f",
                    "iso",
                ],
                "DolphinTool RVZ conversion",
            )
            if not current_image.is_file():
                raise ModderError("DolphinTool reported success but did not create the temporary ISO.")

        progress("Checking game identity with WIT...")
        get_game_id(wit, current_image)

        progress("Extracting the Wii image to a private temporary workspace...")
        extracted = work / "disc"
        run_tool(
            wit,
            ["EXTRACT", tool_path(current_image), "-d", tool_path(extracted)],
            "WIT extraction",
        )
        stock_dol_path = extracted / "DATA" / "sys" / "main.dol"
        if not stock_dol_path.is_file():
            raise ModderError("Image extraction did not produce DATA/sys/main.dol.")
        stock_dol = stock_dol_path.read_bytes()
        stock_digest = hashlib.sha256(stock_dol).hexdigest()

        progress(f"Finding WFC server fields and applying {endpoint}...")
        patched_dol = make_endpoint_dol(stock_dol, endpoint)
        stock_dol_path.write_bytes(patched_dol)

        progress("Composing a new WBFS image with WIT...")
        working_output = work / "output.wbfs"
        run_tool(
            wit,
            ["COPY", tool_path(extracted), tool_path(working_output), "--wbfs"],
            "WIT WBFS composition",
        )
        if not working_output.is_file() or working_output.stat().st_size == 0:
            raise ModderError("WIT did not create a non-empty WBFS output.")
        progress("Re-extracting the WBFS and comparing all game files...")
        rebuilt = work / "rebuilt"
        run_tool(
            wit,
            ["EXTRACT", tool_path(working_output), "-d", tool_path(rebuilt)],
            "WIT output verification",
        )
        compared, patched_count = compare_game_files(extracted, rebuilt)
        rebuilt_dol_path = rebuilt / "DATA" / "sys" / "main.dol"
        if sha256_file(rebuilt_dol_path) != hashlib.sha256(patched_dol).hexdigest():
            raise ModderError("Rebuilt WBFS main.dol does not match the requested patched executable.")
        if sha256_file(source) != source_digest:
            raise ModderError("Source image changed during processing; refusing to publish output.")

        try:
            os.link(working_output, destination)
        except FileExistsError as exc:
            raise ModderError("Output appeared during processing; refusing to overwrite it.") from exc
        except OSError:
            try:
                shutil.copyfile(working_output, temporary_output)
                os.link(temporary_output, destination)
            except FileExistsError as exc:
                raise ModderError("Output appeared during processing; refusing to overwrite it.") from exc
            finally:
                temporary_output.unlink(missing_ok=True)
        return {
            "source_sha256": source_digest,
            "output_sha256": sha256_file(destination),
            "source_dol_sha256": stock_digest,
            "output_dol_sha256": sha256_file(rebuilt_dol_path),
            "endpoint": endpoint,
            "other_files_verified": compared,
            "patched_files": patched_count,
            "output_size": destination.stat().st_size,
        }
    finally:
        temporary_output.unlink(missing_ok=True)
        shutil.rmtree(work, ignore_errors=True)


def browse_file(title: str, patterns: list[tuple[str, str]], save: bool = False) -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            if save:
                selected = filedialog.asksaveasfilename(
                    title=title,
                    filetypes=patterns,
                    defaultextension=".wbfs",
                )
            else:
                selected = filedialog.askopenfilename(title=title, filetypes=patterns)
        finally:
            root.destroy()
        return Path(selected) if selected else None
    except ImportError:
        return None


def ask_file(title: str, patterns: list[tuple[str, str]], prompt: str, save: bool = False) -> Path | None:
    selected = browse_file(title, patterns, save=save)
    if selected is not None:
        return selected
    typed = input(f"{prompt} (blank to cancel): ").strip().strip('"')
    return Path(typed) if typed else None


def find_tool(name: str) -> Path | None:
    env_name = "DOLPHIN_TOOL_EXE" if name == "DolphinTool.exe" else "WIT_EXE"
    configured = os.environ.get(env_name)
    if configured and Path(configured).is_file():
        return Path(configured)
    candidates = [
        Path(__file__).parent / "tools" / name,
        Path(r"C:\Program Files\Wiimm\WIT\bin") / name,
        Path(r"C:\Program Files\Dolphin") / name,
    ]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def select_tool(name: str, label: str) -> Path | None:
    detected = find_tool(name)
    if detected:
        answer = input(f"{label} detected at {detected}\nPress Enter to use it, or type another path: ").strip().strip('"')
        if not answer:
            return detected
        candidate = Path(answer)
    else:
        print(f"{label} was not found. Select its executable.")
        candidate = ask_file(
            f"Select {label}",
            [("Windows executable", "*.exe"), ("All files", "*.*")],
            f"Path to {name}",
        )
        if candidate is None:
            return None
    return candidate.resolve() if candidate.is_file() else None


def run_ui() -> int:
    print("=" * 66)
    print("  Wii Chess WFC Converter")
    print("=" * 66)
    print("For Wii Chess Europe (RTYP01). Server fields are detected by content.")
    print("RVZ needs DolphinTool; ISO and WBFS can be processed with WIT.")
    print("The source is never overwritten. A new WBFS container is rebuilt.")
    print("Unknown or ambiguous executable layouts are rejected without patching.")
    print(f"WFC endpoint (fixed): {DEFAULT_SERVER}")
    print()

    source = ask_file(
        "Choose your Wii Chess Europe image",
        [("Wii disc images", "*.rvz *.iso *.wbfs"), ("All files", "*.*")],
        "Path to the original Wii Chess .rvz, .iso, or .wbfs",
    )
    if source is None:
        print("Cancelled.")
        return 0
    if not source.is_file():
        print("Input file does not exist.")
        return 1
    default_output = source.with_name(f"{source.stem}.WFC-modded.wbfs")
    destination = browse_file(
        "Choose a new output WBFS filename",
        [("WBFS image", "*.wbfs")],
        save=True,
    )
    if destination is None:
        text = input(f"Output WBFS path [{default_output}]: ").strip().strip('"')
        destination = Path(text) if text else default_output

    endpoint = DEFAULT_SERVER

    wit = select_tool("wit.exe", "Wiimms ISO Tool (WIT)")
    if wit is None:
        print("WIT is required. Install Wiimms ISO Tools or choose its wit.exe.")
        return 1
    dolphin = None
    if source.suffix.lower() == ".rvz":
        dolphin = select_tool("DolphinTool.exe", "DolphinTool")
        if dolphin is None:
            print("RVZ input requires DolphinTool.exe. Use an ISO/WBFS or choose DolphinTool.")
            return 1

    print(f"\nInput:  {source.resolve()}")
    print(f"Output: {destination.resolve()}")
    print(f"Server: {endpoint} (fixed)")
    print("RVZ conversion requires about 5 GB of temporary disk space.")
    if input("Type BUILD to start: ").strip() != "BUILD":
        print("Cancelled.")
        return 0
    try:
        result = make_wbfs(source, destination, wit, dolphin, endpoint)
    except (OSError, ModderError) as exc:
        print(f"\nBuild failed: {exc}")
        return 1

    print("\nNew WFC WBFS built and verified.")
    print(f"Output: {destination.resolve()}")
    print(f"Size: {result['output_size']:,} bytes")
    print(f"Server endpoint: {result['endpoint']}")
    print(f"Original image SHA-256 (unchanged): {result['source_sha256']}")
    print(f"Output WBFS SHA-256: {result['output_sha256']}")
    print(f"Stock DOL SHA-256: {result['source_dol_sha256']}")
    print(f"Patched DOL SHA-256: {result['output_dol_sha256']}")
    print(
        f"Verified {result['other_files_verified']} other DATA/UPDATE game files unchanged; "
        "main.dol was patched and WIT regenerated h3/setup/ticket/TMD, disc/region.bin, "
        "and sys/fst.bin metadata."
    )
    print("The rebuilt WBFS container is not byte-identical to the source image.")
    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
            validate_endpoint(DEFAULT_SERVER)
            print("Wii Chess WFC Converter self-test passed.")
            sys.exit(0)
        sys.exit(run_ui())
    except (OSError, ModderError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(0)
