# File Organizer CLI

*A flexible command-line tool to organize mixed files (images, PDFs, videos, etc.) into structured folders with optional deduplication and reporting. It was  built with Python and Pandas as part of the **Codecademy AI Maker Bootcamp**.*

## What It Does

- Organizes files from a resources/ folder
- Outputs structured files into an organized/ folder
- Supports file-type and date-based grouping
- Detects and handles duplicate files (`SHA-256` hash)
- Generates a `JSON` report
- Supports dry-run mode for safe previews
- Designed as a robust, production-style CLI utility.

## Features

- Organize by:

  - type
  - date
  - type-date

- Exact duplicate detection (hash-based)
- Move or delete duplicates
- Safe filename collision handling
- Dry-run mode
- Optional clean output folder
- `JSON` audit report
- Standard library only (no external dependencies)

## Installation

```bash
git clone <repo-url>
cd file-organizer
```

Activate virtual environment (optional):
Windows:

```bash
venv\Scripts\activate
```
No external dependencies required.

## Usage

Place files to organize inside the `resources/` folder.

Basic run:

```bash
py organizer.py
```

Organize by type and date:

```bash
py organizer.py --by type-date
```

Remove duplicates (move to Duplicates folder):

```bash
py organizer.py --dedupe move
```

Delete duplicates instead:

```bash
py organizer.py --dedupe delete
```

Preview without changing files:

```bash
py organizer.py --dry-run
```


Clean output folder before organizing:

```bash
py organizer.py --clean-output
```

Generate report:

```bash
py organizer.py --report report.json
```

## Organization Rules

### By Type

```bash
organized/
  jpg/
  pdf/
  mp4/
```

### By Date

```bash
organized/
  2026-02/
  2026-01/
```

### By Type + Date

```bash
organized/
  jpg/2026-02/
  pdf/2025-12/
```

Files without extensions go into:

```bash
organized/
  no_ext/
```

### Duplicate Handling

Duplicates are detected using `SHA-256` hashing.
Modes:

- `off` → keep everything
- `move` → move duplicates into organized/Duplicates/
- `delete` → skip duplicates

### Report

The `JSON` report contains:

- Settings used
- Totals summary
- File actions (source → destination)
- Errors (if any)
- Folder breakdown

## Tech Stack

|Technology   | Role                  |
|-------------|-----------------------|
|Python 3.12+ | Core logic            |
|pathlib      | File system handling  |
|hashlib      | Duplicate detection   |
|argparse     | CLI interface         |
|json         | Reporting             |

## Project Context

Built as a demo-ready CLI file management utility focused on:

- Clean architecture and modular design
- Robust validation and safe filesystem operations
- Flexible, rule-based input handling
- Content-based duplicate detection (SHA-256 hashing)
- Production-style `JSON` reporting and auditability
The project emphasizes practical engineering decisions, safe defaults (`--dry-run`, `--clean-output`), and extensibility while remaining dependency-free and fully based on Python’s standard library.
