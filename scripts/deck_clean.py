#!/usr/bin/env python3
"""deck_clean.py — strip artifacts from a .pptx before client delivery.

Removes:
  --remove-hidden          hidden slides (`p:sldId show="0"` or unreferenced sld parts)
  --remove-comments        slide comments + commentAuthors (ppt/comments/*, ppt/commentAuthors.xml)
  --remove-revision-info   collaboration revision metadata (ppt/changesInfos/, revisionInfo.xml, authors.xml)
  --remove-notes           speaker notes (ppt/notesSlides/, notesMaster, notesSlide refs)
  --all                    enable all of the above

Usage:
  deck_clean.py <input.pptx> <output.pptx> [flags]

Implementation: zip-level surgery. We unpack the .pptx, modify XML files, drop
unwanted parts, update [Content_Types].xml + relationship files, repack. This
avoids python-pptx's limitations around slide deletion and orphan handling.

Returns JSON summary to stdout listing what was removed.
"""

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

for prefix, uri in NS.items():
    ET.register_namespace("" if prefix == "ct" else prefix, uri)


def _read(zin: zipfile.ZipFile, name: str) -> bytes:
    return zin.read(name)


def _list_files(zin: zipfile.ZipFile) -> list[str]:
    return zin.namelist()


def _find_hidden_slide_rids(presentation_xml: bytes) -> set[str]:
    """Return set of rIds whose sldId has show='0'."""
    root = ET.fromstring(presentation_xml)
    sld_id_lst = root.find("p:sldIdLst", NS)
    if sld_id_lst is None:
        return set()
    hidden = set()
    for sld_id in sld_id_lst.findall("p:sldId", NS):
        if sld_id.get("show") == "0":
            rid = sld_id.get(f"{{{NS['r']}}}id")
            if rid:
                hidden.add(rid)
    return hidden


def _drop_hidden_slides_from_presentation(presentation_xml: bytes,
                                          rids_to_drop: set[str]) -> bytes:
    """Remove sldId entries for the given rIds. Returns updated XML."""
    root = ET.fromstring(presentation_xml)
    sld_id_lst = root.find("p:sldIdLst", NS)
    if sld_id_lst is not None:
        for sld_id in list(sld_id_lst.findall("p:sldId", NS)):
            rid = sld_id.get(f"{{{NS['r']}}}id")
            if rid in rids_to_drop:
                sld_id_lst.remove(sld_id)
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def _resolve_rels(rels_xml: bytes, rids: set[str]) -> set[str]:
    """Given a rels XML and a set of rIds, return the set of file targets."""
    root = ET.fromstring(rels_xml)
    targets = set()
    for rel in root.findall("rel:Relationship", NS):
        if rel.get("Id") in rids:
            targets.add(rel.get("Target"))
    return targets


def _remove_rels(rels_xml: bytes, rids: set[str]) -> bytes:
    """Remove relationships matching the given rIds. Returns updated XML."""
    root = ET.fromstring(rels_xml)
    for rel in list(root.findall("rel:Relationship", NS)):
        if rel.get("Id") in rids:
            root.remove(rel)
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def _normalize_target(target: str, base_part_dir: str = "ppt/") -> str:
    """Resolve a relationship target relative to its rels file's location."""
    target = target.lstrip("/")
    if target.startswith("../"):
        # Relative path — strip ../ and prepend base
        return target[3:]
    return base_part_dir + target.lstrip("./")


def _remove_content_type_entries(content_types_xml: bytes,
                                  paths_to_remove: set[str]) -> bytes:
    """Remove <Override> entries from [Content_Types].xml whose PartName matches."""
    root = ET.fromstring(content_types_xml)
    # PartName has leading slash
    paths_with_slash = {"/" + p for p in paths_to_remove}
    for el in list(root.findall("ct:Override", NS)):
        if el.get("PartName") in paths_with_slash:
            root.remove(el)
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def clean_deck(input_path: Path, output_path: Path, *,
               remove_hidden: bool = False,
               remove_comments: bool = False,
               remove_revision_info: bool = False,
               remove_notes: bool = False) -> dict:
    """Strip selected artifacts from input_path, write cleaned deck to output_path.

    Returns a summary dict listing what was removed.
    """
    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "hidden_slides_removed": 0,
        "comment_files_removed": 0,
        "revision_files_removed": 0,
        "notes_files_removed": 0,
        "removed_files": [],
    }

    files_to_skip: set[str] = set()
    file_overrides: dict[str, bytes] = {}

    with zipfile.ZipFile(input_path) as zin:
        all_files = set(_list_files(zin))

        # ── Read core files ──────────────────────────────────────────────
        presentation_xml = _read(zin, "ppt/presentation.xml") if "ppt/presentation.xml" in all_files else b""
        pres_rels_xml = _read(zin, "ppt/_rels/presentation.xml.rels") if "ppt/_rels/presentation.xml.rels" in all_files else b""
        content_types_xml = _read(zin, "[Content_Types].xml") if "[Content_Types].xml" in all_files else b""

        # ── Hidden slides ────────────────────────────────────────────────
        if remove_hidden and presentation_xml:
            hidden_rids = _find_hidden_slide_rids(presentation_xml)
            if hidden_rids:
                # Find file paths for those rids
                hidden_targets = _resolve_rels(pres_rels_xml, hidden_rids)
                for tgt in hidden_targets:
                    full_path = _normalize_target(tgt)
                    files_to_skip.add(full_path)
                    # Also drop the slide's _rels file
                    rels_path = full_path.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
                    files_to_skip.add(rels_path)
                    summary["removed_files"].append(full_path)
                # Update presentation.xml + presentation.xml.rels
                file_overrides["ppt/presentation.xml"] = (
                    _drop_hidden_slides_from_presentation(presentation_xml, hidden_rids)
                )
                file_overrides["ppt/_rels/presentation.xml.rels"] = (
                    _remove_rels(pres_rels_xml, hidden_rids)
                )
                summary["hidden_slides_removed"] = len(hidden_rids)

        # ── Comments ─────────────────────────────────────────────────────
        if remove_comments:
            comment_files = [f for f in all_files
                             if f.startswith("ppt/comments/") or
                                f.startswith("ppt/modernComments/") or
                                f == "ppt/commentAuthors.xml"]
            for f in comment_files:
                files_to_skip.add(f)
                summary["removed_files"].append(f)
                summary["comment_files_removed"] += 1

            # Drop comment-related rels from per-slide rels files
            for slide_rels_path in [f for f in all_files
                                    if f.startswith("ppt/slides/_rels/")]:
                if slide_rels_path in files_to_skip:
                    continue
                rels_xml = _read(zin, slide_rels_path)
                rels_root = ET.fromstring(rels_xml)
                changed = False
                for rel in list(rels_root.findall("rel:Relationship", NS)):
                    rel_type = rel.get("Type", "")
                    if "comments" in rel_type.lower() or "modernComments" in rel_type:
                        rels_root.remove(rel)
                        changed = True
                if changed:
                    file_overrides[slide_rels_path] = ET.tostring(
                        rels_root, xml_declaration=True, encoding="UTF-8")

            # Drop commentAuthors rel from presentation.xml.rels
            if pres_rels_xml:
                pres_rels_root = ET.fromstring(
                    file_overrides.get("ppt/_rels/presentation.xml.rels", pres_rels_xml)
                )
                for rel in list(pres_rels_root.findall("rel:Relationship", NS)):
                    rel_type = rel.get("Type", "")
                    if "commentAuthors" in rel_type:
                        pres_rels_root.remove(rel)
                file_overrides["ppt/_rels/presentation.xml.rels"] = ET.tostring(
                    pres_rels_root, xml_declaration=True, encoding="UTF-8")

        # ── Revision / changes info ──────────────────────────────────────
        if remove_revision_info:
            rev_paths = ["ppt/revisionInfo.xml", "ppt/authors.xml"]
            rev_paths += [f for f in all_files if f.startswith("ppt/changesInfos/")]
            rev_paths += [f for f in all_files if f.startswith("ppt/restoredKeyInfo")]
            for f in rev_paths:
                if f in all_files:
                    files_to_skip.add(f)
                    summary["removed_files"].append(f)
                    summary["revision_files_removed"] += 1

            # Drop their rels from presentation.xml.rels
            if pres_rels_xml:
                pres_rels_root = ET.fromstring(
                    file_overrides.get("ppt/_rels/presentation.xml.rels", pres_rels_xml)
                )
                for rel in list(pres_rels_root.findall("rel:Relationship", NS)):
                    rel_type = rel.get("Type", "")
                    if any(k in rel_type for k in ("changesInfo", "revisionInfo", "authors")):
                        pres_rels_root.remove(rel)
                file_overrides["ppt/_rels/presentation.xml.rels"] = ET.tostring(
                    pres_rels_root, xml_declaration=True, encoding="UTF-8")

        # ── Notes (optional) ─────────────────────────────────────────────
        if remove_notes:
            notes_paths = [f for f in all_files
                           if f.startswith("ppt/notesSlides/") or
                              f.startswith("ppt/notesMasters/")]
            for f in notes_paths:
                files_to_skip.add(f)
                summary["removed_files"].append(f)
                summary["notes_files_removed"] += 1

            # Drop notes rels from per-slide rels files + presentation rels
            for slide_rels_path in [f for f in all_files
                                    if f.startswith("ppt/slides/_rels/") or
                                       f == "ppt/_rels/presentation.xml.rels"]:
                if slide_rels_path in files_to_skip:
                    continue
                rels_xml = _read(zin, slide_rels_path)
                if slide_rels_path == "ppt/_rels/presentation.xml.rels":
                    rels_xml = file_overrides.get(slide_rels_path, rels_xml)
                rels_root = ET.fromstring(rels_xml)
                changed = False
                for rel in list(rels_root.findall("rel:Relationship", NS)):
                    rel_type = rel.get("Type", "")
                    if "notesSlide" in rel_type or "notesMaster" in rel_type:
                        rels_root.remove(rel)
                        changed = True
                if changed:
                    file_overrides[slide_rels_path] = ET.tostring(
                        rels_root, xml_declaration=True, encoding="UTF-8")

        # ── Update [Content_Types].xml ───────────────────────────────────
        if files_to_skip and content_types_xml:
            # Remove Overrides for skipped files
            file_overrides["[Content_Types].xml"] = _remove_content_type_entries(
                content_types_xml, files_to_skip
            )

        # ── Write the cleaned zip ────────────────────────────────────────
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename in files_to_skip:
                    continue
                if item.filename in file_overrides:
                    zout.writestr(item, file_overrides[item.filename])
                else:
                    zout.writestr(item, zin.read(item.filename))

    return summary


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="Input .pptx")
    parser.add_argument("output", help="Output .pptx")
    parser.add_argument("--remove-hidden", action="store_true",
                        help="Strip hidden slides")
    parser.add_argument("--remove-comments", action="store_true",
                        help="Strip slide comments + comment authors")
    parser.add_argument("--remove-revision-info", action="store_true",
                        help="Strip collaboration revision metadata")
    parser.add_argument("--remove-notes", action="store_true",
                        help="Strip speaker notes (not in --all)")
    parser.add_argument("--all", action="store_true",
                        help="Enable --remove-hidden + --remove-comments + --remove-revision-info "
                             "(does NOT strip notes — pass --remove-notes explicitly)")
    parser.add_argument("--quiet", action="store_true", help="JSON-only output")
    args = parser.parse_args()

    if args.all:
        args.remove_hidden = True
        args.remove_comments = True
        args.remove_revision_info = True

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.exists():
        print(f"ERROR: {in_path} does not exist", file=sys.stderr)
        sys.exit(2)

    if not any([args.remove_hidden, args.remove_comments,
                args.remove_revision_info, args.remove_notes]):
        print("ERROR: no clean operations selected. Pass --all or one of "
              "--remove-hidden / --remove-comments / --remove-revision-info / --remove-notes",
              file=sys.stderr)
        sys.exit(2)

    summary = clean_deck(
        in_path, out_path,
        remove_hidden=args.remove_hidden,
        remove_comments=args.remove_comments,
        remove_revision_info=args.remove_revision_info,
        remove_notes=args.remove_notes,
    )

    print(json.dumps(summary, indent=2))

    if not args.quiet:
        print(f"\n--- Cleaned: {in_path.name} → {out_path.name} ---", file=sys.stderr)
        print(f"  Hidden slides removed: {summary['hidden_slides_removed']}",
              file=sys.stderr)
        print(f"  Comment files removed: {summary['comment_files_removed']}",
              file=sys.stderr)
        print(f"  Revision files removed: {summary['revision_files_removed']}",
              file=sys.stderr)
        print(f"  Notes files removed: {summary['notes_files_removed']}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
