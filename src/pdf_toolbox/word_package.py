"""Append Word-generated page XML to the unchanged original OOXML package."""

from pathlib import Path
from xml.dom import minidom
from zipfile import ZIP_DEFLATED, ZipFile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def elements(node):
    return [child for child in node.childNodes if child.nodeType == child.ELEMENT_NODE]


def assemble(original: Path, generated: Path, original_nodes: int):
    """Preserve original parts, body nodes and section properties byte-for-byte in meaning.

    Word supplies pagination/anchor XML only for appended paragraphs. Their images
    get fresh relationship IDs and filenames, so no original resource is replaced.
    """
    with ZipFile(original) as source, ZipFile(generated) as output:
        doc = minidom.parseString(source.read("word/document.xml"))
        added_doc = minidom.parseString(output.read("word/document.xml"))
        doc_root, added_root = doc.documentElement, added_doc.documentElement
        assert doc_root is not None and added_root is not None
        body = doc.getElementsByTagNameNS(W, "body")[0]
        added_body = added_doc.getElementsByTagNameNS(W, "body")[0]
        original_children = [node for node in elements(body) if node.localName != "sectPr"]
        if len(original_children) != original_nodes:
            raise ValueError("Word rewrote the original document structure. No output was saved.")
        appended = [node for node in elements(added_body) if node.localName != "sectPr"][
            original_nodes:
        ]
        # Preserve namespace declarations used by Word-generated drawing markup.
        for name in added_root.attributes.keys():
            if name.startswith("xmlns:") and not doc_root.hasAttribute(name):
                doc_root.setAttribute(name, added_root.getAttribute(name))
        rel_path = "word/_rels/document.xml.rels"
        relationships = minidom.parseString(
            source.read(rel_path)
            if rel_path in source.namelist()
            else f'<Relationships xmlns="{REL}"/>'
        )
        generated_rels = minidom.parseString(output.read("word/_rels/document.xml.rels"))
        rel_root = relationships.documentElement
        assert rel_root is not None
        rel_map = {
            node.getAttribute("Id"): node for node in elements(generated_rels.documentElement)
        }
        used = {node.getAttribute("Id") for node in elements(relationships.documentElement)}
        replacements: dict[str, str] = {}
        new_media = {}
        imported = []
        for node in appended:
            copied = doc.importNode(node, True)
            for child in [copied, *copied.getElementsByTagName("*")]:
                for attribute in list(child.attributes.values()):
                    if attribute.namespaceURI != R:
                        continue
                    old_id = attribute.value
                    if old_id not in replacements:
                        relation = rel_map[old_id]
                        if not relation.getAttribute("Type").endswith("/image"):
                            raise ValueError("Unexpected relationship in an appended page.")
                        if relation.getAttribute("TargetMode") == "External":
                            raise ValueError("An appended image is linked instead of embedded.")
                        index = len(replacements) + 1
                        new_id = f"rIdPDFToolbox{index}"
                        while new_id in used:
                            index += 1
                            new_id = f"rIdPDFToolbox{index}"
                        used.add(new_id)
                        suffix = Path(relation.getAttribute("Target")).suffix
                        target = f"media/pdf-toolbox-{index}{suffix}"
                        while (
                            "word/" + target in source.namelist() or "word/" + target in new_media
                        ):
                            index += 1
                            target = f"media/pdf-toolbox-{index}{suffix}"
                        resource = "word/" + relation.getAttribute("Target").lstrip("/")
                        if ".." in Path(resource).parts:
                            raise ValueError("Unexpected image resource path.")
                        new_media["word/" + target] = output.read(resource)
                        new_relation = relationships.createElementNS(REL, "Relationship")
                        new_relation.setAttribute("Id", new_id)
                        new_relation.setAttribute("Type", relation.getAttribute("Type"))
                        new_relation.setAttribute("Target", target)
                        rel_root.appendChild(new_relation)
                        replacements[old_id] = new_id
                    child.setAttributeNS(R, attribute.name, replacements[old_id])
            imported.append(copied)
        final_section = next((node for node in elements(body) if node.localName == "sectPr"), None)
        for node in imported:
            body.insertBefore(node, final_section)
        types = minidom.parseString(source.read("[Content_Types].xml"))
        output_types = minidom.parseString(output.read("[Content_Types].xml"))
        type_root = types.documentElement
        assert type_root is not None
        extensions = {node.getAttribute("Extension") for node in elements(types.documentElement)}
        for node in elements(output_types.documentElement):
            extension = node.getAttribute("Extension")
            if extension and extension not in extensions:
                type_root.appendChild(types.importNode(node, True))
                extensions.add(extension)
        changed = {
            "word/document.xml": doc.toxml(encoding="utf-8"),
            "word/_rels/document.xml.rels": relationships.toxml(encoding="utf-8"),
            "[Content_Types].xml": types.toxml(encoding="utf-8"),
        }
        assembled = generated.with_name("assembled.docx")
        with ZipFile(assembled, "w", ZIP_DEFLATED) as destination:
            for entry in source.infolist():
                destination.writestr(entry, changed.get(entry.filename, source.read(entry)))
            for name, data in changed.items():
                if name not in source.namelist():
                    destination.writestr(name, data)
            for name, data in new_media.items():
                destination.writestr(name, data)
    assembled.replace(generated)
