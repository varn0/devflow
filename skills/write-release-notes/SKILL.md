---
name: write-release-notes
description: Use when preparing a release, writing changelog entries, or the user asks for release notes. Reads git history since the last production tag and generates user-friendly release notes covering only features and fixes.
user-invocable: true
argument-hint: [tag or version to diff from, e.g. v1.2.0]
---

Generate user-friendly release notes from git history since the last production tag and write them to `RELEASE_NOTES.md`.

## How It Works

1. **Find the baseline tag** — the last production release:
   ```bash
   git describe --tags --abbrev=0 --match "v*"
   ```
   - If `$ARGUMENTS` provides a specific tag/version, use that instead.
   - If no tags exist, use the root commit (`git rev-list --max-parents=0 HEAD`).

2. **Read commits since that tag:**
   ```bash
   git log <tag>..HEAD --oneline --no-merges
   ```

3. **Filter commits** — keep ONLY:
   - `feat:` or `feature:` — new functionality
   - `fix:` or `bugfix:` — bug fixes
   - Commits whose message clearly describes a user-facing change even without a conventional prefix

   **Discard** all of these:
   - `chore:`, `build:`, `ci:`, `deps:`
   - `docs:`, `doc:`
   - `refactor:`, `style:`, `test:`, `tests:`
   - `plan:`, `wip:`
   - Merge commits, version bumps, changelog updates

4. **Group by category:**
   - **New** — features, new capabilities
   - **Fixed** — bug fixes, corrections

5. **Write the release notes** to `RELEASE_NOTES.md` in the repo root. If the file already exists, prepend the new section above existing content. Use this format:

   ```markdown
   ## What's New in <version>

   ### New
   - <User-friendly description of feature>
   - ...

   ### Fixed
   - <User-friendly description of fix>
   - ...
   ```

## Writing Style

- Write for **end users**, not developers.
- Describe **what changed for the user**, not what code changed.
- Use plain language — no file paths, function names, or technical jargon.
- Start each bullet with a verb: "Added...", "Fixed...", "Improved...".
- One bullet per change. Combine closely related commits into a single bullet.
- If a commit message is unclear, read the diff (`git show <sha> --stat`) to understand the change before writing the bullet.

## What This Skill Does NOT Do

- Does NOT create git tags or bump versions.
- Does NOT commit or push the release notes.
- Does NOT include internal/infra changes — only user-facing work.
