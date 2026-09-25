"""Command-line entry point for bookmark-doctor."""
from __future__ import annotations

import argparse
import sys

from .core import check_links, find_duplicates, is_ok, parse_bookmarks


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bookmark-doctor",
        description="Find duplicate and dead links in an exported browser bookmarks file.",
    )
    parser.add_argument("file", help="path to a bookmarks.html file (Netscape bookmark format)")
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="fetch each URL to find dead links (makes network requests)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=8.0,
        help="per-request timeout in seconds (default: 8.0)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="number of concurrent link checks (default: 10)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    try:
        with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
            html = fh.read()
    except OSError as exc:
        print(f"error: could not read {args.file}: {exc}", file=sys.stderr)
        return 1

    entries = parse_bookmarks(html)
    if not entries:
        print("no bookmarks found in file")
        return 0

    print(f"parsed {len(entries)} bookmarks")

    dupes = find_duplicates(entries)
    if dupes:
        print(f"\n{len(dupes)} duplicate URL(s):")
        for url, group in dupes.items():
            titles = ", ".join(f'"{entry.title}"' for entry in group)
            print(f"  {url}")
            print(f"    seen {len(group)}x: {titles}")
    else:
        print("\nno duplicate URLs")

    if args.check_links:
        unique_urls = sorted({entry.url for entry in entries})
        print(
            f"\nchecking {len(unique_urls)} unique link(s) "
            f"(timeout={args.timeout}s, workers={args.workers})..."
        )
        results = check_links(unique_urls, timeout=args.timeout, workers=args.workers)
        dead = {url: status for url, status in results.items() if not is_ok(status)}
        if dead:
            print(f"\n{len(dead)} broken link(s):")
            for url, status in sorted(dead.items()):
                print(f"  [{status}] {url}")
        else:
            print("\nall links reachable")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
