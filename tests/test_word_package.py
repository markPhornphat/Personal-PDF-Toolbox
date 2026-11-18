from xml.dom import minidom
from zipfile import ZipFile

from pdf_toolbox.word_package import R, W, assemble, elements


def make_package(path, body, rels="", media=None):
    with ZipFile(path, "w") as package:
        package.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>'
            f'{body}<w:sectPr><w:pgSz w:w="12000" w:h="16000"/>'
            "</w:sectPr></w:body></w:document>",
        )
        package.writestr(
            "word/_rels/document.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/'
            f'package/2006/relationships">{rels}</Relationships>',
        )
        package.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/'
            'package/2006/content-types"><Default Extension="png" '
            'ContentType="image/png"/></Types>',
        )
        package.writestr("word/styles.xml", b"original styles")
        package.writestr("word/header1.xml", b"original header")
        for name, data in (media or {}).items():
            package.writestr(name, data)


def test_assembly_preserves_parts_and_remaps_colliding_image_relationships(tmp_path):
    source, output = tmp_path / "source.docx", tmp_path / "output.docx"
    original = "<w:p><w:r><w:t>Original content</w:t></w:r></w:p>"
    relation = f'<Relationship Id="rId1" Type="{R}/image" Target="media/image1.png"/>'
    make_package(source, original, relation, {"word/media/image1.png": b"original logo"})
    appended = '<w:p><w:r><w:drawing r:embed="rId1"/></w:r></w:p>'
    make_package(output, original + appended, relation, {"word/media/image1.png": b"new image"})
    assemble(source, output, 1)
    with ZipFile(source) as before, ZipFile(output) as after:
        for name in ("word/styles.xml", "word/header1.xml", "word/media/image1.png"):
            assert before.read(name) == after.read(name)
        document = minidom.parseString(after.read("word/document.xml"))
        body = document.getElementsByTagNameNS(W, "body")[0]
        assert len(elements(body)) == 3
        assert elements(body)[0].toxml() == original
        drawing = document.getElementsByTagNameNS(W, "drawing")[0]
        assert drawing.getAttributeNS(R, "embed") == "rIdPDFToolbox1"
        assert after.read("word/media/pdf-toolbox-1.png") == b"new image"
