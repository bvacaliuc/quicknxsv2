# quicknxsv2 (neutrons/quicknxs) — Agent Instructions

## Project identity
This is the **upstream institutional project** (`neutrons/quicknxs`) for the
Magnetism Reflectometer data reduction GUI at ORNL/SNS.  It is distinct from
`quicknxsv1` (`bvacaliuc/quicknxs`), which is a fork.  Changes here follow
SNS/ORNL data-reduction conventions and require `mr_reduction` / `mantid`
compatibility.

## Layout and tools
- **`src/` layout** — package lives at `src/quicknxs/`; tests under `test/`
- **Build tool:** `pixi` (no Makefile); use `pixi run <task>` for all operations
- **Key pixi tasks:** `test`, `conda-build`, `audit-deps`, `build-docs`
- **Versioning:** Git-tag-based via `versioningit` (hatchling backend)
- **Platform:** linux-64 only

## Branching model
- **`next`** — integration branch; all PRs target `next`
- **`qa`** — staging; promoted from `next`
- **`main`** — stable release; promoted from `qa`
- Never commit directly to `next`, `qa`, or `main`

## Branch naming conventions
- `EWM{number}_{description}` — work items tracked in the SNS work management system
- `bugfix_{description}` or `fix_{description}` — bug fixes
- `{user}/{description}` — personal/agentic branches (see Agent workflow below)
- `dependabot/**`, `pre-commit-ci-*` — automated dependency/tooling branches

## CI/CD (`.github/workflows/test_and_deploy.yml`)
- **Triggers:** push to `next`/`qa`/`main`, pull requests, `v*` tags, manual dispatch
- **`tests` job:** pytest with coverage → Codecov upload
- **`build` job:** conda package build → conda-verify
- **`publish` job:** on `v*` tags only — uploads to Anaconda (label `rc` or `main`)
- **`deploy-dev` job:** on push to `next` only — triggers GitLab CI dev deployment
  ⚠️  Merges to `next` automatically trigger a dev environment deployment.
- **Lockfile updates:** monthly via `update-lockfile.yml`, targets `next`

## Required secrets
- `CODECOV_TOKEN` — coverage uploads
- `ANACONDA_TOKEN` — conda package publishing (release only)
- `GITLAB_DEPLOY_TOKEN` — dev deployment trigger (on `next` pushes)

## Pre-commit hooks
Pre-commit runs ruff (lint + format) automatically; CI (`pre-commit.ci`) will
push auto-fixes to PRs.  The `pixi-lock-check` hook runs at pre-push stage.
Do not bypass pre-commit; it is enforced in CI.

## Test data
Integration tests use `git-lfs`; the `test/data` submodule must be initialised.
Unit and UI tests do not require LFS.

## Agent workflow for this repository
This is an institutional repo with controlled write access.  Claude operates
under the following constraints:

**Read-only via `origin`:**
```bash
git fetch origin        # OK
git log origin/next     # OK
git push origin ...     # NOT permitted
```

**Branch creation and push is performed by the human contributor.**
The agreed convention is `{user}/{feature-description}` for agentic branches.

**Draft PR creation via PAT:**
After the human has pushed a `{user}/` branch, Claude may use the PAT
(extracted from the `upstream` remote URL) to open a **draft PR** targeting
`next` via the GitHub REST API:
```
POST https://api.github.com/repos/neutrons/quicknxs/pulls
{ "draft": true, "head": "{user}/{feature}", "base": "next", ... }
```

**Claude's session workflow:**
1. Prepare all changes for a logical task on the local `{user}/{feature-description}`
   branch (or a task-specific branch agreed with the user).
2. Commit locally with descriptive messages.
3. Ask the user to push: `git push origin {user}/{feature-description}`.
4. Once confirmed, create a draft PR via the PAT.
5. The user reviews and promotes the PR from draft to ready when satisfied.

**Do not** open non-draft PRs, merge PRs, or modify branch protection settings
on this repository without explicit instruction.

## Plotting architecture (`src/quicknxs/ui/mplwidget.py`)

Project-specific class wiring (reusable matplotlib-storage facts live in
the parent repo's `setup/patterns/ui-aspects.md` and are not duplicated here):

- **`MplCanvas`** — owns one `fig` + one `ax` (single subplot)
- **`MPLWidget`** — owns one `MplCanvas`, two stacked toolbars (Generic + Reflectivity), and a `cplot` reference
- **`NavigationToolbar`** — base class with Save Data / Print buttons; `self.canvas.ax` always refers to the correct axes for that widget
- **`NavigationToolbarGeneric`** — for 2D plots (imshow/pcolormesh); has Log toggle
- **`NavigationToolbarReflectivity`** — for 1D errorbar plots; has XLog, YLog, RQ⁴, Lines

When implementing "Save Data" or any other code that reads live Axes
content (iterating `ax.containers`, `ax.images`, `ax.collections`, dealing
with gouraud shading, `imshow` origin round-trip, label location on
`ErrorbarContainer` vs data line, etc.), **load**
`setup/patterns/ui-aspects.md` — the pitfalls there were characterised on
this codebase and apply in full.

## Off-specular / GISANS data shape (data-processing learning)

The reason the pcolormesh plots here use `shading="gouraud"` with 2D
coordinate arrays (and not 1D edges) is **not** a cosmetic choice — it
reflects the underlying reduction output:

- Off-specular and GISANS Q-space output is **inherently irregular**.
  Each `(detector pixel, time-of-flight bin)` cell maps to a unique
  `(Qx, Qz)` (or `(Qx, Qy)` for GISANS), because Q depends on both
  scattering angle and wavelength. There is no 1D x-axis and no 1D
  y-axis that the grid aligns to — the coordinates are fundamentally 2D.
- **Different runs produce surfaces with different column counts** (the
  ToF binning or pixel masking can vary run-to-run). Any code that
  overlays or exports multiple runs must keep each run's mesh separate;
  you cannot concatenate onto a shared coordinate axis.
- **Do not try to collapse to 1D.** A "helpful" refactor that replaces
  the 2D coordinate arrays with 1D edges will silently corrupt any
  pixel whose Q-vector doesn't lie on the assumed regular grid — and
  that is every pixel in off-specular analysis.
- The matplotlib-side consequences (how `get_coordinates` /
  `get_array` behave, what export code has to carry) are in
  `setup/patterns/ui-aspects.md`. The fact above is the *reason* those
  matplotlib rules matter; keep them in sync if the reduction output
  shape ever changes.
