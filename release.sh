#!/usr/bin/env bash
# Cut a single-file SDP Explorer release.
#
# Packs static/ into one offline HTML file (via build_release.py), tags the
# current commit, and publishes a GitHub Release with the HTML attached.
# Used instead of CI because GitHub Actions is disabled at the org level.
#
# Usage:
#   ./release.sh v1.2.0            # build, tag, and publish the release
#   ./release.sh v1.2.0 --dry-run  # build only; no tag, no push, no release
#
# Requirements: python3, gh (authenticated), a clean checkout on the commit
# you want to release.
set -euo pipefail

REPO="databricks-solutions/sdp-explorer"

tag="${1:-}"
dry_run="${2:-}"

if [[ -z "$tag" ]]; then
  echo "usage: $0 <version-tag> [--dry-run]   e.g. $0 v1.2.0" >&2
  exit 2
fi
if [[ ! "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "error: tag '$tag' should look like v1.2.0" >&2
  exit 2
fi

out="dist/sdp-explorer-${tag}.html"

echo ">> building $out"
python3 build_release.py -o "$out"

if [[ "$dry_run" == "--dry-run" ]]; then
  echo ">> dry run: built $out; skipping tag, push, and release"
  exit 0
fi

if git rev-parse "$tag" >/dev/null 2>&1; then
  echo ">> tag $tag already exists locally; reusing it"
else
  echo ">> tagging $tag"
  git tag "$tag"
fi

echo ">> pushing tag $tag"
git push origin "$tag"

echo ">> publishing GitHub Release $tag"
gh release create "$tag" "$out" \
  --repo "$REPO" \
  --title "SDP Explorer $tag" \
  --notes "**SDP Explorer — single-file offline build.**

Download \`$(basename "$out")\` below and open it in any browser. No install, no server, no internet required: all scripts, images, and fonts are embedded."

echo ">> done: https://github.com/$REPO/releases/tag/$tag"
