# bookmark-doctor

Bookmarks rot. You save a page, forget about it, and eighteen months later
the link is a 404, or a redirect to a domain-squatter, or you saved the same
article twice from two different tabs. Browsers never tell you any of this
themselves — they'll happily keep a dead bookmark forever. This is a small
command-line tool that reads the bookmarks file your browser can export and
tells you what's broken.

## What it does

Every major browser can export bookmarks as an HTML file in the old
Netscape bookmark format (that's the actual name of the format — it dates
back to Netscape Navigator and every browser since has kept using it for
import/export). `bookmark-doctor` parses that file and reports:

- duplicate URLs saved more than once, wherever they live in your folders
- dead links, if you ask it to actually check (`--check-links`), including
  timeouts, DNS failures, and HTTP error codes

It does not touch your browser's profile directly and does not modify the
input file. It only reads the export and prints a report.

## Getting a bookmarks export

- Chrome / Edge / Brave: `chrome://bookmarks` → the three-dot menu → Export bookmarks
- Firefox: Bookmarks → Manage Bookmarks → Import and Backup → Export Bookmarks to HTML
- Safari: File → Export Bookmarks

## Install

No dependencies beyond the Python standard library. Python 3.9+.

```
pip install .
```

or just run it in place:

```
python -m bookmark_doctor path/to/bookmarks.html
```

## Usage

```
$ bookmark-doctor bookmarks.html
parsed 812 bookmarks

3 duplicate URL(s):
  https://example.com/some-article
    seen 2x: "Some Article", "Some Article (2)"
  https://news.example.org/2019/report
    seen 3x: "Interesting report", "report - saved again", "read later"

$ bookmark-doctor bookmarks.html --check-links --workers 20
parsed 812 bookmarks

no duplicate URLs

checking 798 unique link(s) (timeout=8.0s, workers=20)...

14 broken link(s):
  [404] https://example.com/moved-page
  [timeout] https://old-startup-that-died.io/
  [Name or service not known] https://typo-domain.con/
  [500] https://example.net/broken-endpoint
```

Flags:

- `--check-links` — actually fetch every unique URL (HEAD, falling back to
  GET if the server rejects HEAD) and report anything that isn't a 2xx/3xx
  response. Off by default since it makes real network requests and can
  take a while on a large bookmark collection.
- `--json` — print one JSON object instead of the text report, with
  `bookmark_count`, `duplicates` (url, count, and the title/folder/add_date
  of each copy) and `broken` (url and status, or `null` if `--check-links`
  was not given). Nothing else is written to stdout in this mode.
- `--timeout SECONDS` — per-request timeout (default 8.0)
- `--workers N` — how many links to check concurrently (default 10)

## Why not just click through them

For a few dozen bookmarks, sure. Past a couple hundred, nobody actually
does this, which is exactly how you end up with a bookmarks bar that's
half dead links you've stopped trusting.

## License

MIT, see LICENSE.
