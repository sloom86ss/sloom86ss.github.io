#!/usr/bin/env python3
"""Offline quality gate for SLOOM365: validate data and parse every inline script."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InlineScripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.current = None
        self.parts = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "script":
            return
        attrs = dict(attrs)
        if attrs.get("src"):
            self.current = None
            return
        kind = (attrs.get("type") or "").lower()
        if kind and kind not in ("text/javascript", "application/javascript", "module"):
            self.current = None
            return
        self.current = []
        self.parts.append(self.current)

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script":
            self.current = None


def fail(message):
    print("FAIL:", message, file=sys.stderr)
    raise SystemExit(1)


def main():
    python_files = sorted(set(ROOT.glob("*.py")) | set((ROOT / "scripts").rglob("*.py")))
    for path in python_files:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except Exception as exc:
            fail(f"Python syntax: {path.relative_to(ROOT)}: {exc}")
    print(f"Python syntax OK ({len(python_files)} files)")

    node = shutil.which("node")
    if not node:
        fail("Node.js is required to validate JavaScript")

    html_files = sorted(ROOT.glob("*.html"))
    script_count = 0
    with tempfile.TemporaryDirectory(prefix="sloom365-check-") as temp:
        temp_path = Path(temp)
        for page in html_files:
            parser = InlineScripts()
            try:
                parser.feed(page.read_text(encoding="utf-8"))
                parser.close()
            except Exception as exc:
                fail(f"HTML parsing: {page.name}: {exc}")
            for number, parts in enumerate(parser.parts, 1):
                source = "".join(parts)
                if not source.strip():
                    continue
                target = temp_path / f"{page.stem}-{number}.mjs"
                target.write_text(source, encoding="utf-8")
                result = subprocess.run(
                    [node, "--check", str(target)],
                    capture_output=True, text=True, check=False
                )
                if result.returncode:
                    fail(f"JavaScript syntax: {page.name} inline script {number}: "
                         f"{(result.stderr or result.stdout).strip()}")
                script_count += 1

    for path in sorted(ROOT.glob("*.js")):
        result = subprocess.run([node, "--check", str(path)], capture_output=True,
                                text=True, check=False)
        if result.returncode:
            fail(f"JavaScript syntax: {path.name}: {(result.stderr or result.stdout).strip()}")
        script_count += 1
    for path in sorted((ROOT / "api").glob("*.js")) if (ROOT / "api").exists() else []:
        result = subprocess.run([node, "--check", "--input-type=module"],
                                input=path.read_text(encoding="utf-8"),
                                capture_output=True, text=True, check=False)
        if result.returncode:
            fail(f"JavaScript syntax: {path.relative_to(ROOT)}: "
                 f"{(result.stderr or result.stdout).strip()}")
        script_count += 1
    print(f"JavaScript syntax OK ({script_count} scripts)")

    for path in sorted(ROOT.glob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"JSON: {path.name}: {exc}")
    data_path = ROOT / "data.json"
    if data_path.exists():
        data = json.loads(data_path.read_text(encoding="utf-8"))
        if not isinstance(data.get("leagues"), dict) or not data["leagues"]:
            fail("data.json has no valid leagues object")
        for name, league in data["leagues"].items():
            if not isinstance(league, dict) or not isinstance(league.get("matches", []), list):
                fail(f"Invalid league data: {name}")
    sitemap = ROOT / "sitemap.xml"
    if sitemap.exists():
        try:
            ET.parse(sitemap)
        except Exception as exc:
            fail(f"sitemap.xml: {exc}")
    print("JSON, league data and sitemap OK")
    print("SLOOM365 quality checks passed")


if __name__ == "__main__":
    main()
