import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("assemble_site", ROOT / "scripts" / "assemble-site.py")
build = importlib.util.module_from_spec(spec)
import sys
sys.modules["assemble_site"] = build
spec.loader.exec_module(build)
vspec = importlib.util.spec_from_file_location("validate_site", ROOT / "scripts" / "validate-site.py")
validate_module = importlib.util.module_from_spec(vspec)
sys.modules["validate_site"] = validate_module
vspec.loader.exec_module(validate_module)


class SiteToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.flow = self.base / "flow"
        self.cave = self.base / "cave"
        self.out = self.base / "site"
        self.flow.mkdir()
        self.dist = self.cave / "website" / "dist"
        (self.dist / "assets").mkdir(parents=True)
        self.cave.joinpath("website").mkdir(exist_ok=True)
        self._write(self.flow / "index.html", '<html><body><a href="/flowloop-app/">Flowloop</a><a href="/caveos/">CaveOS</a></body></html>')
        self._write(self.flow / "404.html", "<html><body>Not found</body></html>")
        self._write(self.flow / "privacy.html", "<p>Privacy</p>")
        self._write(self.flow / "flowloop-app" / "privacy.html", "<p>Privacy</p>")
        self._write(self.flow / "flowloop-app" / "index.html", "<html><body>Flowloop</body></html>")
        self._write(self.flow / "flowloop-app" / "index.html", "<h1>Flowloop</h1>")
        self._write(self.flow / "portfolio" / "site.css", "body{}")
        self._write(self.flow / "static" / "app.css", "body{}")
        self._write(self.flow / "flowloop-app" / "static" / "app.css", "body{}")
        self._write(self.flow / "flowloop-app" / "download" / "index.html", "<p>Download</p>")
        self._write(self.flow / "download" / "app.zip", "bytes")
        self._write(self.dist / "index.html", '''<!doctype html><html><head><meta property="og:url" content="https://old.example/index"><meta property="og:image" content="https://old.example/assets/picture.png"></head><body><p>Public</p><section data-publication="private"><p>LOCAL-PRIVATE-CANARY</p></section><a href="styles.css">Style link</a><a href="story.html">Excluded link</a><a href="absent.html">Absent link</a><img src="assets/picture.png"><img data-publication="private" src="assets/private.png"></body></html>''')
        self._write(self.dist / "styles.css", "body { background: url('assets/picture.png') }")
        self._write(self.dist / "site.js", '"use strict";\nconst gallery=[{"id":"allowed","src":"assets/picture.png","caption":"safe"},{"id":"unapproved","src":"assets/private.png"}];\nconst viewer=document.getElementById("viewer");\n')
        self._write(self.dist / "assets" / "picture.png", b"IMAGE")
        self._write(self.dist / "assets" / "private.png", b"PRIVATE-IMAGE")
        self.write_profile()

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else value.encode("utf-8"))

    def write_profile(self, status="pending", extra=None):
        profile = {"schema_version": 1, "profile_id": "synthetic-v1", "status": status,
                   "approved_by": "editor" if status == "approved" else None,
                   "approved_at": "2026-01-01" if status == "approved" else None,
                   "files": ["index.html", "styles.css", "site.js", "assets/picture.png"],
                   "gallery_ids": ["allowed"], "excluded_pages": ["story.html"],
                   "public_origin": "https://flowloop.io", "social_image": "assets/picture.png"}
        if extra:
            profile.update(extra)
        self._write(self.cave / "website" / "publication-profile.json", json.dumps(profile))

    def assemble_clean(self, *args, **kwargs):
        clean = ({"flowloop": "a" * 40, "caveos": "b" * 40, "orchestrator": "c" * 40},
                 {"flowloop": False, "caveos": False, "orchestrator": False})
        with mock.patch.object(build, "source_state", return_value=clean):
            return build.assemble(*args, **kwargs)

    def test_pending_approval_refuses_before_writing(self):
        with self.assertRaisesRegex(build.BuildError, "approval is pending"):
            build.assemble(self.flow, self.cave, self.out)
        self.assertFalse(self.out.exists())

    def test_local_preview_strips_private_dom_and_filters_gallery(self):
        build.assemble(self.flow, self.cave, self.out, allow_unapproved_local=True)
        page = (self.out / "caveos" / "index.html").read_text()
        self.assertNotIn("LOCAL-PRIVATE-CANARY", page)
        self.assertNotIn("data-publication", page)
        self.assertNotIn("story.html", page)
        self.assertIn('<a href="styles.css">Style link</a>', page)
        self.assertIn("https://flowloop.io/caveos/", page)
        self.assertIn("https://flowloop.io/caveos/assets/picture.png", page)
        self.assertNotIn("absent.html", page)
        self.assertIn("Absent link", page)  # visible text survives while the missing anchor is unwrapped
        js = (self.out / "caveos" / "site.js").read_text()
        self.assertIn('"allowed"', js)
        self.assertNotIn("unapproved", js)
        self.assertTrue((self.out / ".unapproved-preview").is_file())
        self.assertEqual((self.out / "privacy.html").read_bytes(), b"<p>Privacy</p>")
        self.assertEqual((self.out / "index.html").read_bytes(), (self.flow / "index.html").read_bytes())
        self.assertEqual((self.out / "flowloop-app" / "privacy.html").read_bytes(), (self.flow / "flowloop-app" / "privacy.html").read_bytes())

    def test_ci_rejects_local_preview_flag(self):
        with mock.patch.dict(os.environ, {"CI": "true"}, clear=True):
            with self.assertRaisesRegex(build.BuildError, "forbidden in CI"):
                build.assemble(self.flow, self.cave, self.out, allow_unapproved_local=True)
        self.assertFalse(self.out.exists())

    def test_policy_path_traversal_and_symlink_are_rejected(self):
        self.write_profile(extra={"files": ["../private.html"]})
        with self.assertRaisesRegex(build.BuildError, "unsafe CaveOS allowlisted file"):
            build.profile_load(self.cave)
        self.write_profile()
        link = self.dist / "assets" / "linked.png"
        link.symlink_to(self.dist / "assets" / "picture.png")
        self.write_profile(extra={"files": ["assets/linked.png"], "social_image": "assets/linked.png"})
        with self.assertRaisesRegex(build.BuildError, "symlink"):
            build.assemble(self.flow, self.cave, self.out, allow_unapproved_local=True)

    def test_validator_detects_missing_assets_and_manifest_mismatch(self):
        self.write_profile("approved")
        self.assemble_clean(self.flow, self.cave, self.out)
        (self.out / "caveos" / "styles.css").write_text("body{background:url('assets/not-there.png')}")
        errors = validate_module.validate(self.out, self.cave)
        self.assertTrue(any("missing local asset" in e for e in errors), errors)
        self.assertTrue(any("manifest hash mismatch" in e for e in errors), errors)

    def test_unapproved_validator_mode_requires_marker_and_is_ci_forbidden(self):
        errors = validate_module.validate(self.out, self.cave, allow_unapproved_local=True)
        self.assertTrue(any("does not exist" in e or "No such file" in e for e in errors), errors)
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            with self.assertRaisesRegex(build.BuildError, "forbidden in CI"):
                build.check_local_flag(type("A", (), {"allow_unapproved_local": True})())

    def test_output_is_deterministic(self):
        self.write_profile("approved")
        first, second = self.base / "one", self.base / "two"
        self.assemble_clean(self.flow, self.cave, first)
        self.assemble_clean(self.flow, self.cave, second)
        files1 = {p.relative_to(first).as_posix(): p.read_bytes() for p in first.rglob("*") if p.is_file()}
        files2 = {p.relative_to(second).as_posix(): p.read_bytes() for p in second.rglob("*") if p.is_file()}
        self.assertEqual(files1, files2)

    def test_approved_fixture_passes_complete_validator(self):
        self.write_profile("approved")
        self.assemble_clean(self.flow, self.cave, self.out)
        errors = validate_module.validate(self.out, self.cave)
        self.assertEqual(errors, [])

    def test_nonempty_output_is_never_overwritten(self):
        self.write_profile("approved")
        self.out.mkdir()
        sentinel = self.out / "keep.txt"
        sentinel.write_text("preserve")
        with self.assertRaisesRegex(build.BuildError, "refusing to overwrite nonempty"):
            build.assemble(self.flow, self.cave, self.out)
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_approved_publication_refuses_dirty_sources(self):
        self.write_profile("approved")
        dirty = ({"flowloop": "a" * 40, "caveos": "b" * 40, "orchestrator": "c" * 40},
                 {"flowloop": False, "caveos": True, "orchestrator": False})
        with mock.patch.object(build, "source_state", return_value=dirty):
            with self.assertRaisesRegex(build.BuildError, "requires clean"):
                build.assemble(self.flow, self.cave, self.out)
        self.assertFalse(self.out.exists())

    def test_parent_symlink_in_private_source_is_rejected(self):
        original = self.cave / "website"
        moved = self.base / "actual-website"
        original.rename(moved)
        original.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(build.BuildError, "symlink"):
            build.assemble(self.flow, self.cave, self.out, allow_unapproved_local=True)
        self.assertFalse(self.out.exists())

    def test_retained_links_keep_matching_closing_tags(self):
        self._write(self.dist / "index.html", '<html><head></head><body><a href="index.html">Keep</a><a href="story.html">Unwrap</a><a href="https://example.com">External</a></body></html>')
        build.assemble(self.flow, self.cave, self.out, allow_unapproved_local=True)
        page = (self.out / "caveos/index.html").read_text()
        self.assertIn('<a href="index.html">Keep</a>', page)
        self.assertIn('<a href="https://example.com">External</a>', page)
        self.assertNotIn('story.html', page)
        self.assertEqual(page.count('<a '), page.count('</a>'))

    def test_validator_catches_broken_local_fragment(self):
        self.write_profile("approved")
        self._write(self.flow / "index.html", '<a href="/flowloop-app/#not-there">Flowloop</a><a href="/caveos/">CaveOS</a>')
        self.assemble_clean(self.flow, self.cave, self.out)
        errors = validate_module.validate(self.out, self.cave)
        self.assertTrue(any("missing local HTML fragment" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
