import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from wfc_modder import (
    DEFAULT_SERVER,
    ModderError,
    compare_game_files,
    make_endpoint_dol,
    rewrite_server_fields,
    tool_path,
    validate_endpoint,
)


class EndpointTests(unittest.TestCase):
    def test_accepts_fixed_server(self):
        self.assertEqual(validate_endpoint(DEFAULT_SERVER), b"158.180.55.245")

    def test_rejects_other_server_addresses(self):
        for endpoint in ("not-an-ip", "127.0.0.1", "203.111.22.233", "158.180.55.256"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ModderError):
                    validate_endpoint(endpoint)

    @staticmethod
    def make_sample_dol() -> bytes:
        services = [f"service-{index}.gs.nintendowifi.net".encode() for index in range(22)]
        urls = [
            f"https://naswii{environment}.nintendowifi.net/{route}".encode()
            for environment in ("", ".test", ".dev")
            for route in ("ac", "pr")
        ]
        return b"\x00".join(services + urls) + b"\x00"

    def test_rewrites_detected_service_and_url_fields_without_changing_size(self):
        dol = self.make_sample_dol()
        output = rewrite_server_fields(dol, DEFAULT_SERVER)
        self.assertEqual(len(output), len(dol))
        self.assertEqual(output.count(b"http://158.180.55.245/ac"), 3)
        self.assertEqual(output.count(b"http://158.180.55.245/pr"), 3)
        self.assertEqual(output.count(b"158.180.55.245"), 28)

    def test_rejects_missing_or_ambiguous_fields(self):
        valid = self.make_sample_dol()
        with self.assertRaisesRegex(ModderError, "Expected 22"):
            rewrite_server_fields(valid.replace(b"service-0.gs.nintendowifi.net", b"service-0.invalid"), DEFAULT_SERVER)
        with self.assertRaisesRegex(ModderError, "Expected 6"):
            rewrite_server_fields(
                valid.replace(
                    b"https://naswii.test.nintendowifi.net/pr\x00",
                    b"\x00",
                ),
                DEFAULT_SERVER,
            )

    def test_rejects_unrecognized_or_duplicate_wii_connect24_urls(self):
        valid = self.make_sample_dol()
        malformed = valid.replace(b"naswii.test", b"naswii.other", 1)
        with self.assertRaisesRegex(ModderError, "unrecognized format"):
            rewrite_server_fields(malformed, DEFAULT_SERVER)
        duplicate = valid.replace(b"naswii.test.nintendowifi.net/pr", b"naswii.nintendowifi.net/ac")
        with self.assertRaisesRegex(ModderError, "ambiguous"):
            rewrite_server_fields(duplicate, DEFAULT_SERVER)

    def test_rejects_unknown_dol_layout(self):
        with self.assertRaisesRegex(ModderError, "isn't supported"):
            make_endpoint_dol(b"not a Wii Chess DOL", DEFAULT_SERVER)


class FileComparisonTests(unittest.TestCase):
    def test_allows_only_main_dol_to_differ(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source"
            rebuilt = Path(folder) / "rebuilt"
            for root in (source, rebuilt):
                (root / "DATA" / "sys").mkdir(parents=True)
                (root / "DATA" / "disc").mkdir()
                (root / "DATA" / "files").mkdir(parents=True)
                (root / "DATA" / "sys" / "fst.bin").write_bytes(b"fst")
                (root / "DATA" / "disc" / "region.bin").write_bytes(b"region")
                (root / "DATA" / "setup.txt").write_bytes(b"generated")
                (root / "UPDATE").mkdir()
                (root / "UPDATE" / "sys").mkdir()
                (root / "UPDATE" / "disc").mkdir()
                (root / "UPDATE" / "sys" / "fst.bin").write_bytes(b"fst")
                (root / "UPDATE" / "disc" / "region.bin").write_bytes(b"region")
                (root / "UPDATE" / "setup.txt").write_bytes(b"generated")
            (source / "DATA" / "sys" / "main.dol").write_bytes(b"stock")
            (rebuilt / "DATA" / "sys" / "main.dol").write_bytes(b"patch")
            (rebuilt / "DATA" / "sys" / "fst.bin").write_bytes(b"new")
            (rebuilt / "DATA" / "disc" / "region.bin").write_bytes(b"change")
            (rebuilt / "DATA" / "setup.txt").write_bytes(b"recreated")
            (rebuilt / "UPDATE" / "sys" / "fst.bin").write_bytes(b"new")
            (rebuilt / "UPDATE" / "disc" / "region.bin").write_bytes(b"change")
            (rebuilt / "UPDATE" / "setup.txt").write_bytes(b"recreated")
            (source / "DATA" / "files" / "asset.bin").write_bytes(b"same")
            (rebuilt / "DATA" / "files" / "asset.bin").write_bytes(b"same")
            (source / "UPDATE" / "files").mkdir()
            (rebuilt / "UPDATE" / "files").mkdir()
            (source / "UPDATE" / "files" / "update.bin").write_bytes(b"update")
            (rebuilt / "UPDATE" / "files" / "update.bin").write_bytes(b"update")
            self.assertEqual(compare_game_files(source, rebuilt), (2, 1))

    def test_rejects_other_changed_game_files(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source"
            rebuilt = Path(folder) / "rebuilt"
            for root in (source, rebuilt):
                (root / "DATA" / "sys").mkdir(parents=True)
                (root / "DATA" / "files").mkdir(parents=True)
                (root / "DATA" / "h3.bin").write_bytes(b"derived hash tree")
            (source / "DATA" / "sys" / "main.dol").write_bytes(b"stock")
            (rebuilt / "DATA" / "sys" / "main.dol").write_bytes(b"patched")
            (rebuilt / "DATA" / "h3.bin").write_bytes(b"recomputed tree")
            (source / "DATA" / "files" / "asset.bin").write_bytes(b"source")
            (rebuilt / "DATA" / "files" / "asset.bin").write_bytes(b"change")
            with self.assertRaisesRegex(ModderError, "content differs"):
                compare_game_files(source, rebuilt)


class ToolPathTests(unittest.TestCase):
    def test_resolves_existing_and_future_paths_without_spaces(self):
        with tempfile.TemporaryDirectory(prefix="wfc test ") as folder:
            existing = Path(folder) / "tool.exe"
            existing.write_bytes(b"tool")
            resolved = Path(tool_path(existing))
            self.assertTrue(resolved.is_file())
            future = Path(tool_path(Path(folder) / "output.wbfs"))
            self.assertFalse(" " in str(future))


class LocalDOLIntegrationTests(unittest.TestCase):
    def test_known_europe_dol_generates_verified_default_patch(self):
        stock_path = os.environ.get("WII_CHESS_TEST_STOCK_DOL")
        if not stock_path:
            self.skipTest("Set WII_CHESS_TEST_STOCK_DOL to a local Europe main.dol to run.")
        stock = Path(stock_path).read_bytes()
        generated = make_endpoint_dol(stock, DEFAULT_SERVER)
        self.assertEqual(
            hashlib.sha256(generated).hexdigest(),
            "ce589b174b7258616402c1bf050b2e9b2f447967c6fc9ff53f13decae7e8c4d1",
        )


if __name__ == "__main__":
    unittest.main()
