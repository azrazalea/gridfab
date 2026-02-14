---
name: gridfab-release
description: Prepare and publish a new GridFab release. Use when cutting a new version, tagging a release, updating version numbers, or consolidating the changelog for release. Triggers on tasks like "prepare a release", "bump the version", "tag v0.2.0", "cut a release".
---

# GridFab Release Process

## Pre-Release Checklist

1. **Ensure CI is green** on main: check https://github.com/azrazalea/gridfab/actions
2. **Run tests locally**: `python -m pytest tests/ -v`
3. **Verify no uncommitted changes**: `git status`

## Version Bump

Update the version string in all three locations:

1. `pyproject.toml` — `version = "X.Y.Z"` under `[project]`
2. `src/gridfab/__init__.py` — `__version__ = "X.Y.Z"`
3. `GRIDFAB_PROJECT_SPEC.md` — version reference near the top

GridFab uses [Semantic Versioning](https://semver.org/).

## Consolidate Changelog

In `CHANGELOG.md`:

1. Move all entries from `## [Unreleased]` into a new `## [X.Y.Z]` section
2. Leave `## [Unreleased]` empty (but keep the heading)
3. Review entries — consolidate, reword for clarity, remove internal-only changes
4. Ensure categories follow Keep a Changelog: Added, Changed, Deprecated, Removed, Fixed, Security

The release workflow extracts this section for the GitHub Release body.

## Commit, Tag, Push

```bash
git add -A
git commit -m "Release vX.Y.Z"
git push
git tag vX.Y.Z
git push origin vX.Y.Z
```

## What Happens Automatically

The GitHub Actions workflow (`.github/workflows/release.yml`) triggers on `v*` tags and:

1. Runs tests on Windows, macOS, and Linux
2. Builds Nuitka binaries (CLI + GUI) for all three platforms
3. Includes project docs (README, LICENSE, CHANGELOG, INSTRUCTIONS), source code, and tests in archives
4. Extracts the tagged version's section from CHANGELOG.md for the release body
5. Creates a GitHub Release with platform archives (`gridfab-{platform}-X.Y.Z.{zip,tar.gz}`)
6. Appends auto-generated contributor/commit notes

## Post-Release

- Verify the release at https://github.com/azrazalea/gridfab/releases
- Download and spot-check at least one platform archive
- If something went wrong: delete the tag (`git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z`), fix, and re-tag
