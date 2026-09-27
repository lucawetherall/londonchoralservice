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

- `scripts/stage_site.py` selects the files that match `PUBLIC`: root `*.html`, the HTML in `areas/`, `compare/`, `destinations/` and `music-guides/`, the web asset types in `assets/`, `css/`, `fonts/` and `js/`, and the root files fetched by name. It copies them byte for byte into a directory outside the checkout and builds nothing. `build.sh` stays the build, run locally, and its output stays committed.
- `.github/workflows/deploy-pages.yml` runs the script's tests, stages the site, uploads it with `actions/upload-pages-artifact` and deploys it with `actions/deploy-pages` on every push to `main`. Pull requests run the same checks and stop before the deploy.

An allowlist rather than a denylist, because a new internal file should be private by default, and a new public file should fail loudly rather than go missing quietly.

## Checks

Each check fails the build locally (`build.sh` runs the script last) and in CI, and nothing is staged:

1. **Every file is published or internal, never both and never neither.** `PRIVATE` (logs/, docs/, scripts/, data/, tests/, partials/, graphify-out/, and any `.md`, `.py`, `.sh`, `.yml`, `.yaml`, `.json` or `.csv` file, matched ignoring case) is refused even if `PUBLIC` is widened to `**`. Hidden paths and names with control characters are internal; a published file may not be a symlink. A file that matches neither list, such as a verification file dropped at the root, fails until someone adds it to one of them.
2. **Sitemap coverage.** Every `<loc>` in `sitemap.xml` maps to a published file, in the order Pages looks them up: the file, then `.html`, then a directory `index.html`.
3. **Reference coverage.** Every same-site URL in a published file resolves to a published file. That covers HTML attributes (`href`, `src`, `srcset`, `poster`, og/twitter `content`, and `data-*` values that look like links, such as the form pages' `data-redirect` to `thank-you.html`), CSS `url()` and `@import` both inline and in `css/`, absolute `londonchoralservice.com` URLs anywhere (JSON-LD, the llms files, robots), and quoted root paths in scripts and the web manifest. A target that exists but is not published is an allowlist gap; a target that exists nowhere is a broken link, or a file never committed. Both fail.
4. **Fetched by name.** `index.html`, `404.html`, `robots.txt`, `favicon.ico` and the IndexNow key file (found by the same rule as `scripts/indexnow-ping.py`).

In a copy of the repo without `.git` (`tests/test_register_generators.py` runs the build in one), the script checks the files on disk instead of git's list. It never borrows the file list of an enclosing checkout.

When this was written, the script published 297 files (21.3 MB) with no errors. `tests/test_stage_site.py` covers each check, and each test was confirmed to fail when its check was disabled.

## What else changed

- **IndexNow.** `indexnow.yml` ran on `page_build`, an event that only branch mode emits, so the switch would have stopped the pings without a word. It is now also a reusable workflow, which `deploy-pages.yml` calls after each successful deploy. `page_build` stays so a rollback keeps pinging. A failed ping marks the deploy run failed even though the site deployed; the job names show which part failed.
- **Branch mode is refused.** Pages still accepts Actions deployments while its source is a branch, so the branch build and this workflow would race on every push. The deploy job reads the Pages source first and fails unless it is GitHub Actions. That also makes an accidental switch back visible.
- **Custom domain and HTTPS.** Both are repository settings (with the domain verified at account level), so they carry over. Actions mode ignores the `CNAME` file and `.nojekyll`; both stay in the repo, and `CNAME` is still published, harmlessly.
- **Verification.** `scripts/check_live_site.py` requests every published file (expects 200), every other file on the deployed branch (expects 404, reported per top-level directory), every URL in the live sitemap (200), and the http→https and github.io→domain redirects. The CDN in front of Pages ignores query strings, so no request can bypass its cache (ten minutes for files, sometimes longer for 404s). Instead, each answer's `Date` minus `Age` gives when the CDN fetched it. A wrong answer fetched before the latest github-pages deployment succeeded (read from the public GitHub API) counts as stale, exit 2, rather than failed, exit 1.

## Rollout

1. Pull request with the stage check green.
2. The owner sets Settings → Pages → Build and deployment → Source to **GitHub Actions**. The site keeps serving the last branch deployment until the next deploy.
3. Merge. The push deploys the allowlisted artifact and pings IndexNow.
4. `python3 scripts/check_live_site.py` passes. On exit 2, re-run after ten minutes.

**Rollback:** set Source back to "Deploy from a branch" (`main`, `/ (root)`). The branch build republishes the whole repo within a couple of minutes, which restores the old site and the leak together. The deploy job then fails on every push by design; disable "Deploy site to Pages" in the Actions tab until the source is switched back.

## Non-goals

- **Making the repo private.** The repo stays public on GitHub, so its files stay readable there. This change takes them off the website and out of its search footprint. Pages on a private repo needs a paid GitHub plan, which is an owner decision.
- **`.well-known/`.** Hidden paths are always internal, and `upload-pages-artifact` drops dotfiles by default. Nothing needs one today; serving one would take a `PUBLIC` exception and `include-hidden-files: true`.
- **Security headers, extensionless redirects, `www` TLS.** These are GitHub Pages limits this change leaves as they were (MANUAL-ACTIONS-REQUIRED.md §5 and §15).
- **Building in CI.** The workflow never runs `build.sh`. The committed output is what ships.
