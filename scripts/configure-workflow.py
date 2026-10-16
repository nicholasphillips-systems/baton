#!/usr/bin/env python3
"""Install shared instruction files, backing up replaced files first."""
import datetime
import json
from pathlib import Path
import shutil
import sys
import uuid

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "lib"))
import workflow as w

home = w.user_home()
backup = w.state_dir() / "recovery" / (
    "instructions-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
manifest = []


def replace(path, text):
    if path.exists() and path.read_text() == text:
        return
    if path.exists() or path.is_symlink():
        relative = path.relative_to(home)
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination, follow_symlinks=False)
        manifest.append(str(relative))
    w.atomic_write(path, text)


replace(home / "AGENTS.md", (root / "templates/AGENTS.md.template").read_text())
adapter = (root / "templates/POINTER.md.template").read_text()
for relative in ["CLAUDE.md", "GEMINI.md", ".codex/AGENTS.md", ".gemini/GEMINI.md",
                 ".qwen/QWEN.md", ".config/opencode/AGENTS.md", ".cursorrules", ".clinerules"]:
    replace(home / relative, adapter)

if manifest:
    (backup / "manifest.json").write_text(json.dumps({"backed_up": manifest}, indent=2) + "\n")
    print(f"Shared instructions installed. Replaced files saved in {backup}")
else:
    print("Shared instructions installed.")
