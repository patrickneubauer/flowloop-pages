#!/usr/bin/env python3
"""Assemble a deterministic, buildless static publication from two source trees."""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from typing import NoReturn
from urllib.parse import unquote, urlsplit

ORIGIN = "https://flowloop.io"
PROFILE = "publication-profile.json"
MANIFEST = "deployment-manifest.json"
CLOUDFLARE_BEACON = "https://static.cloudflareinsights.com/beacon.min.js"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class BuildError(Exception):
    pass


def fail(message: str) -> NoReturn:
    raise BuildError(message)


def safe_rel(value: str, label: str = "path") -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        fail(f"invalid {label}: {value!r}")
    p = PurePosixPath(value)
    if p.is_absolute() or any(part in ("", ".", "..") for part in p.parts):
        fail(f"unsafe {label}: {value!r}")
    if any(part.startswith(".") for part in p.parts):
        fail(f"hidden {label} is not publishable: {value!r}")
    return p.as_posix()


def source_file(root: Path, rel: str) -> Path:
    rel = safe_rel(rel)
    candidate = root / rel
    cur = root
    for part in PurePosixPath(rel).parts:
        cur = cur / part
        if cur.is_symlink():
            fail(f"symlink in source path: {rel}")
    if not candidate.is_file():
        fail(f"allowlisted source file is missing: {rel}")
    return candidate


def profile_load(caveos: Path) -> dict:
    path = source_file(caveos, "website/" + PROFILE)
    if path.is_symlink() or not path.is_file():
        fail(f"missing or unsafe CaveOS publication policy: {path}")
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        fail(f"cannot read CaveOS publication policy: {e}")
    if profile.get("schema_version") != 1:
        fail("unsupported CaveOS publication policy schema_version")
    if not isinstance(profile.get("profile_id"), str) or not profile["profile_id"].strip():
        fail("publication policy profile_id must be nonempty")
    if not isinstance(profile.get("files"), list) or not profile["files"]:
        fail("publication policy files must be a nonempty list")
    if not isinstance(profile.get("gallery_ids"), list):
        fail("publication policy gallery_ids must be a list")
    if any(not isinstance(x, str) or not x.strip() for x in profile["gallery_ids"]):
        fail("publication policy gallery_ids must contain nonempty strings")
    if len(profile["gallery_ids"]) != len(set(profile["gallery_ids"])):
        fail("publication policy gallery_ids must be unique")
    files = [safe_rel(x, "CaveOS allowlisted file") for x in profile["files"]]
    if any(x.startswith("website/dist/") for x in files):
        fail("CaveOS policy file paths must be relative to website/dist")
    if len(files) != len(set(files)):
        fail("publication policy has duplicate file paths")
    excluded = profile.get("excluded_pages", [])
    if not isinstance(excluded, list) or any(not isinstance(x, str) for x in excluded):
        fail("publication policy excluded_pages must be a list of strings")
    excluded = [safe_rel(x, "excluded page") for x in excluded]
    if any(not x.lower().endswith((".html", ".htm")) for x in excluded):
        fail("publication policy excluded_pages entries must be HTML paths")
    if any(PurePosixPath(f).name in {PurePosixPath(x).name for x in excluded} for f in files):
        fail("publication policy allowlists an excluded page")
    if profile.get("public_origin", ORIGIN) != ORIGIN:
        fail(f"publication policy public_origin must be {ORIGIN}")
    social_image = safe_rel(profile.get("social_image", "assets/work-bay.jpg"), "social_image")
    if social_image.startswith("website/dist/") or social_image not in files:
        fail("publication policy social_image must be an allowlisted file")
    profile["social_image"] = social_image
    return {**profile, "files": files, "gallery_ids": profile["gallery_ids"], "excluded_pages": excluded}


def check_local_flag(args: argparse.Namespace) -> bool:
    local = bool(getattr(args, "allow_unapproved_local", False))
    if local and ("CI" in os.environ or "GITHUB_ACTIONS" in os.environ):
        fail("--allow-unapproved-local is LOCAL preview only and is forbidden in CI/GITHUB_ACTIONS")
    return local


def git_revision(root: Path) -> str:
    try:
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
                                check=True, capture_output=True, text=True, timeout=5)
        value = result.stdout.strip()
        return value if re.fullmatch(r"[0-9a-f]{40,64}", value) else "unavailable"
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def source_state(flowloop: Path, caveos: Path, orchestrator: Path) -> tuple[dict, dict]:
    revisions = {}
    dirty = {}
    for name, root in (("flowloop", flowloop), ("caveos", caveos), ("orchestrator", orchestrator)):
        revisions[name] = git_revision(root)
        try:
            status = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=normal"],
                                   check=True, capture_output=True, text=True, timeout=10)
            dirty[name] = bool(status.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            dirty[name] = True
    return revisions, dirty


def approval(profile: dict, local: bool) -> None:
    if profile.get("status") == "approved":
        if not (isinstance(profile.get("approved_by"), str) and profile["approved_by"].strip()
                and isinstance(profile.get("approved_at"), str) and profile["approved_at"].strip()):
            fail("approved publication policy requires nonempty approved_by and approved_at")
        return
    if local:
        return
    fail("CaveOS publication approval is pending; refusing to write a site (use --allow-unapproved-local for a LOCAL preview only)")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def html_href_present(href: str, source_rel: str, output_paths: set[str], mount: str = "") -> bool:
    href = html.unescape(href.strip())
    if not href or href.startswith(("#", "//")):
        return True
    parts = urlsplit(href)
    if parts.scheme or parts.netloc:
        return True
    raw_path = unquote(parts.path)
    if not raw_path:
        return True
    if raw_path.startswith("/"):
        if mount and raw_path.startswith(mount):
            candidate = raw_path[len(mount):]
        else:
            candidate = raw_path.lstrip("/")
    else:
        candidate = (PurePosixPath(source_rel).parent / raw_path).as_posix()
    normalized = []
    for part in PurePosixPath(candidate).parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not normalized:
                return False
            normalized.pop()
        else:
            normalized.append(part)
    candidate = "/".join(normalized)
    if urlsplit(href).path.endswith("/"):
        candidate = (candidate + "/" if candidate else "") + "index.html"
    elif not candidate:
        candidate = "index.html"
    html_route = (not PurePosixPath(candidate).suffix) or PurePosixPath(candidate).suffix.lower() in {".html", ".htm"}
    return not html_route or candidate in output_paths


class HtmlSanitizer(HTMLParser):
    def __init__(self, source_rel: str, output_paths: set[str], cave: bool = False,
                 social_image: str = "assets/work-bay.jpg"):
        super().__init__(convert_charrefs=False)
        self.source_rel = source_rel
        self.output_paths = output_paths
        self.cave = cave
        self.social_image = social_image
        self.output: list[str] = []
        self.drop_stack: list[str] = []
        self.anchor_stack: list[bool] = []
        self.canonical_found = False

    def _attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> list[tuple[str, str | None]]:
        attrs = [(k, v) for k, v in attrs if k.lower() != "data-publication"]
        attrs = [(k, v) for k, v in attrs if not (tag.lower() == "a" and k.lower() == "href" and v is not None
                                                   and not html_href_present(v, self.source_rel, self.output_paths,
                                                                             "/caveos/" if self.cave else ""))]
        if self.cave:
            fixed = []
            for k, v in attrs:
                kl = k.lower()
                if kl == "content" and v is not None:
                    meta_prop = next((av for ak, av in attrs if ak.lower() in ("property", "name")), "") or ""
                    if meta_prop.lower() == "og:url":
                        v = self._canonical_url()
                    elif meta_prop.lower() == "og:image":
                        v = self._cave_url(self.social_image)
                if kl == "href" and v and any(ak.lower() == "rel" and "canonical" in (av or "").lower().split()
                                               for ak, av in attrs):
                    v = self._canonical_url()
                    self.canonical_found = True
                fixed.append((k, v))
            attrs = fixed
        return attrs

    def _canonical_url(self) -> str:
        rel = self.source_rel.removeprefix("caveos/")
        return f"{ORIGIN}/caveos/" + ("" if rel == "index.html" else rel)

    @staticmethod
    def _cave_url(value: str) -> str:
        p = urlsplit(html.unescape(value))
        path = p.path
        if path.startswith("https://caveos-unfiled.blizzfire.chatgpt.site/"):
            path = "/" + path.split("/", 3)[-1]
        elif path.startswith("/"):
            path = path.lstrip("/")
        return f"{ORIGIN}/caveos/{path.lstrip('/')}" + (("?" + p.query) if p.query else "") + (("#" + p.fragment) if p.fragment else "")

    @staticmethod
    def _start(tag: str, attrs: list[tuple[str, str | None]], close: bool = False) -> str:
        bits = ["<", tag]
        for key, value in attrs:
            bits += [" ", key]
            if value is not None:
                bits += ['="', html.escape(value, quote=True), '"']
        bits.append(" />" if close else ">")
        return "".join(bits)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        private = any(k.lower() == "data-publication" and (v or "").lower() == "private" for k, v in attrs)
        if self.drop_stack:
            if tag.lower() not in VOID:
                self.drop_stack.append(tag.lower())
            return
        if private:
            if tag.lower() not in VOID:
                self.drop_stack = [tag.lower()]
            return
        clean = self._attrs(tag, attrs)
        orig_href = next((v for k, v in attrs if k.lower() == "href"), None)
        unlink = tag.lower() == "a" and orig_href is not None and not any(k.lower() == "href" for k, _ in clean)
        if tag.lower() == "a":
            self.anchor_stack.append(unlink)
        if not unlink:
            self.output.append(self._start(tag, clean))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.drop_stack or any(k.lower() == "data-publication" and (v or "").lower() == "private" for k, v in attrs):
            return
        self.output.append(self._start(tag, self._attrs(tag, attrs), True))

    def handle_endtag(self, tag: str) -> None:
        if self.drop_stack:
            if tag.lower() not in VOID and tag.lower() in self.drop_stack:
                index = len(self.drop_stack) - 1 - self.drop_stack[::-1].index(tag.lower())
                del self.drop_stack[index:]
            return
        if tag.lower() == "a":
            omitted = self.anchor_stack.pop() if self.anchor_stack else False
            if not omitted:
                self.output.append(f"</{tag}>")
        else:
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.drop_stack:
            self.output.append(data)

    def handle_entityref(self, name: str) -> None:
        if not self.drop_stack:
            self.output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.drop_stack:
            self.output.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        if not self.drop_stack:
            self.output.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        if not self.drop_stack:
            self.output.append(f"<!{decl}>")

    def unknown_decl(self, data: str) -> None:
        if not self.drop_stack:
            self.output.append(f"<![{data}]>")

    def handle_pi(self, data: str) -> None:
        if not self.drop_stack:
            self.output.append(f"<?{data}>")


class CanonicalCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        amap = {k.lower(): v or "" for k, v in attrs}
        if "canonical" in amap.get("rel", "").lower().split() and amap.get("href"):
            self.urls.append(amap["href"])

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def sanitize_html(data: bytes, rel: str, output_paths: set[str], cave: bool = False,
                  social_image: str = "assets/work-bay.jpg") -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        fail(f"HTML is not UTF-8: {rel}: {e}")
    parser = HtmlSanitizer(rel, output_paths, cave, social_image)
    parser.feed(text)
    parser.close()
    result = "".join(parser.output)
    if cave and not parser.canonical_found:
        canonical = f'<link rel="canonical" href="{parser._canonical_url()}">'
        if re.search(r"</head\s*>", result, flags=re.I):
            result = re.sub(r"</head\s*>", canonical + "</head>", result, count=1, flags=re.I)
        else:
            result = canonical + result
    return result.encode("utf-8")


def gallery_filter(data: bytes, ids: list[str], allowed_paths: set[str]) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        fail(f"site.js is not UTF-8: {e}")
    match = re.search(r"(?ms)(^\s*const\s+gallery\s*=\s*)(\[.*?\])(\s*;\s*const\s+viewer\b)", text)
    if not match:
        fail("CaveOS site.js does not contain a JSON gallery array before const viewer")
    try:
        items = json.loads(match.group(2))
    except json.JSONDecodeError as e:
        fail(f"CaveOS gallery must be JSON data (not executable JavaScript): {e}")
    if not isinstance(items, list):
        fail("CaveOS gallery is not an array")
    selected = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            fail("CaveOS gallery items must be objects with string ids")
        if item["id"] in ids:
            src = item.get("src")
            if not isinstance(src, str):
                fail(f"gallery item {item['id']} has no string src")
            rel = safe_rel(src, "gallery asset")
            if rel not in allowed_paths:
                fail(f"approved gallery asset is not in the file allowlist: {src}")
            selected.append(item)
    if set(x["id"] for x in selected) != set(ids):
        fail("publication policy gallery_ids do not match gallery entries in site.js")
    if len(selected) != len(set(ids)):
        fail("CaveOS site.js has duplicate approved gallery ids")
    json_array = json.dumps(selected, ensure_ascii=False, separators=(",", ":"))
    return (text[:match.start(2)] + json_array + text[match.end(2):]).encode("utf-8")


def copy_tree_filtered(src: Path, dst: Path, rel: str) -> None:
    base = src if rel == "." else src / rel
    if not base.exists():
        fail(f"required Flowloop path is missing: {rel}")
    if base.is_symlink():
        fail(f"symlink source is not permitted: {rel}")
    if base.is_file():
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(base, target)
        return
    for current, dirs, files in os.walk(base, followlinks=False):
        cur = Path(current)
        for d in dirs:
            if (cur / d).is_symlink():
                fail(f"symlink source is not permitted: {(cur / d).relative_to(src)}")
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            source = cur / name
            if source.is_symlink():
                fail(f"symlink source is not permitted: {source.relative_to(src)}")
            if name.startswith("."):
                continue
            if not source.is_file():
                continue
            relpath = source.relative_to(src)
            target = dst / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


def ensure_disjoint(output: Path, roots: list[Path]) -> None:
    for root in roots:
        try:
            output.relative_to(root)
            fail(f"output path overlaps source/orchestrator directory: {output}")
        except ValueError:
            pass
        try:
            root.relative_to(output)
            fail(f"output path is an ancestor of source/orchestrator directory: {output}")
        except ValueError:
            pass


def add_web_analytics(data: bytes, token: str, page: str) -> bytes:
    if CLOUDFLARE_BEACON.encode("ascii") in data:
        fail(f"Cloudflare Web Analytics is already present in {page}")
    closing = list(re.finditer(rb"</body\s*>", data, flags=re.I))
    if len(closing) != 1:
        fail(f"Cloudflare Web Analytics requires one closing body tag in {page}")
    snippet = ("<!-- Cloudflare Web Analytics -->\n"
               f'<script type="module" src="{CLOUDFLARE_BEACON}" '
               f'data-cf-beacon=\'{{"token":"{token}"}}\'></script>\n'
               "<!-- End Cloudflare Web Analytics -->\n").encode("ascii")
    position = closing[0].start()
    return data[:position] + snippet + data[position:]


def assemble(flowloop: Path, caveos: Path, output: Path, allow_unapproved_local: bool = False,
             cloudflare_web_analytics_token: str = "") -> Path:
    if flowloop.is_symlink() or caveos.is_symlink():
        fail("Flowloop and CaveOS source roots must not be symlinks")
    flowloop = flowloop.resolve(strict=True)
    caveos = caveos.resolve(strict=True)
    orchestrator = Path(__file__).resolve().parents[1]
    output = output.absolute()
    if output.exists() and output.is_symlink():
        fail("output path must not be a symlink")
    output = output.resolve(strict=False)
    for parent in output.parents:
        if parent.exists() and parent.is_symlink():
            fail(f"output parent must not be a symlink: {parent}")
    ensure_disjoint(output.resolve(strict=False), [flowloop, caveos, orchestrator])
    profile = profile_load(caveos)
    local = check_local_flag(argparse.Namespace(allow_unapproved_local=allow_unapproved_local))
    approval(profile, local)  # must happen before staging or writing
    analytics_token = cloudflare_web_analytics_token.lower()
    if analytics_token and not re.fullmatch(r"[0-9a-f]{32}", analytics_token):
        fail("Cloudflare Web Analytics requires its 32-character hexadecimal public site token")
    cave_dist = caveos / "website" / "dist"
    allow = set(profile["files"])
    for rel in sorted(allow):
        source_file(caveos, "website/dist/" + rel)
    replacements = profile.get("text_replacements", {})
    if not isinstance(replacements, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not k for k, v in replacements.items()):
        fail("publication policy text_replacements must map nonempty strings to strings")
    if not (flowloop / "index.html").is_file() or not (flowloop / "404.html").is_file():
        fail("Flowloop source must contain root index.html and 404.html")
    # Copy to a sibling staging directory, then replace only an absent or empty destination.
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        fail(f"refusing to overwrite nonempty output directory: {output}")
    revisions, dirty = source_state(flowloop, caveos, orchestrator)
    if not local and (any(dirty.values()) or any(v == "unavailable" for v in revisions.values())):
        fail("publication requires clean Git worktrees with committed revisions for Flowloop, CaveOS, and orchestrator")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=output.parent))
    try:
        for rel in ("index.html", "404.html", "portfolio", "flowloop-app"):
            copy_tree_filtered(flowloop, stage, rel)
        for name in ("favicon.svg", "site.webmanifest"):
            src = flowloop / name
            if src.is_symlink():
                fail(f"symlink source is not permitted: {name}")
            if src.is_file():
                shutil.copyfile(src, stage / name)
        # Compatibility aliases and root legal/favicon assets retain migrated bytes.
        privacy = flowloop / "flowloop-app" / "privacy.html"
        if not privacy.is_file() or privacy.is_symlink():
            fail("Flowloop source must contain flowloop-app/privacy.html")
        shutil.copyfile(privacy, stage / "privacy.html")
        for name in ("favicon.ico", "favicon-16x16.png", "favicon-32x32.png", "apple-touch-icon.png",
                     "android-chrome-192x192.png", "android-chrome-512x512.png", "safari-pinned-tab.svg",
                     "browserconfig.xml", "mstile-150x150.png"):
            src = flowloop / "flowloop-app" / name
            if src.is_symlink():
                fail(f"symlink source is not permitted: flowloop-app/{name}")
            if src.is_file():
                shutil.copyfile(src, stage / name)
        if not (stage / "site.webmanifest").exists():
            legacy_manifest = flowloop / "flowloop-app" / "site.webmanifest"
            if legacy_manifest.is_symlink():
                fail("symlink source is not permitted: flowloop-app/site.webmanifest")
            if legacy_manifest.is_file():
                shutil.copyfile(legacy_manifest, stage / "site.webmanifest")
        # Alias directories are byte-for-byte copies from the migrated app.
        for alias in ("static", "download"):
            src = flowloop / "flowloop-app" / alias
            if src.exists():
                copy_tree_filtered(src, stage / alias, ".")
        # The selected CaveOS policy paths are the only CaveOS content copied.
        for cave_rel in sorted(allow):
            source = source_file(caveos, "website/dist/" + cave_rel)
            dest_rel = "caveos/" + cave_rel
            target = stage / dest_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            if cave_rel == "site.js":
                data = gallery_filter(data, profile["gallery_ids"], allow)
            elif cave_rel.lower().endswith(".html"):
                for old, new in replacements.items():
                    data = data.replace(old.encode("utf-8"), new.encode("utf-8"))
                # Route resolution uses the complete output plan, including future copies.
                planned = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
                planned |= {"caveos/" + p for p in allow}
                data = sanitize_html(data, dest_rel, planned, cave=True, social_image=profile["social_image"])
            target.write_bytes(data)
        excluded = set(profile["excluded_pages"])
        for target in sorted(stage.rglob("*.html")):
            text = target.read_text(encoding="utf-8")
            if re.search(r"class\s*=\s*([\"'])[^\"']*\bspoiler-details\b", text, flags=re.I):
                fail(f"publication refusal: spoiler-details remains in {target.relative_to(stage)}")
            for page in excluded:
                if re.search(r"(?:href|src)\s*=\s*([\"'])[^\"']*(?:^|/)" + re.escape(page) + r"(?:[?#\"'])", text, flags=re.I):
                    fail(f"publication refusal: link to excluded page {page} remains")
        analytics_pages = []
        if analytics_token:
            # Track public content pages only. Legal/download aliases and the private
            # standalone CaveOS source retain their original bytes and behavior.
            tracked = {"index.html", "flowloop-app/index.html"}
            tracked |= {"caveos/" + rel for rel in allow if rel.lower().endswith(".html")}
            for rel in sorted(tracked):
                target = stage / rel
                target.write_bytes(add_web_analytics(target.read_bytes(), analytics_token, rel))
                analytics_pages.append(rel)
        (stage / "CNAME").write_text("flowloop.io\n", encoding="ascii")
        (stage / ".nojekyll").write_bytes(b"")
        if local:
            (stage / ".unapproved-preview").write_text("LOCAL PREVIEW ONLY\n", encoding="ascii")
        retained_html = sorted(p.relative_to(stage).as_posix() for p in stage.rglob("*.html") if p.is_file())
        sitemap_urls = []
        for rel in retained_html:
            if rel == "404.html":
                continue
            try:
                collector = CanonicalCollector()
                collector.feed((stage / rel).read_text(encoding="utf-8"))
                collector.close()
            except (OSError, UnicodeError):
                continue
            sitemap_urls.extend(collector.urls)
        sitemap = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n" + "".join(f"  <url><loc>{html.escape(u)}</loc></url>\n" for u in sorted(set(sitemap_urls))) + "</urlset>\n"
        (stage / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        (stage / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n", encoding="utf-8")
        file_hashes = {p.relative_to(stage).as_posix(): sha256(p.read_bytes()) for p in sorted(stage.rglob("*"))
                       if p.is_file() and p.name != MANIFEST}
        manifest = {"schema_version": 1, "profile_id": profile["profile_id"],
                    "revisions": revisions, "source_dirty": dirty, "files": file_hashes}
        if analytics_token:
            manifest["analytics"] = {"provider": "cloudflare-web-analytics", "site_token": analytics_token,
                                     "pages": analytics_pages}
        (stage / MANIFEST).write_text(json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        if output.exists():
            output.rmdir()
        stage.replace(output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flowloop", type=Path, required=True)
    parser.add_argument("--caveos", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-unapproved-local", action="store_true")
    parser.add_argument("--cloudflare-web-analytics-token", default="",
                        help="public Cloudflare Web Analytics site token (not an API credential)")
    args = parser.parse_args(argv)
    try:
        result = assemble(args.flowloop, args.caveos, args.output, args.allow_unapproved_local,
                          args.cloudflare_web_analytics_token)
        print(f"Assembled static site at {result}")
        return 0
    except (BuildError, OSError) as e:
        print(f"assemble-site: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
