#!/usr/bin/env python3
"""File organizer CLI – copies (or moves) files into structured subfolders."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── hashing ──────────────────────────────────────────────────────────────────

CHUNK = 8 * 1024 * 1024  # 8 MB


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


# ── destination helpers ──────────────────────────────────────────────────────


def _ext_folder(path: Path) -> str:
    return path.suffix.lstrip(".").lower() or "no_ext"


def _date_folder(path: Path) -> str:
    mtime = path.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m")


def dest_for(path: Path, output: Path, by: str) -> Path:
    ext = _ext_folder(path)
    date = _date_folder(path)
    match by:
        case "type":
            return output / ext / path.name
        case "date":
            return output / date / path.name
        case "type-date":
            return output / ext / date / path.name
        case _:
            raise ValueError(f"Unknown --by value: {by}")


def safe_dest(dest: Path) -> Path:
    """Append _1, _2, … before the extension until the name is unused."""
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    parent = dest.parent
    n = 1
    while True:
        candidate = parent / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


# ── core logic ───────────────────────────────────────────────────────────────


def collect_files(input_dir: Path, recursive: bool) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    return sorted(
        p for p in input_dir.glob(pattern)
        if p.is_file() and not p.name.startswith(".")
    )


def organize(args: argparse.Namespace) -> dict:
    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    # ── clean output folder if requested ─────────────────────────────────
    if args.clean_output and not args.dry_run and output_dir.exists():
        shutil.rmtree(output_dir)

    files = collect_files(input_dir, args.recursive)

    seen_hashes: dict[str, Path] = {}  # hash -> first-occurrence source
    actions: list[dict] = []
    errors: list[dict] = []
    folders_created: set[str] = set()
    totals = {
        "scanned_files": len(files),
        "copied": 0,
        "moved": 0,
        "skipped_duplicates": 0,
        "duplicates_moved": 0,
        "errors": 0,
    }

    for src in files:
        try:
            file_hash = sha256(src)

            # ── dedupe check ─────────────────────────────────────────────
            is_dup = file_hash in seen_hashes
            if not is_dup:
                seen_hashes[file_hash] = src

            if is_dup and args.dedupe == "delete":
                actions.append({
                    "source": str(src),
                    "dest": None,
                    "action": "skipped",
                    "reason": f"duplicate of {seen_hashes[file_hash]}",
                    "hash": file_hash,
                })
                totals["skipped_duplicates"] += 1
                continue

            if is_dup and args.dedupe == "move":
                dest = safe_dest(output_dir / "Duplicates" / src.name)
                action_label = "duplicate_moved"
            else:
                dest = safe_dest(dest_for(src, output_dir, args.by))
                action_label = "move" if args.move else "copy"

            # ── perform filesystem action ────────────────────────────────
            folders_created.add(str(dest.parent))
            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if args.move and action_label != "duplicate_moved":
                    shutil.move(str(src), str(dest))
                else:
                    shutil.copy2(str(src), str(dest))
                    # For dedupe=move we still *copy* to Duplicates
                    # (originals stay untouched unless --move is set)
                    if action_label == "duplicate_moved" and args.move:
                        src.unlink()

            actions.append({
                "source": str(src),
                "dest": str(dest),
                "action": action_label,
                "hash": file_hash,
            })

            if action_label == "duplicate_moved":
                totals["duplicates_moved"] += 1
            elif action_label == "move":
                totals["moved"] += 1
            else:
                totals["copied"] += 1

        except Exception as exc:
            errors.append({"source": str(src), "error": str(exc)})
            totals["errors"] += 1

    # ── build breakdown by top-level folder ─────────────────────────────
    folder_counts: dict[str, int] = {}
    for entry in actions:
        if entry["dest"] is None:
            continue
        dest_path = Path(entry["dest"])
        try:
            top_folder = dest_path.relative_to(output_dir).parts[0]
        except (ValueError, IndexError):
            top_folder = "other"
        folder_counts[top_folder] = folder_counts.get(top_folder, 0) + 1

    breakdown = {
        **dict(sorted(folder_counts.items())),
        "total_files_in_output": sum(folder_counts.values()),
    }

    # ── build report ─────────────────────────────────────────────────────
    report = {
        "settings": vars(args),
        "totals": totals,
        "folders_created": sorted(folders_created),
        "breakdown": breakdown,
        "files": actions,
        "errors": errors,
    }
    return report


# ── CLI ──────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Organize files into structured subfolders."
    )
    p.add_argument("--input", default="resources", help="Source folder (default: resources)")
    p.add_argument("--output", default="organized", help="Destination folder (default: organized)")
    p.add_argument("--by", choices=["type", "date", "type-date"], default="type",
                    help="Organization strategy (default: type)")
    p.add_argument("--recursive", action="store_true", help="Scan subfolders inside input")
    p.add_argument("--dedupe", choices=["off", "move", "delete"], default="off",
                    help="Duplicate handling (default: off)")
    p.add_argument("--dry-run", action="store_true", help="Preview actions without changes")
    p.add_argument("--report", default="report.json", help="Report filename (default: report.json)")
    p.add_argument("--move", action="store_true", help="Move files instead of copying")
    p.add_argument("--clean-output", action="store_true",
                    help="Delete the output folder before organizing (ignored with --dry-run)")
    return p


def main() -> None:
    args = build_parser().parse_args()
    report = organize(args)

    # write report next to the output dir (repo root by convention)
    report_path = Path(args.report).resolve()
    if not args.dry_run:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    t = report["totals"]
    bd = report["breakdown"]
    mode = "DRY-RUN" if args.dry_run else "DONE"

    print(f"\n[{mode}] Scanned {t['scanned_files']} file(s)")
    print(f"  Copied: {t['copied']}  |  Moved: {t['moved']}")
    print(f"  Duplicates moved: {t['duplicates_moved']}  |  Skipped: {t['skipped_duplicates']}")
    print(f"  Errors: {t['errors']}")

    print(f"\n  Breakdown:")
    for folder, count in bd.items():
        print(f"    {folder}: {count}")

    if not args.dry_run:
        print(f"\nReport written to: {report_path}")
    else:
        print("\nNo changes made (dry-run). Report not written.")


if __name__ == "__main__":
    main()
