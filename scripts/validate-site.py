#!/usr/bin/env python3
"""Validate an assembled Flowloop publication without executing site code."""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit

_spec = importlib.util.spec_from_file_location("assemble_site", Path(__file__).with_name("assemble-site.py"))
_build = importlib.util.module_from_spec(_spec)
sys.modules["assemble_site"] = _build
assert _spec.loader
_spec.loader.exec_module(_build)

ORIGIN = _build.ORIGIN
MANIFEST = _build.MANIFEST
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel", "data", "javascript", "blob"}
ASSET_SUFFIXES = {".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
                  ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".webm", ".pdf", ".json", ".xml", ".webmanifest"}


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)


class HtmlRefs(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str]] = []
        self.canonical: list[str] = []
        self.project_links: list[str] = []
        self.ids: set[str] = set()
        self.spoiler = False
        self.private_attr = False
        self.cloudflare_tokens: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        amap = {k.lower(): (v or "") for k, v in attrs}
        if amap.get("id"):
            self.ids.add(amap["id"])
        if tag.lower() == "a" and amap.get("name"):
            self.ids.add(amap["name"])
        if tag.lower() == "script" and amap.get("src") == _build.CLOUDFLARE_BEACON:
            try:
                config = json.loads(amap.get("data-cf-beacon", ""))
                token = config.get("token") if isinstance(config, dict) else None
            except json.JSONDecodeError:
                token = None
            self.cloudflare_tokens.append(token)
        for attr in ("href", "src", "poster", "data", "action"):
            if amap.get(attr):
                self.refs.append((attr, amap[attr]))
        if amap.get("srcset"):
            for part in amap["srcset"].split(","):
                url = part.strip().split()
                if url:
                    self.refs.append(("srcset", url[0]))
        if "data-publication" in amap:
            self.private_attr = True
        if "spoiler-details" in amap.get("class", "").split():
            self.spoiler = True
        if tag.lower() == "link" and "canonical" in amap.get("rel", "").lower().split():
            self.canonical.append(amap.get("href", ""))
        if tag.lower() == "a" and amap.get("href", "") in {"/flowloop-app/", "/caveos/"}:
            self.project_links.append(amap["href"])
        for attr in ("style",):
            for url in re.findall(r"url\(\s*['\"]?([^'\")]+)", amap.get(attr, ""), flags=re.I):
                self.refs.append(("style", url.strip()))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def local_target(site: Path, page_rel: str, url: str, mount: str = "") -> tuple[str | None, bool]:
    parts = urlsplit(url.strip())
    if parts.scheme.lower() in EXTERNAL_SCHEMES or parts.netloc or url.startswith("//"):
        return None, False
    path = unquote(parts.path)
    if not path:
        return page_rel, False
    if path.startswith("/"):
        if mount and path.startswith(mount):
            rel = path[len(mount):]
        else:
            rel = path.lstrip("/")
    else:
        rel = (PurePosixPath(page_rel).parent / path).as_posix()
    stack: list[str] = []
    for part in PurePosixPath(rel).parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not stack:
                return None, True
            stack.pop()
        else:
            stack.append(part)
    rel = "/".join(stack)
    if path.endswith("/"):
        rel = (rel + "/" if rel else "") + "index.html"
    elif not rel:
        rel = "index.html"
    return rel, False


def check_ref(v: Validation, site: Path, page_rel: str, attr: str, url: str, paths: set[str], mount: str = "") -> None:
    target, traversal = local_target(site, page_rel, url, mount)
    if traversal:
        v.error(f"{page_rel}: path traversal reference {url!r}")
        return
    if target is None:
        return
    suffix = PurePosixPath(urlsplit(url).path).suffix.lower()
    is_html = attr == "href" and (not suffix or suffix in {".html", ".htm"})
    is_asset = attr != "href" or suffix in ASSET_SUFFIXES
    if is_html or is_asset:
        if target not in paths:
            v.error(f"{page_rel}: missing local {'route' if is_html else 'asset'} {url!r} (resolved as {target})")


def validate(site: Path, caveos: Path | None = None, allow_unapproved_local: bool = False) -> list[str]:
    v = Validation()
    if site.is_symlink():
        return ["assembled site root must not be a symlink"]
    try:
        site = site.resolve(strict=True)
    except OSError as e:
        return [f"site directory does not exist or is inaccessible: {e}"]
    try:
        local = _build.check_local_flag(argparse.Namespace(allow_unapproved_local=allow_unapproved_local))
        policy = _build.profile_load(caveos.resolve(strict=True)) if caveos else None
        if policy:
            _build.approval(policy, local)
    except (_build.BuildError, OSError) as e:
        v.error(str(e))
        return v.errors
    paths = {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()}
    for p in site.rglob("*"):
        if p.is_symlink():
            v.error(f"symlink in assembled site: {p.relative_to(site)}")
    cname = site / "CNAME"
    if not cname.is_file() or cname.read_text(encoding="utf-8", errors="replace").strip() != "flowloop.io":
        v.error("CNAME must contain exactly flowloop.io")
    if ".nojekyll" not in paths:
        v.error("missing .nojekyll")
    if local:
        if ".unapproved-preview" not in paths:
            v.error("local unapproved preview must contain .unapproved-preview marker")
    elif ".unapproved-preview" in paths:
        v.error("publication mode must not contain .unapproved-preview")
    forbidden_names = {".git", ".openai", "README.md", "IMPLEMENTATION.md", "IMPORT-RECORD.md", "ASSET-PROVENANCE.json",
                       "package.json", "requirements.txt", ".env", ".DS_Store"}
    for rel in sorted(paths):
        parts = PurePosixPath(rel).parts
        if any(p in forbidden_names or p.startswith(".") and p not in {".nojekyll", ".unapproved-preview"} for p in parts):
            v.error(f"forbidden hidden/source file in site: {rel}")
    fixed = {"index.html", "404.html", "privacy.html", "CNAME", ".nojekyll", "robots.txt", "sitemap.xml", MANIFEST,
             "favicon.svg", "favicon.ico", "favicon-16x16.png", "favicon-32x32.png", "apple-touch-icon.png",
             "android-chrome-192x192.png", "android-chrome-512x512.png", "safari-pinned-tab.svg", "site.webmanifest",
             "browserconfig.xml", "mstile-150x150.png", ".unapproved-preview"}
    for rel in sorted(paths):
        if rel in fixed or rel.startswith(("portfolio/", "flowloop-app/", "static/", "download/", "caveos/")):
            continue
        v.error(f"file outside publication allowlist: {rel}")
    manifest_path = site / MANIFEST
    manifest = None
    if not manifest_path.is_file():
        v.error(f"missing {MANIFEST}")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as e:
            v.error(f"invalid {MANIFEST}: {e}")
        if manifest is not None:
            if manifest.get("schema_version") != 1:
                v.error("manifest schema_version must be 1")
            if policy and manifest.get("profile_id") != policy.get("profile_id"):
                v.error("manifest profile_id does not match CaveOS publication policy")
            source_dirty = manifest.get("source_dirty")
            if not isinstance(source_dirty, dict) or set(source_dirty) != {"flowloop", "caveos", "orchestrator"} or any(type(x) is not bool for x in source_dirty.values()):
                v.error("manifest source_dirty must contain boolean states for all three source trees")
            elif not local and any(source_dirty.values()):
                v.error("publication source trees are marked dirty")
            revisions = manifest.get("revisions")
            if not isinstance(revisions, dict) or set(revisions) != {"flowloop", "caveos", "orchestrator"}:
                v.error("manifest revisions must include Flowloop, CaveOS, and orchestrator")
            else:
                invalid = [name for name, rev in revisions.items()
                           if not isinstance(rev, str) or not (rev == "unavailable" or re.fullmatch(r"[0-9a-f]{40,64}", rev))]
                if invalid:
                    v.error(f"manifest has invalid revision values for {sorted(invalid)}")
                if not local and any(rev == "unavailable" for rev in revisions.values()):
                    v.error("publication manifest requires committed Git revisions for every source tree")
            hashes = manifest.get("files")
            if not isinstance(hashes, dict):
                v.error("manifest files must be a path-to-sha256 object")
            else:
                actual = paths - {MANIFEST}
                if set(hashes) != actual:
                    for rel in sorted(set(hashes) - actual):
                        v.error(f"manifest lists missing file: {rel}")
                    for rel in sorted(actual - set(hashes)):
                        v.error(f"file is absent from manifest: {rel}")
                for rel in sorted(actual & set(hashes)):
                    try:
                        if hashes[rel] != file_hash(site / rel):
                            v.error(f"manifest hash mismatch: {rel}")
                    except OSError as e:
                        v.error(f"cannot hash {rel}: {e}")
    if policy:
        expected = {"caveos/" + rel for rel in policy["files"]}
        actual = {p for p in paths if p.startswith("caveos/") and p != "caveos/"}
        if actual != expected:
            for rel in sorted(expected - actual):
                v.error(f"CaveOS policy file is missing from site: {rel}")
            for rel in sorted(actual - expected):
                v.error(f"CaveOS subtree contains file outside policy: {rel}")
        if not local and policy.get("status") != "approved":
            v.error("publication mode requires approved CaveOS policy")
    html_files = sorted(p for p in paths if p.lower().endswith((".html", ".htm")))
    html_parsers: dict[str, HtmlRefs] = {}
    refs_by_page: dict[str, list[tuple[str, str]]] = {}
    canonical_urls: set[str] = set()
    for rel in html_files:
        path = site / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as e:
            v.error(f"cannot read HTML {rel}: {e}")
            continue
        parser = HtmlRefs()
        try:
            parser.feed(text)
        except Exception as e:
            v.error(f"cannot parse HTML {rel}: {e}")
            continue
        html_parsers[rel] = parser
        if parser.private_attr:
            v.error(f"private publication marker remains in {rel}")
        if parser.spoiler:
            v.error(f"spoiler-details remains in {rel}")
        refs_by_page[rel] = parser.refs
        if rel.startswith("caveos/"):
            canonical = parser.canonical
            expected_url = f"{ORIGIN}/caveos/" + ("" if rel == "caveos/index.html" else rel.removeprefix("caveos/"))
            if canonical != [expected_url]:
                v.error(f"{rel}: expected one canonical URL {expected_url!r}, got {canonical!r}")
            if "https://caveos-unfiled.blizzfire.chatgpt.site" in text:
                v.error(f"{rel}: old CaveOS host remains in metadata")
            if policy:
                for page in policy["excluded_pages"]:
                    if re.search(r"(?:href|src)\s*=\s*(['\"])[^'\"]*(?:/|^)" + re.escape(page) + r"(?:[?#'\"])", text, flags=re.I):
                        v.error(f"{rel}: link to excluded page {page} remains")
        canonical_urls.update(x for x in parser.canonical if x)
    analytics = manifest.get("analytics") if isinstance(manifest, dict) else None
    expected_analytics: dict[str, str] = {}
    if analytics is not None:
        if (not isinstance(analytics, dict) or analytics.get("provider") != "cloudflare-web-analytics"
                or not isinstance(analytics.get("site_token"), str)
                or not re.fullmatch(r"[0-9a-f]{32}", analytics["site_token"])
                or not isinstance(analytics.get("pages"), list)
                or any(not isinstance(p, str) for p in analytics["pages"])):
            v.error("invalid Cloudflare Web Analytics manifest configuration")
        else:
            expected_pages = {"index.html", "flowloop-app/index.html"}
            expected_pages |= {p for p in html_parsers if p.startswith("caveos/")}
            if set(analytics["pages"]) != expected_pages or len(analytics["pages"]) != len(expected_pages):
                v.error("Cloudflare Web Analytics pages must match public content pages only")
            expected_analytics = {p: analytics["site_token"] for p in expected_pages}
    for rel, parser in html_parsers.items():
        expected_tokens = [expected_analytics[rel]] if rel in expected_analytics else []
        if parser.cloudflare_tokens != expected_tokens:
            v.error(f"{rel}: Cloudflare Web Analytics beacon does not match manifest coverage/token")
    for rel, refs in refs_by_page.items():
        mount = "/caveos/" if rel.startswith("caveos/") else ""
        for attr, url in refs:
            check_ref(v, site, rel, attr, url, paths, mount)
            parts = urlsplit(url.strip())
            target, traversal = local_target(site, rel, url, mount)
            if parts.fragment and not parts.scheme and not parts.netloc and not url.startswith("//") and target:
                target_parser = html_parsers.get(target)
                if target_parser and unquote(parts.fragment) not in target_parser.ids:
                    v.error(f"{rel}: missing local HTML fragment {parts.fragment!r} in {target}")
    home = html_parsers.get("index.html")
    if home:
        wanted = {"/flowloop-app/", "/caveos/"}
        found = set(home.project_links)
        if not wanted.issubset(found):
            v.error(f"index.html must link to both projects: missing {sorted(wanted - found)}")
    else:
        v.error("missing index.html")
    sitemap_path = site / "sitemap.xml"
    if sitemap_path.is_file():
        try:
            root = ET.parse(sitemap_path).getroot()
            locs = {el.text or "" for el in root.iter() if el.tag.endswith("}loc") or el.tag == "loc"}
            if locs != canonical_urls:
                v.error("sitemap URLs do not match retained canonical HTML pages")
        except (ET.ParseError, OSError) as e:
            v.error(f"invalid sitemap.xml: {e}")
    gallery_path = site / "caveos" / "site.js"
    if gallery_path.is_file():
        try:
            script = gallery_path.read_text(encoding="utf-8")
            match = re.search(r"(?ms)^\s*const\s+gallery\s*=\s*(\[.*?\])\s*;\s*const\s+viewer\b", script)
            if not match:
                v.error("caveos/site.js must expose a JSON gallery array before const viewer")
            else:
                gallery = json.loads(match.group(1))
                ids = [item.get("id") for item in gallery if isinstance(item, dict)] if isinstance(gallery, list) else []
                if not isinstance(gallery, list) or len(ids) != len(gallery) or len(ids) != len(set(ids)):
                    v.error("caveos/site.js gallery must contain unique objects with ids")
                if policy and set(ids) != set(policy["gallery_ids"]):
                    v.error("caveos/site.js gallery ids do not match publication policy")
                for item in gallery if isinstance(gallery, list) else []:
                    if not isinstance(item, dict) or not isinstance(item.get("src"), str):
                        v.error("caveos/site.js gallery item must include a source path")
                        continue
                    src = item["src"]
                    if src.startswith(("/", "\\")) or ".." in PurePosixPath(src).parts:
                        v.error(f"caveos/site.js has unsafe gallery source {src!r}")
                    elif "caveos/" + src not in paths:
                        v.error(f"caveos/site.js gallery asset is missing: {src}")
                    if policy and src not in policy["files"]:
                        v.error(f"caveos/site.js gallery asset is outside publication policy: {src}")
        except (OSError, UnicodeError, json.JSONDecodeError) as e:
            v.error(f"invalid caveos/site.js gallery data: {e}")
    # Validate CSS and JavaScript references with the referring file as the base.
    for rel in sorted(paths):
        suffix = PurePosixPath(rel).suffix.lower()
        if suffix not in {".css", ".js", ".mjs"}:
            continue
        try:
            text = (site / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            v.error(f"cannot read text asset {rel}")
            continue
        urls = []
        if suffix == ".css":
            urls += re.findall(r"url\(\s*['\"]?([^'\")]+)", text, flags=re.I)
            urls += re.findall(r"@import\s+(?:url\()?\s*['\"]([^'\"]+)", text, flags=re.I)
        else:
            urls += [u for u in re.findall(r"(?:src|href|fetch|location(?:\.href)?)\s*=\s*['\"]([^'\"]+)['\"]", text)
                     if PurePosixPath(urlsplit(u).path).suffix.lower() in ASSET_SUFFIXES and "$" not in u and "{{" not in u]
            urls += re.findall(r"(?:import\s*\(|from\s*)['\"]([^'\"]+\.(?:js|mjs|json))['\"]", text)
        for url in urls:
            check_ref(v, site, rel, "src", url.strip(), paths, "/caveos/" if rel.startswith("caveos/") else "")
    if not (site / "index.html").is_file() or not (site / "404.html").is_file():
        v.error("site requires root index.html and 404.html")
    if not (site / "privacy.html").is_file():
        v.error("site requires root privacy.html compatibility alias")
    for alias in ("static", "download"):
        app_prefix = f"flowloop-app/{alias}/"
        source_files = {p[len(app_prefix):] for p in paths if p.startswith(app_prefix)}
        root_files = {p[len(alias) + 1:] for p in paths if p.startswith(alias + "/")}
        if not source_files:
            v.error(f"site requires migrated flowloop-app/{alias}/ assets for the root alias")
        if source_files != root_files:
            v.error(f"root {alias}/ alias file set does not match flowloop-app/{alias}/")
        for rel in sorted(source_files & root_files):
            if file_hash(site / f"{alias}/{rel}") != file_hash(site / f"flowloop-app/{alias}/{rel}"):
                v.error(f"root {alias}/ alias differs from flowloop-app/{alias}/{rel}")
    return v.errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--caveos", type=Path)
    parser.add_argument("--allow-unapproved-local", action="store_true")
    args = parser.parse_args(argv)
    try:
        errors = validate(args.site, args.caveos, args.allow_unapproved_local)
    except (OSError, _build.BuildError) as e:
        errors = [str(e)]
    if errors:
        for error in errors:
            print(f"validate-site: {error}", file=sys.stderr)
        print(f"Validation failed: {len(errors)} issue(s)", file=sys.stderr)
        return 1
    print(f"Validated static site at {args.site.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
