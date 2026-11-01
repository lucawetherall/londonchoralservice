# Handoff: ad tracking improvements and the WhatsApp Business Platform

Written 31 October 2026 for an agent starting fresh. It holds what that agent needs and `CLAUDE.md` doesn't: what was found and verified on 31 October, what has already changed, the gaps that remain, and the work in order, with the points where the owner decides. Read it once from top to bottom, then work one package at a time.

**Progress (1 Nov 2026):**
- WP1: the comment is reworded. The `form_error` read is due after 9 Nov.
- WP2: built, validate-only (`docs/superpowers/specs/2026-11-01-enquiry-conversion-design.md`). Creating the action and the privacy sentence wait for the owner.
- WP3: decision document written (`docs/superpowers/specs/2026-11-01-whatsapp-business-platform.md`); it recommends no go on the Cloud API.
- WP4 and WP5 wait on those decisions.

## 1. How to use this document

- It records the state on 31 October 2026. Numbers move, so pull them again before you act on any of them.
- The owner, Luca Wetherall (they/them in anything you write about them), has given a full mandate for London Choral Service work: decide, build, open and merge reviewed PRs, and verify live. Three things always need their explicit approval:
  - any change to the Google Ads account: one approval per change set, shown as current value → new value with a reason;
  - any GA4 or Search Console configuration change: shown the same way, after a dry run;
  - any business or privacy policy call, which covers everything in section 6.

  Batch these into one question.
- Nothing is ever sent by you. Client messages are drafts the owner sends. That rule covers WhatsApp too (section 6).
- No client names, phone numbers, emails, message text or ledger money figures go into the repo, a PR, a commit message or `logs/`. The repo is public. Private data stays in `~/lcs-private/`.

## 2. Read first, in this order

1. `CLAUDE.md`, all of it. The rules you will use most are in "Google Ads & GA4", the bookings ledger paragraph, "Email and invoices", and the enquiry assistant and pipeline paragraphs.
2. `docs/superpowers/specs/2026-10-14-cookieless-ad-attribution.md` and `docs/superpowers/specs/2026-10-23-cookieless-ad-source-design.md`: how an ad click is carried into an enquiry with consent and without it.
3. `partials/analytics.html`: Consent Mode v2, with every consent default set to denied. It also holds `lcsAttribution()`, `lcsAdVisit()`, `lcsClickIds()`, `lcsShortRef()` and `lcsLabelMessage()`, which adds "Sent from …" and "Ref: XXXX" / "Ad visit: …" to WhatsApp and email links when they are clicked. Edit the partial and run `./build.sh`; never edit the expanded copy in a page.
4. `js/form.js`: the web form. It sends to Web3Forms with an hCaptcha guard and the `botcheck` honeypot, and adds the attribution fields. Since 31 Oct it also waits for the captcha, retries once and offers fallbacks (section 3).
5. `scripts/reports/enquiry_sources.py`: how every enquiry is graded A, B or C by ad source. This grading is the business's real measure of the ads, because Google's own conversion figures can't measure this volume.
6. `scripts/ads/lookup_ref.py` (four-character ref → gclid), `scripts/ads/upload_bookings.py` (the "Booked job" upload through the Data Manager API), `scripts/bookings/pipeline.py` (`~/lcs-private/enquiries.csv`, which holds no names) and `scripts/bookings/assistant_io.py`.
7. `scripts/reports/weekly_review.py`, sections 3 (conversions), 5 (GA4), 5c (GoatCounter), 8 (wiring) and 9b (enquiries by ad source), and `.claude/agents/lcs-review-ads.md`.
8. `docs/utm-conventions.md`, `logs/ads-changes.md` and `logs/ga4-changes.md`, newest first. Check the logs before proposing anything, so you don't undo a recent change.

## 3. What was found and changed on 31 October

### Verified on the live site (pretend ad clicks, run by hand)
- **Cookies accepted:** the gclid, `utm_*` and campaign are kept (`lcsAttribution()`). A WhatsApp tap opens with "Sent from your 'Hire carol singers in London' page, via a Google ad. Ref: XXXX". `lookup_ref.py` turns that ref back into the click.
- **Cookies refused:** no click ID is kept. The landing page gets the label "Ad visit: christmas (christmas-carol-singers-2026)", which rides into WhatsApp and email messages and the form's `ad_visit` field. Internal links carry it to the next page as `?lcs_av=…`. Typing a URL directly drops it, which is correct.
- **Google Ads account:**
  - auto-tagging on;
  - enhanced conversions for leads on;
  - customer data terms accepted;
  - the GA4 link (8733881378) present;
  - all three landing pages report "all tags present".

### Changed (all merged and live)

| What | Where |
|---|---|
| Funeral campaign 23735776277 paused (spend guard: £125.64 in 28 days, no A or B enquiry) | `logs/ads-changes.md` |
| "WhatsApp or email click" (7796284061) primary → secondary. A tap is not a sent message: funeral showed 2 conversions with no enquiry behind them. "Submit lead form" is now the only primary action | #437, `logs/ads-changes.md` |
| GA4 custom dimension `error_detail` ("Form error detail") registered; the Monday report's section 5 prints it | #437, `logs/ga4-changes.md` |
| `form_error` now carries `error_detail` (Web3Forms' message or the network error's name) | #435 |
| Form: if the visitor submits before the hCaptcha widget renders, it waits up to 5 s and then asks them to tick it; a request that gets no answer (fetch `TypeError`) retries once (`error_type` "retry"); a reply that isn't JSON counts as a failure; after any failure the visitor gets "Email these details" and "Send on WhatsApp" buttons, filled in with what they typed | #436 |
| Christmas form: name, email, date and venue first; the rest under "More details" | #435 |

### What the data says
- **GA4, 90 days:** there were no `captcha` and no `incomplete` form errors. Only name and email are required. The only errors were three `submit` failures from one iPhone Safari visitor on christmas.html on 28 Oct. Their sends failed after passing validation and the captcha, probably because of a content blocker or the network. From 31 Oct, `error_detail` shows the reason.
- **Season since 1 Sep:** about £700 of ad spend produced 1 A-graded enquiry (Christmas) and no booking. Wedding (about £242) and funeral (about £287) produced none. Almost every enquiry and every booking came from organic search, referrals and direct contact. "Booked job" has never recorded a conversion because no booking carried a click reference. That matches the economics; it isn't a broken pipe.
- **Coverage:** Google Ads sees only consented visitors. GoatCounter counts every visitor (section 5c). Google's search-terms report covered 19% of the week's spend.
- **Calls:** not tracked. The site has no call buttons, by owner decision (WhatsApp and email come first); the phone number is shown as text.

## 4. Gaps that remain

1. **No conversion means "a message arrived".**
   - "Submit lead form" fires only for web forms, and only with consent.
   - WhatsApp and email enquiries are counted only in the private pipeline (A/B grades), never in Google Ads.
   - Since the 31 Oct change, Google Ads under-reports message enquiries rather than over-reporting taps. Manual CPC means bidding is unaffected, but the Ads UI understates results.
2. **The WhatsApp side of the pipeline is manual.**
   - Email and form enquiries reach the enquiry assistant through Zoho.
   - WhatsApp messages live only on the owner's phone. A WhatsApp enquiry reaches the pipeline only when the owner mentions it, and its "Ref:" line only when they paste it (the Monday question asks for it).
3. **The "Booked job" loop has never run with real data.** It works only for consented A-graded bookings, or form senders who ticked the ad-measurement box.
4. **Stale wording:** the comment in `partials/analytics.html` around line 83 still calls "WhatsApp or email click" the tap's Ads action as if it were primary. Reword it to say secondary, then rebuild.
5. **Legacy conversion actions** "Contact" (codeless) and "Contact (1)" (GA4 import) are secondary and enabled, kept for history. Leave them unless the owner wants them hidden. Never delete.
6. **Calls from ad viewers are invisible.** That is the owner's choice; record it rather than "fix" it.

## 5. Work packages, in order

### WP1. Small fixes (no approval needed beyond the PR)
- Reword the comment in `partials/analytics.html` (gap 4), run `./build.sh` (expect the ~165-file partial diff) and run `tests/run_ci_tests.py`.
- After 9 November, read `form_error` × `error_type` × `error_detail` in GA4. If one cause dominates (for example Web3Forms rejecting iOS requests), fix it in `js/form.js`, or propose a second submission route as an owner decision. Never remove the hCaptcha check or the honeypot.

### WP2. An "Enquiry received" offline conversion, for every channel (spec first)
**Goal:** Google Ads counts real enquiries, not taps, from every channel the consent rules allow.

**Design to spec in `docs/superpowers/specs/2026-11-xx-enquiry-conversion-design.md`:**
- **A new conversion action,** "Enquiry received" (category Submit lead form or Contact; secondary first, primary only once the owner agrees). Create it with a dated script in `scripts/ads/` (validate, approve, apply, log).
- **Upload rules:**
  - Upload from `~/lcs-private/enquiries.csv` the enquiries graded A: a gclid/gbraid/wbraid, or a "Ref:" resolved by `lookup_ref.py`.
  - Upload a form sender who ticked the ad-measurement box with their hashed email, as `upload_bookings.py` already does.
  - Use the enquiry's thread id as the order ID, so a row can never count twice.
  - Model it on `upload_bookings.py`: Data Manager API, validate-only by default, `--apply` after approval, a count only in `logs/ads-changes.md`.
- **Never upload B-graded enquiries.** "Ad visit" carries no click ID, and the owner rejected `url_passthrough` on 23 Oct 2026 on ICO consent grounds: don't reopen that without legal advice.
- **Schedule:** the Monday review proposes the upload ("UPLOAD would send n"), and the owner approves it with the rest of that week's decisions.
- **Verify** with a test conversion in validate-only mode, then one real A-graded enquiry.

### WP3. WhatsApp Business Platform: a feasibility and decision document (spec, no build)
**Goal:** decide whether the Cloud API should feed WhatsApp enquiries into the pipeline automatically. Write `docs/superpowers/specs/2026-11-xx-whatsapp-business-platform.md` for the owner. Check every fact below against Meta's current documentation on the day you write it, and cite it; these points are what to find out, not settled facts.

**What it would buy:**
- WhatsApp enquiries land in the pipeline automatically, with their "Ref:" or "Ad visit:" line parsed, so they are graded A/B like email.
- A-graded WhatsApp enquiries feed WP2's upload.
- The assistant drafts replies.
- The Monday report counts WhatsApp properly. It no longer needs the "did any WhatsApp enquiry turn into a booking?" question.

**Questions the spec must answer:**
1. **The number.**
   - Is 07356 042468 on the WhatsApp Business app or personal WhatsApp?
   - Can it run on the Cloud API while the owner keeps the phone app? Meta's "coexistence" onboarding is the thing to check: availability in the UK, what it syncs, and what the owner loses on the phone.
   - If not, the choice is a second number or moving the existing one. That is a business decision with a real cost to the owner's workflow.
2. **Meta requirements:** a Meta Business portfolio, business verification for Alma Consort Ltd (trading as London Choral Service), display name approval, and whether a payment method is needed.
3. **Cost:** Meta's current pricing for service (customer-initiated) messages, utility and marketing templates, and the 24-hour customer service window.
   - Replies the owner sends inside the window are the normal case.
   - Follow-ups after it would need approved templates.
4. **Hosting.**
   - The site is static GitHub Pages, so it can't receive webhooks.
   - Options: a small serverless function (Cloudflare Workers or similar) that verifies Meta's signature and passes only what is needed, or a local poller.
   - Whatever receives the messages must not keep message text beyond what the pipeline needs.
   - Secrets go in the macOS Keychain (as `lcs-starling-read` and `lcs-pagespeed` do) or the host's secret store. Never put them in the repo, which is public.
5. **The drafts-only rule.**
   - The owner sends every client message. A Cloud API integration can send messages, so the design must make sending impossible from Claude's side, the way `.claude/hooks/zoho_guard.py` does for Zoho: a guard hook, no send tool exposed, or a read-only token if Meta offers one.
   - Drafts would have to live somewhere the owner sends from. If WhatsApp has no draft concept through the API, the realistic design is **receive and log only**, with the owner replying from the phone app. Say so plainly.
   - An automatic acknowledgement ("Thanks, Luca will reply within one working day") is an owner decision, and it breaks the drafts-only rule unless the owner explicitly changes it.
6. **Privacy and law.**
   - Meta becomes a processor of enquiry data. The privacy notice (`privacy.html`) needs a WhatsApp section.
   - UK GDPR lawful basis: replying to an enquiry is pre-contractual.
   - Retention: keep no message text in the repo, and in `~/lcs-private/` only what the pipeline needs.
   - PECR for any template the business starts: no marketing templates without consent.
   - The owner's 23 Oct consent rulings still apply. A WhatsApp message carries a Ref only if the visitor accepted cookies.
7. **Click-to-WhatsApp ads** are a Meta (Facebook/Instagram) product, not Google Ads. Note them as out of scope for this account. Also check whether Google Ads offers message assets that open WhatsApp in the UK, and whether that would conflict with the targeting rules (choirs of four or more, no solo-singer searches).
8. **Recommendation:** build or don't build, with the cheapest design that meets 1–6. A fallback that needs no API is fine: the owner forwards WhatsApp enquiries to office@ by the share sheet, and the assistant handles them like email.

**Deliverable:** the spec, plus one batched question to the owner covering the number, the cost ceiling, auto-acknowledgement yes or no, and go or no go.

### WP4. Build the WhatsApp intake (only after the owner approves WP3)
- **Plan first:** `docs/superpowers/plans/2026-11-xx-whatsapp-intake.md`, in the house plan style.
- **Webhook receiver:** verifies the signature, then passes sender, timestamp and text to a private queue that only the owner's Mac reads. Prefer a pull model, so nothing private sits on a third-party host.
- **`assistant_io.py` / `pipeline.py`:** a `whatsapp` source keyed by the WhatsApp message or thread id, holding no names, with "Ref:" / "Ad visit:" parsed into the existing columns so `enquiry_sources.py` grades it with no special case.
- **A guard hook** that makes sending impossible, plus tests in the style of `tests/test_zoho_guard.py`.
- **The Monday report:** section 9c (the assistant's runs) and section 9b gain WhatsApp. Drop the WhatsApp question from the review prompt once counts are automatic.
- **Verify:** a test message through the sandbox number, its pipeline row, its grade and, with a test ref, the WP2 validate-only upload.

### WP5. Reporting check (once WP2 is live)
- Add a line to section 3 or 9b that sets Google Ads' "Enquiry received" count beside the pipeline's A-graded count for the same week. A gap points to a broken upload.
- Keep the spend guard on A/B grades, not Ads conversions (owner decision, 26 Oct 2026).

## 6. Owner decisions to batch (one question)
1. WP2: create "Enquiry received" as a secondary action now, and make it primary later once it has data?
2. WP3: the number (coexistence, a second number, or migration), a monthly cost ceiling for Meta, an automatic acknowledgement or none, go or no go.
3. Privacy notice wording for WhatsApp (draft it; the owner approves it).

## 7. Rules that bite
- **Google Ads:**
  - every change goes through a dated script in `scripts/ads/`;
  - run validate-only first, show current → new, apply after approval and log;
  - never delete; pause instead;
  - budgets are never a standing approval;
  - daily budget caps live in `budget_cap.py`.
- **GA4:** dry run, approval, apply, log in `logs/ga4-changes.md`. The Admin API has no validate-only mode.
- **Never `url_passthrough`, and never carry a click ID for a visitor who refused cookies** (ICO, owner decision 23 Oct 2026).
- **Never target solo-singer searches.** Keep the negatives singer, soloist, solo and vocalist on every campaign.
- **Forms:** keep the `h-captcha-response` check and the `botcheck` honeypot.
- **Before merging:** `.venv/bin/python tests/run_ci_tests.py` locally. Never merge while "Check and stage public files" is failing or running. Afterwards, check that main's deploy succeeded.
- **Keep `graphify-out/` out of these PRs.**
