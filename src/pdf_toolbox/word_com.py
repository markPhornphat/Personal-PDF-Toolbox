"""Thread-affine Microsoft Word adapter. Imported without requiring Office."""

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile
from uuid import uuid4

from PIL import Image

from .pdf import safe_local
from .word_layout import Layout, PlacementSettings, fit_image
from .word_logging import record_error

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass(frozen=True)
class WordInfo:
    path: Path
    size: int
    pages: int
    layout: Layout


def check_document(path: Path):
    if path.suffix.lower() != ".docx" or not safe_local(path):
        raise ValueError("Choose a local .docx document.")
    if any(path.with_name("~$" + name).exists() for name in (path.name, path.name[2:])):
        raise ValueError("The Word document is locked. Close it in Word and try again.")
    import os

    if os.name == "nt":
        import win32file
        import pywintypes

        try:
            handle = win32file.CreateFile(
                str(path), win32file.GENERIC_READ, 0, None, win32file.OPEN_EXISTING, 0, None
            )
            handle.Close()
        except pywintypes.error as error:
            raise ValueError(
                "The Word document is inaccessible or locked. "
                "Close it in Word and check file permissions."
            ) from error
    try:
        with ZipFile(path) as package:
            package.read("word/document.xml")
            if any(name.lower().endswith("vbaproject.bin") for name in package.namelist()):
                raise ValueError("Choose a macro-free .docx document.")
            for name in package.namelist():
                if name.endswith(".rels"):
                    for relation in ET.fromstring(package.read(name)):
                        if relation.get("TargetMode") == "External" and not relation.get(
                            "Type", ""
                        ).endswith("/hyperlink"):
                            raise ValueError(
                                "This document has linked external content. "
                                "Embed it in Word before offline conversion."
                            )
    except (BadZipFile, KeyError, ET.ParseError) as error:
        raise ValueError(
            "The Word file is encrypted, corrupted or not a supported .docx."
        ) from error


def normalized(element):
    """Ignore editing-session IDs and cached dynamic page-field results only."""
    element = ET.fromstring(ET.tostring(element))
    for node in element.iter():
        for key in list(node.attrib):
            local = key.split("}")[-1]
            if local.startswith("rsid") or local in {"paraId", "textId"}:
                del node.attrib[key]
    field_stack = []
    for node in element.iter():
        if node.tag == W + "fldChar":
            kind = node.get(W + "fldCharType")
            if kind == "begin":
                field_stack.append(["", False])
            elif kind == "separate" and field_stack:
                field_stack[-1][1] = True
            elif kind == "end" and field_stack:
                field_stack.pop()
        elif node.tag == W + "instrText" and field_stack:
            field_stack[-1][0] += node.text or ""
        elif node.tag == W + "t" and field_stack:
            instruction, result = field_stack[-1]
            if result and str(instruction).strip().split(" ")[0] in {
                "PAGE",
                "NUMPAGES",
                "SECTIONPAGES",
            }:
                node.text = "#PAGE-FIELD#"
    return ET.canonicalize(ET.tostring(element, encoding="unicode"))


def package_snapshot(path: Path):
    with ZipFile(path) as package:
        body = ET.fromstring(package.read("word/document.xml")).find(W + "body")
        if body is None:
            raise ValueError("The Word document has no body.")
        original = [normalized(child) for child in body if child.tag != W + "sectPr"]
        sections = [normalized(node) for node in body.iter(W + "sectPr")]
        headers = {
            name: normalized(ET.fromstring(package.read(name)))
            for name in package.namelist()
            if name.startswith(("word/header", "word/footer")) and name.endswith(".xml")
        }
        return original, sections, headers


class WordAutomation:
    def __enter__(self):
        self.app = None
        self.doc = None
        self.records = []
        self.run_id = uuid4().hex[:12]
        self.previous_links = None
        try:
            import pythoncom
            from win32com.client import DispatchEx
        except ImportError as error:
            raise ValueError(
                "Word automation components are missing. Reinstall PDF Toolbox."
            ) from error
        self.com = pythoncom
        pythoncom.CoInitialize()
        try:
            self.app = DispatchEx("Word.Application")
            self.app.Visible = False
            self.app.DisplayAlerts = 0
            self.app.AutomationSecurity = 3  # force-disable macros in this instance only
            self.previous_links = self.app.Options.UpdateLinksAtOpen
            self.app.Options.UpdateLinksAtOpen = False
            return self
        except Exception as error:
            record_error("Word activation", error)
            self.__exit__(None, None, None)
            raise ValueError(
                "Microsoft Word Desktop automation is unavailable. "
                "Install and activate Word, then try again."
            ) from error

    def __exit__(self, *_):
        try:
            if self.doc is not None:
                self.doc.Close(SaveChanges=0)
        finally:
            self.doc = None
            try:
                if self.app is not None:
                    try:
                        if self.previous_links is not None:
                            self.app.Options.UpdateLinksAtOpen = self.previous_links
                    finally:
                        self.app.Quit(SaveChanges=0)
            finally:
                self.app = None
                self.com.CoUninitialize()

    def _open(self, path, readonly=False):
        try:
            doc = self.app.Documents.Open(
                FileName=str(path),
                ConfirmConversions=False,
                ReadOnly=readonly,
                AddToRecentFiles=False,
                PasswordDocument="PDF-Toolbox-no-password",
                WritePasswordDocument="PDF-Toolbox-no-password",
                Visible=False,
                OpenAndRepair=False,
                NoEncodingDialog=True,
            )
            if doc.ProtectionType != -1 or doc.TrackRevisions:
                doc.Close(SaveChanges=0)
                raise ValueError("Remove document editing protection and tracked changes first.")
            doc.Repaginate()
            return doc
        except ValueError:
            raise
        except Exception as error:
            record_error("Word document open", error)
            raise ValueError(
                "Word could not open the document. Check corruption, password "
                "protection, file locks and Word activation."
            ) from error

    def open(self, path):
        import shutil

        check_document(path)
        self.path = path
        self.original_package = path.with_name("original-package.docx")
        shutil.copy2(path, self.original_package)
        self.source_snapshot = package_snapshot(path)
        self.doc = self._open(path)
        self.original_pages = int(self.doc.ComputeStatistics(2))
        self.original_page_starts = [
            int(self.doc.GoTo(1, 1, page).Start) for page in range(1, self.original_pages + 1)
        ]
        self.original_end = max(0, int(self.doc.Content.End) - 2)
        self.original_end_page = int(
            self.doc.Range(self.original_end, self.original_end).Information(3)
        )
        self.original_shapes = int(self.doc.Shapes.Count)
        self.doc.Save()
        self.snapshot = package_snapshot(path)
        self.layout()  # fail before rendering if safe placement cannot be established
        return self.original_pages

    def layout(self):
        section = self.doc.Sections.Last
        setup = section.PageSetup
        if setup.TextColumns.Count != 1:
            raise ValueError("Multi-column final sections require manual layout review.")
        width, height = float(setup.PageWidth), float(setup.PageHeight)
        left, right = float(setup.LeftMargin), width - float(setup.RightMargin)
        gutter = max(0, float(setup.Gutter))
        if setup.MirrorMargins:
            # Intersection of odd/even safe areas; preserves mirrored settings.
            left = max(float(setup.LeftMargin), float(setup.RightMargin)) + gutter
            right = width - left
        elif setup.GutterPos == 1:  # top gutter
            pass
        elif setup.GutterPos == 2:  # right gutter
            right -= gutter
        else:
            left += gutter
        top = float(setup.TopMargin) + (gutter if setup.GutterPos == 1 else 0)
        bottom = height - float(setup.BottomMargin)
        for collection, header in ((section.Headers, True), (section.Footers, False)):
            for index in (1, 2, 3):
                story = collection.Item(index)
                if not story.Exists:
                    continue
                # Floating header/footer geometry can depend on wrapping, rotation,
                # groups and relative anchors. Refuse rather than guess its boundary.
                if story.Shapes.Count:
                    raise ValueError(
                        "Header/footer contains floating objects whose bounds "
                        "cannot be verified. Use inline logos in Word first."
                    )
                rng = story.Range.Duplicate
                if rng.Tables.Count:
                    raise ValueError(
                        "Header/footer table boundaries cannot yet be verified. "
                        "Use a document with paragraph-based headers and footers."
                    )
                if rng.Frames.Count or rng.Borders.Enable:
                    raise ValueError(
                        "Framed or bordered headers/footers require manual "
                        "layout review; their occupied bounds are uncertain."
                    )
                if not rng.Text.strip() and not rng.InlineShapes.Count and not rng.Tables.Count:
                    continue
                top_edge = float(rng.Information(6))
                last = rng.Duplicate
                last.SetRange(max(rng.Start, rng.End - 1), max(rng.Start, rng.End - 1))
                last_y = float(last.Information(6))
                if min(top_edge, last_y) < 0:
                    raise ValueError(
                        "Word cannot measure header/footer boundaries. "
                        "Layout protection could not be verified."
                    )
                font = float(last.Font.Size)
                if not 0 < font < 1000:
                    sizes = [float(character.Font.Size) for character in rng.Characters]
                    if any(not 0 < size < 1000 for size in sizes):
                        raise ValueError("Cannot measure mixed header/footer font sizes.")
                    font = max(sizes, default=24)
                # A smaller final character must not hide taller glyphs in the line.
                mixed_size = float(rng.Font.Size)
                if not 0 < mixed_size < 1000:
                    sizes = [float(character.Font.Size) for character in rng.Characters]
                    if any(not 0 < size < 1000 for size in sizes):
                        raise ValueError("Cannot measure mixed header/footer font sizes.")
                    font = max([font, *sizes])
                # Include line descent, inline image height and table row footprint.
                end = last_y + font * 1.5
                for inline in rng.InlineShapes:
                    y = float(inline.Range.Information(6))
                    if y < 0:
                        raise ValueError("Cannot measure an inline header/footer image.")
                    end = max(end, y + float(inline.Height) + font * 0.5)
                if header:
                    top = max(top, end)
                else:
                    bottom = min(bottom, top_edge)
        layout = Layout(width, height, left, top, right, bottom)
        if not 0 <= left < right <= width or not 0 <= top < bottom <= height:
            raise ValueError("Header/footer layout leaves no verifiable safe image area.")
        return layout

    def append(self, image: Path, settings: PlacementSettings, expected: int):
        doc = self.doc
        # Keep the original last paragraph intact; new anchors get a separate paragraph.
        end = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
        end.InsertBefore("\r")
        anchor = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
        anchor.InsertBreak(7)  # wdPageBreak; no new sections
        anchor = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
        anchor.InsertBefore("\u200b")  # stable nonprinting anchor before the paragraph mark
        anchor = doc.Range(doc.Content.End - 2, doc.Content.End - 1)
        paragraph = anchor.ParagraphFormat
        paragraph.SpaceBefore = 0
        paragraph.SpaceAfter = 0
        paragraph.KeepWithNext = False
        paragraph.PageBreakBefore = False
        paragraph.LineSpacingRule = 4  # exactly
        paragraph.LineSpacing = 1
        anchor.Font.Size = 1
        doc.Repaginate()
        if anchor.Information(3) != expected or doc.ComputeStatistics(2) != expected:
            raise ValueError(
                "Unexpected appended page. Trailing breaks or section layout "
                "require review; no output was saved."
            )
        with Image.open(image) as picture:
            rect = fit_image(self.layout(), *picture.size, settings)
        shape = doc.Shapes.AddPicture(
            str(image), False, True, rect.x, rect.y, rect.width, rect.height, anchor
        )
        shape.Name = f"PDFToolbox_{self.run_id}_{len(self.records) + 1}"
        shape.LockAspectRatio = -1
        shape.RelativeHorizontalPosition = 1  # page
        shape.RelativeVerticalPosition = 1  # page
        shape.WrapFormat.Type = 3  # no text wrap (front)
        shape.LockAnchor = True
        shape.LayoutInCell = False
        shape.Width = rect.width
        shape.Height = rect.height
        shape.Left, shape.Top = rect.x, rect.y
        self.records.append((shape.Name, expected, rect))
        shape = anchor = end = None

    def _validate(self, expected, count):
        doc = self.doc
        doc.Repaginate()
        if int(doc.ComputeStatistics(2)) != expected:
            raise ValueError("Final Word page count does not match the expected count.")
        starts = [int(doc.GoTo(1, 1, page).Start) for page in range(1, self.original_pages + 1)]
        end_page = int(doc.Range(self.original_end, self.original_end).Information(3))
        if starts != self.original_page_starts or end_page != self.original_end_page:
            raise ValueError(
                "The original Word pages repaginated during insertion. No output was saved."
            )
        if len(self.records) != count or doc.Shapes.Count != self.original_shapes + count:
            raise ValueError("Inserted image count validation failed.")
        for name, page, rect in self.records:
            shape = doc.Shapes.Item(name)
            if shape.Type != 13 or int(shape.Anchor.Information(3)) != page:
                raise ValueError(
                    f"Image embedding, order or page assignment validation failed "
                    f"({name}: type {shape.Type}, page "
                    f"{shape.Anchor.Information(3)}, expected {page})."
                )
            if any(
                abs(float(actual) - wanted) > 0.5
                for actual, wanted in (
                    (shape.Left, rect.x),
                    (shape.Top, rect.y),
                    (shape.Width, rect.width),
                    (shape.Height, rect.height),
                )
            ):
                raise ValueError("Image placement validation failed.")
        # Re-evaluate protection after repagination, including page-number growth.
        layout = self.layout()
        if any(
            rect.x < layout.left
            or rect.y < layout.top
            or rect.right > layout.right + 0.5
            or rect.bottom > layout.bottom + 0.5
            for _, _, rect in self.records
        ):
            raise ValueError("Header/footer protection validation failed.")

    def validate_save(self, expected, count):
        from .word_package import assemble

        self._validate(expected, count)
        self.doc.Save()
        original, _, _ = self.snapshot
        actual, _, _ = package_snapshot(self.path)
        if actual[: len(original)] != original:
            raise ValueError("Original content changed during Word page insertion.")
        self.doc.Close(SaveChanges=0)
        self.doc = None
        assemble(self.original_package, self.path, len(original))
        original, sections, headers = self.source_snapshot
        actual, actual_sections, actual_headers = package_snapshot(self.path)
        if actual[: len(original)] != original or sections != actual_sections:
            raise ValueError("Original content or section formatting preservation failed.")
        if headers != actual_headers:
            raise ValueError("Header/footer preservation validation failed.")
        self.doc = self._open(self.path, readonly=True)
        self._validate(expected, count)


def inspect_word(path: Path) -> WordInfo:
    """Inspect a disposable local copy; never open or save the original in Word."""
    from tempfile import TemporaryDirectory
    import shutil

    check_document(path)
    with TemporaryDirectory(prefix="pdf-toolbox-inspect-") as temporary:
        copied = Path(temporary) / "inspect.docx"
        shutil.copy2(path, copied)
        with WordAutomation() as word:
            word.doc = word._open(copied, readonly=True)
            return WordInfo(
                path, path.stat().st_size, int(word.doc.ComputeStatistics(2)), word.layout()
            )
