"""Developer-only synthetic fixture layout diagnostic; no user document input."""

import difflib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PIL import Image
from pdf_toolbox.word_com import WordAutomation, package_snapshot
from pdf_toolbox.word_layout import PlacementSettings

root = Path(__file__).resolve().parents[1] / "build" / "word-diagnostic"
root.mkdir(parents=True, exist_ok=True)
path = root / "synthetic.docx"
image = root / "page.png"
Image.new("RGB", (200, 300), "white").save(image)
with WordAutomation() as word:
    word.doc = word.app.Documents.Add()
    word.doc.Content.Text = "First page\x0cSecond page"
    word.doc.Sections.Last.Headers.Item(1).Range.Text = "Company header"
    word.doc.Sections.Last.Footers.Item(1).Range.Text = "Company footer"
    word.doc.SaveAs2(str(path), FileFormat=16)
with WordAutomation() as word:
    original = word.open(path)
    before = word.snapshot
    word.append(image, PlacementSettings(), original + 1)
    word.append(image, PlacementSettings(), original + 2)
    word.doc.Save()
    after = package_snapshot(path)
    for kind, a, b in zip(("body", "sections", "headers"), before, after):
        if kind == "body":
            b = b[: len(a)]
        if a != b:
            print(kind)
            print("\n".join(difflib.unified_diff(str(a).split("><"), str(b).split("><"))))
