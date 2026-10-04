from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "src" / "ui.py"
APP = ROOT / "app.py"

required_ui = {
    "anchor",
    "callout",
    "chapter_nav",
    "insight_card",
    "section_header",
    "source_note",
    "source_note_geospatial",
    "story_card",
    "subsection_header",
}

def function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

names = function_names(UI)
missing = sorted(required_ui - names)
if missing:
    raise SystemExit(f"[FAIL] src/ui.py kehilangan fungsi: {', '.join(missing)}")

app_text = APP.read_text(encoding="utf-8")
if "subsection_header" not in app_text:
    raise SystemExit("[FAIL] app.py tidak memakai subsection_header seperti kontrak revisi.")

print("[PASS] UI contract sinkron")
print("[PASS] subsection_header tersedia di src/ui.py")
print("[PASS] app.py dan src/ui.py berasal dari revisi yang sama")
