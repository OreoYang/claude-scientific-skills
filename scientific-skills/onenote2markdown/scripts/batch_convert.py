#!/usr/bin/env python3
"""
Batch OneNote to Markdown Converter
Convert multiple notebooks or sections with advanced options
"""

import argparse
import subprocess
import sys
import json
from pathlib import Path


def load_config(config_file):
    """Load notebook configurations from JSON file"""
    try:
        with open(config_file) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def convert_notebook(notebook_name, output_dir, options=None):
    """Convert a single notebook"""
    cmd = [
        "python", "onenote_dump/main.py",
        notebook_name,
        output_dir
    ]

    if options:
        if options.get("section"):
            cmd.extend(["--section", options["section"]])
        if options.get("max_pages"):
            cmd.extend(["----max-pages", str(options["max_pages"])])
        if options.get("start_page"):
            cmd.extend(["--start-page", str(options["start_page"])])
        if options.get("new_session"):
            cmd.append("--new-session")
        if options.get("verbose"):
            cmd.append("--verbose")

    print(f"Converting: {notebook_name}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✓ Success: {notebook_name}")
        return True
    else:
        print(f"✗ Failed: {notebook_name}")
        print(result.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Batch convert OneNote notebooks to Markdown"
    )
    parser.add_argument(
        "notebooks",
        nargs="+",
        help="Notebook names to convert"
    )
    parser.add_argument(
        "-o", "--output",
        default="./onenote_output",
        help="Output directory"
    )
    parser.add_argument(
        "-c", "--config",
        help="JSON config file with notebook settings"
    )
    parser.add_argument(
        "--section",
        help="Convert specific section only"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum pages to convert"
    )
    parser.add_argument(
        "--start-page",
        type=int,
        help="Start from page number"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Load config if provided
    config = {}
    if args.config:
        config = load_config(args.config)

    # Prepare options
    options = {
        "section": args.section,
        "max_pages": args.max_pages,
        "start_page": args.start_page,
        "verbose": args.verbose
    }

    # Convert notebooks
    results = []
    for notebook in args.notebooks:
        notebook_options = config.get(notebook, {})
        notebook_options.update(options)

        output_dir = Path(args.output) / notebook
        success = convert_notebook(notebook, str(output_dir), notebook_options)
        results.append((notebook, success))

    # Print summary
    print("\n=== Conversion Summary ===")
    for notebook, success in results:
        status = "✓ Success" if success else "✗ Failed"
        print(f"{status}: {notebook}")

    # Return error code if any failed
    sys.exit(0 if all(r[1] for r in results) else 1)


if __name__ == "__main__":
    main()
