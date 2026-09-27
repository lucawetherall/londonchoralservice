# Serve an allowlist, not the repo — design doc

**Date:** 2026-09-27
**Author:** Luca Wetherall (with Claude)
**Status:** Implemented 2026-09-27 (see Rollout)
**Related:** [.github/workflows/deploy-pages.yml](../../../.github/workflows/deploy-pages.yml), [scripts/stage_site.py](../../../scripts/stage_site.py), [scripts/check_live_site.py](../../../scripts/check_live_site.py), [tests/test_stage_site.py](../../../tests/test_stage_site.py), [.github/workflows/indexnow.yml](../../../.github/workflows/indexnow.yml)

---

## Problem

GitHub Pages deployed this public repo straight from `main /` (branch mode), so every committed file was on the live domain. That included `logs/ads-changes.md` (keywords, negatives, the budget cap and the reasoning behind them), `MANUAL-ACTIONS-REQUIRED.md`, `CLAUDE.md`, `docs/`, the Google Ads scripts, `data/`, `.claude/` and the repo graph. On 27 September a request for each file found 534 of 535 internal files returning 200. Only `.github/` was withheld.

## Decision

Deploy from a GitHub Actions workflow that publishes an **allowlist**.

- `scripts/stage_site.py` selects the files that match `PUBLIC`: root `*.html`, the HTML in `areas/`, `compare/`, `destinations/` and `music-guides/`, all of `assets/`, `css/`, `fonts/` and `js/`, and the root files fetched by name. It copies them byte for byte into `_site/` and builds nothing. `build.sh` stays the build, run locally, and its output stays committed.
- `.github/workflows/deploy-pages.yml` runs the script's tests, stages the site, uploads it with `actions/upload-pages-artifact` and deploys it with `actions/deploy-pages` on every push to `main`. Pull requests run the same checks and stop before the deploy.

An allowlist rather than a denylist, because a new internal file should be private by default, and a new public directory should fail loudly rather than leak quietly.

## Checks

Each check fails the build locally (`build.sh` runs the script last) and in CI, and nothing is staged:

1. **Nothing internal.** `PRIVATE` (logs/, docs/, scripts/, data/, tests/, partials/, graphify-out/, and any `.md`, `.py`, `.sh`, `.yml`, `.yaml`, `.json` or `.csv` file) is refused even if `PUBLIC` is widened to `**`. So is every hidden path and every symlink.
2. **Sitemap coverage.** Every `<loc>` in `sitemap.xml` maps to a published file, in the order Pages looks them up: the file, then `.html`, then a directory `index.html`.
3. **Reference coverage.** Every internal URL in a published file resolves to a published file. That covers HTML attributes (`href`, `src`, `srcset`, `poster`, og/twitter `content` and the rest), CSS `url()` and `@import` both inline and in `css/`, absolute `londonchoralservice.com` URLs anywhere (JSON-LD, the llms files, robots), and quoted root paths in scripts and the web manifest. A target that exists in the repo but is not published fails the build, because it is an allowlist gap. A target that exists nowhere is a broken link and only warns.
4. **Fetched by name.** `index.html`, `404.html`, `robots.txt`, `favicon.ico` and the IndexNow key file (found by the same rule as `scripts/indexnow-ping.py`).

When this was written the script published 203 files (17.1 MB) with no errors and no warnings. `tests/test_stage_site.py` covers each check, and each test was confirmed to fail when its check was disabled.

## What else changed

- **IndexNow.** `indexnow.yml` ran on `page_build`, an event that only branch mode emits, so the switch would have stopped the pings without a word. It is now also a reusable workflow, which `deploy-pages.yml` calls after each successful deploy. `page_build` stays so a rollback keeps pinging.
- **Custom domain and HTTPS.** Both are repository settings (with the domain verified at account level), so they carry over. Actions mode ignores the `CNAME` file and `.nojekyll`; both stay in the repo, and `CNAME` is still published, harmlessly.
- **Verification.** `scripts/check_live_site.py` requests every published file (expects 200), every other file on the deployed branch and each internal directory (expects 404), every URL in the live sitemap (200), and the http→https and github.io→domain redirects. Each request carries a unique query string so the CDN's ten-minute cache cannot hide a stale deploy.

## Rollout

1. Pull request with the stage check green.
2. The owner sets Settings → Pages → Build and deployment → Source to **GitHub Actions**. The site keeps serving the last branch deployment until the next deploy.
3. Merge. The push deploys the allowlisted artifact and pings IndexNow.
4. `python3 scripts/check_live_site.py` passes.

**Rollback:** set Source back to "Deploy from a branch" (`main`, `/ (root)`). The branch build republishes the whole repo within a couple of minutes, which restores the old site and the leak together.

## Non-goals

- **Making the repo private.** The repo stays public on GitHub, so its files stay readable there. This change takes them off the website and out of its search footprint. Pages on a private repo needs a paid GitHub plan, which is an owner decision.
- **Security headers, extensionless redirects, `www` TLS.** These are GitHub Pages limits this change leaves as they were (MANUAL-ACTIONS-REQUIRED.md §5 and §15).
- **Building in CI.** The workflow never runs `build.sh`. The committed output is what ships.
