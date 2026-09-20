# Local Novel Project Implementation Plan

**Goal:** Convert the existing reader repository into a local, Harness-ready novel project without changing published prose or exposing private spoilers.

**Architecture:** Keep `dist/` as the public deployment artifact and keep all spoiler-bearing sources under ignored `work/`. A standard-library Python tool extracts chapters, scaffolds new chapters, rebuilds the monolithic reader, and validates continuity-sensitive structure.

**Tech Stack:** Python 3 standard library, HTML fragments, JSON manifest, unittest, GitHub Pages.

---

### Task 1: Add project operating rules

**Files:**
- Create: `AGENTS.md`
- Create: `README.md`
- Modify: `.gitignore`

1. Document the public/private boundary and required read order.
2. Document the one-chapter workflow and publishing gate.
3. Ignore secrets, local caches, backups, and the complete `work/` tree.
4. Run `git check-ignore work/author-backstage.md` and expect the file to remain ignored.

### Task 2: Add the manuscript tool

**Files:**
- Create: `scripts/novel_project.py`
- Create: `tests/test_novel_project.py`

1. Write tests for section extraction, exact no-op rebuilding, chapter scaffolding, TOC rebuilding, and validation failures.
2. Implement `extract`, `new`, `build`, `validate`, and `status` commands using only the Python standard library.
3. Run `python3 -m unittest discover -s tests -v` and expect all tests to pass.

### Task 3: Initialize private local sources

**Files:**
- Create: `work/manuscript/manifest.json`
- Create: `work/manuscript/chapters/001.html` through `030.html`
- Create: `work/HARNESS_HANDOFF.md`
- Create: `work/project-state.json`

1. Run `python3 scripts/novel_project.py extract` against the current reader.
2. Verify the manifest contains thirty ordered chapters.
3. Write the spoiler-safe operational handoff plus the private read order and Chapter 31 start state.
4. Confirm all private files remain ignored by Git.

### Task 4: Prove a no-change rebuild

**Files:**
- Verify: `dist/index.html`

1. Record the chapter-title/body hashes from the existing page.
2. Run `python3 scripts/novel_project.py build`.
3. Run `python3 scripts/novel_project.py validate`.
4. Compare pre/post chapter hashes and expect no prose changes.
5. Run `git diff --check` and inspect `git diff -- dist/index.html`.

### Task 5: Deliver the local handoff

1. Run `python3 scripts/novel_project.py status`.
2. Confirm the next chapter is 31 and the last published chapter is 30.
3. Provide the exact local directory and the first Harness prompt.
4. Commit only public tooling and documentation after user authorization; never add `work/`.
