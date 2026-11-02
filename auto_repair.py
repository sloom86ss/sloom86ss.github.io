#!/usr/bin/env python3
"""SLOOM365 free, conservative code checker and safe auto-repair bot.

Only deterministic, explicitly reviewed fixes are applied. Unknown failures stop
the run and are reported; the bot never rewrites arbitrary application logic.
"""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGES = ("index.html", "sloom360.html", "ai.html")
SAFE_REPAIRS = (
    # Restore a missing JavaScript concatenation operator in the known match-card template.
    ('</div>\':\'\')<div class="match-meta"', '</div>\':\'\')+\'<div class="match-meta"'),
)

class InlineScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = False
        self.current = []
        self.scripts = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            attrs = dict(attrs)
            self.in_script = True
            self.current = []
            self.external = bool(attrs.get("src"))
    def handle_data(self, data):
        if self.in_script and not getattr(self, "external", False):
            self.current.append(data)
    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.in_script:
            source = "".join(self.current).strip()
            if source:
                self.scripts.append(source)
            self.in_script = False
            self.current = []
            self.external = False

def apply_safe_repairs():
    changed = []
    for name in PAGES:
        path = ROOT / name
        if not path.exists():
            raise RuntimeError("صفحة أساسية مفقودة: " + name)
        source = path.read_text(encoding="utf-8")
        updated = source
        for old, new in SAFE_REPAIRS:
            updated = updated.replace(old, new)
        if updated != source:
            path.write_text(updated, encoding="utf-8")
            changed.append(name)
    return changed

def validate():
    errors = []
    for name in PAGES:
        path = ROOT / name
        parser = InlineScripts()
        try:
            parser.feed(path.read_text(encoding="utf-8"))
            for i, source in enumerate(parser.scripts, 1):
                with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
                    f.write(source)
                    temp = f.name
                result = subprocess.run(["node", "--check", temp], capture_output=True, text=True)
                Path(temp).unlink(missing_ok=True)
                if result.returncode:
                    errors.append(f"{name}: JavaScript #{i}: {(result.stderr or result.stdout).strip()[:500]}")
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    for path in ROOT.rglob("*.py"):
        if ".git" in path.parts:
            continue
        result = subprocess.run([sys.executable, "-m", "py_compile", str(path)], capture_output=True, text=True)
        if result.returncode:
            errors.append(f"{path.relative_to(ROOT)}: {(result.stderr or result.stdout).strip()[:500]}")
    for name in ("data.json",):
        try:
            json.loads((ROOT / name).read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    for name in ("sitemap.xml",):
        try:
            ET.parse(ROOT / name)
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    if errors:
        raise RuntimeError("تعذر الإصلاح الآمن تلقائياً:\n- " + "\n- ".join(errors))
    return True

def main():
    changed = apply_safe_repairs()
    # Existing repair.py only rebuilds deterministic SEO support files.
    subprocess.run([sys.executable, str(ROOT / "repair.py")], check=True)
    validate()
    print(json.dumps({"ok": True, "auto_fixed": changed}, ensure_ascii=False))
if __name__ == "__main__":
    main()
