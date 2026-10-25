import tempfile
import unittest
from pathlib import Path
import os

from wfc_modder import (
    DEFAULT_SERVER,
    ModderError,
    apply_ips,
    compare_game_files,
    make_endpoint_dol,
    parse_ips,
    rewrite_server_fields,
    tool_path,
    validate_endpoint,
)


class IpsTests(unittest.TestCase):
    def test_parse_and_apply_literal_ips_records(self):
        patch = b"PATCH" + (2).to_bytes(3, "big") + (3).to_bytes(2, "big") + b"xyz" + b"EOF"
        self.assertEqual(parse_ips(patch), [(2, b"xyz")])
        self.assertEqual(apply_ips(b"abcdef", patch), b"abxyzf")

    def test_rejects_malformed_ips(self):
        with self.assertRaisesRegex(ModderError, "header"):
            parse_ips(b"NOPEEOF")
        with self.assertRaisesRegex(ModderError, "truncated"):
            parse_ips(b"PATCH\x00")

    def test_accepts_empty_valid_ips_record_list(self):
        patch = b"PATCH" + b"EOF"
        self.assertEqual(parse_ips(patch), [])


class EndpointTests(unittest.TestCase):
    def test_accepts_same_width_ipv4(self):
        self.assertEqual(validate_endpoint(DEFAULT_SERVER), b"158.180.55.245")
        self.assertEqual(validate_endpoint("203.111.22.233"), b"203.111.22.233")

    def test_rejects_invalid_or_different_width_ipv4(self):
        for endpoint in ("not-an-ip", "127.0.0.1", "158.180.55.256"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ModderError):
                    validate_endpoint(endpoint)

    def test_rewrites_only_the_verified_fixed_width_address_fields(self):
        old = DEFAULT_SERVER.encode("ascii")
        new = b"203.111.22.233"
        template = b"head" + b"|".join([old] * 28) + b"|tail"
        output = rewrite_server_fields(template, new.decode("ascii"))
        self.assertEqual(len(output), len(template))
        self.assertEqual(output.count(new), 28)
        self.assertEqual(output.replace(new, old), template)

    def test_rejects_wrong_number_of_endpoint_slots(self):
        with self.assertRaisesRegex(ModderError, "Expected 28"):
            rewrite_server_fields(DEFAULT_SERVER.encode("ascii"), DEFAULT_SERVER)

    def test_stock_dol_requires_exact_supported_hash(self):
        with self.assertRaisesRegex(ModderError, "SHA-256"):
            make_endpoint_dol(b"not a Wii Chess DOL", b"PATCHEOF", DEFAULT_SERVER)


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
    def test_known_stock_dol_matches_saved_patched_template(self):
        stock_path = os.environ.get("WII_CHESS_TEST_STOCK_DOL")
        patched_path = os.environ.get("WII_CHESS_TEST_PATCHED_DOL")
        if not stock_path or not patched_path:
            self.skipTest("Set WII_CHESS_TEST_STOCK_DOL and WII_CHESS_TEST_PATCHED_DOL to run.")
        stock = Path(stock_path).read_bytes()
        known_patched = Path(patched_path).read_bytes()
        generated = make_endpoint_dol(stock, (Path(__file__).parents[1] / "patches" / "wii_chess_europe.ips").read_bytes(), DEFAULT_SERVER)
        self.assertEqual(generated, known_patched)


if __name__ == "__main__":
    unittest.main()
