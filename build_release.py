#!/usr/bin/env python3
"""Pack SDP Explorer into one self-contained HTML file for offline distribution.

Reads static/index.html and inlines every local asset (the two GSAP scripts,
the logo and favicon SVGs) plus the remote Google Fonts (CSS + woff2 files,
base64-embedded) so the result opens by double-clicking with zero network
access. The static/ tree stays the single source of truth; the packed file is
a pure derivative written to dist/ (which is gitignored).

Usage:
    python build_release.py                      # -> dist/sdp-explorer.html
    python build_release.py -o path/to/out.html
    python build_release.py --no-fonts           # keep the Google Fonts <link>

Standard library only, so CI needs no pip install.
"""
from __future__ import annotations

import argparse
import base64
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

# A browser-like UA so Google Fonts serves the compact woff2 files.
FONT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Local assets referenced from index.html, inlined as data: URIs. The key is the
# exact attribute value in the source; the value is (path, mime).
DATA_URI_ASSETS = {
    "favicon.svg": (STATIC / "favicon.svg", "image/svg+xml"),
    "databricks-logo.svg": (STATIC / "databricks-logo.svg", "image/svg+xml"),
}

# Local scripts, inlined as <script>...</script>.
SCRIPT_ASSETS = ["gsap.min.js", "gsap-flip.min.js"]


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": FONT_UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def data_uri(raw: bytes, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def inline_data_uri_assets(html: str) -> str:
    """Replace href/src="asset.svg" with base64 data: URIs."""
    for name, (path, mime) in DATA_URI_ASSETS.items():
        raw = path.read_bytes()
        uri = data_uri(raw, mime)
        # Match src="asset" or href="asset" with either quote style.
        pattern = re.compile(r'((?:src|href)=)(["\'])' + re.escape(name) + r'\2')
        html, n = pattern.subn(lambda m: f"{m.group(1)}{m.group(2)}{uri}{m.group(2)}", html)
        if n == 0:
            print(f"  ! warning: no reference to {name} found", file=sys.stderr)
        else:
            print(f"  inlined {name} ({len(raw):,} B) in {n} place(s)")
    return html


def inline_scripts(html: str) -> str:
    """Replace <script src="local.js"></script> with the file contents inline."""
    for name in SCRIPT_ASSETS:
        js = (STATIC / name).read_text(encoding="utf-8")
        # A literal </script> inside injected JS would close the tag early.
        js = js.replace("</script", "<\\/script")
        pattern = re.compile(
            r'<script\s+src=(["\'])' + re.escape(name) + r'\1\s*>\s*</script>'
        )
        replacement = f"<script>\n{js}\n</script>"
        html, n = pattern.subn(lambda m: replacement, html, count=1)
        if n == 0:
            print(f"  ! warning: no <script src=\"{name}\"> found", file=sys.stderr)
        else:
            print(f"  inlined {name} ({len(js):,} B)")
    return html


def embed_fonts(html: str) -> str:
    """Fetch the Google Fonts stylesheet, base64 every woff2, inline as <style>.

    On any network failure this warns and leaves the original <link> in place
    rather than failing the whole build.
    """
    link_re = re.compile(
        r'<link\s+href=(["\'])(https://fonts\.googleapis\.com/css2[^"\']*)\1'
        r'[^>]*rel=(["\'])stylesheet\3[^>]*>'
    )
    m = link_re.search(html)
    if not m:
        print("  ! warning: Google Fonts <link> not found; skipping font embed",
              file=sys.stderr)
        return html

    css_url = m.group(2)
    try:
        css = _fetch(css_url).decode("utf-8")
        font_urls = sorted(set(re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)))
        total = 0
        for url in font_urls:
            raw = _fetch(url)
            total += len(raw)
            css = css.replace(url, data_uri(raw, "font/woff2"))
        print(f"  embedded {len(font_urls)} font files ({total:,} B)")
    except Exception as exc:  # network/DNS/timeout — degrade, don't crash
        print(f"  ! warning: could not embed fonts ({exc}); keeping remote <link>",
              file=sys.stderr)
        return html

    style_block = f"<style>\n/* Google Fonts, embedded for offline use */\n{css}\n</style>"
    # Drop the preconnect hints (useless offline) and replace the stylesheet link.
    html = re.sub(
        r'\s*<link\s+rel=(["\'])preconnect\1\s+href=["\']https://fonts\.(?:googleapis|gstatic)\.com["\'][^>]*>',
        "",
        html,
    )
    html = link_re.sub(lambda _m: style_block, html, count=1)
    return html


def build(output: Path, with_fonts: bool) -> None:
    src = STATIC / "index.html"
    print(f"reading {src.relative_to(ROOT)} ({src.stat().st_size:,} B)")
    html = src.read_text(encoding="utf-8")

    html = inline_scripts(html)
    html = inline_data_uri_assets(html)
    if with_fonts:
        html = embed_fonts(html)
    else:
        print("  skipping font embed (--no-fonts); Google Fonts <link> kept")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print(f"\nwrote {output} ({output.stat().st_size:,} B)")

    leftover = re.findall(r'(?:src|href)=["\'](?!data:|#|https?://)([^"\']+\.(?:js|css|svg|png|woff2?))["\']', html)
    if leftover:
        print(f"  ! warning: unresolved local references remain: {sorted(set(leftover))}",
              file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "dist" / "sdp-explorer.html",
                    help="output HTML path (default: dist/sdp-explorer.html)")
    ap.add_argument("--no-fonts", action="store_true",
                    help="keep the Google Fonts <link> instead of embedding the fonts")
    args = ap.parse_args()
    build(args.output, with_fonts=not args.no_fonts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
