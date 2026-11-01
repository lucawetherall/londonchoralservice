# Handoff: ad tracking improvements and the WhatsApp Business Platform

Written 31 October 2026 for an agent starting fresh; revised 1 November 2026 after every claim in it was checked against the repo, the logs and the public documentation. It holds what that agent needs and `CLAUDE.md` doesn't: what was found and verified on 31 October, what has already changed, the gaps that remain, what was looked at and set aside, and the work in order, with the points where the owner decides. Read it once from top to bottom, then work one package at a time.

## 1. How to use this document

- It records the state on 31 October 2026 (section 3) and what the public documentation said on 1 November (section 5, WP3). Numbers move, so pull them again before you act on any of them.
- The owner, Luca Wetherall (they/them in anything you write about them, as the earlier handoff documents do), has given a full mandate for London Choral Service work: decide, build, open and merge reviewed PRs, and verify live. Three things always need their explicit approval:
  - any change to the Google Ads account: one approval per change set, shown as current value → new value with a reason;
  - any GA4 or Search Console configuration change: shown the same way, after a dry run;
  - any business or privacy policy call, which covers everything in section 7.

  Batch these into one question.
- Nothing is ever sent by you. Client messages are drafts the owner sends. That rule covers WhatsApp too (WP3 and WP4).
- No client names, phone numbers, emails, message text or ledger money figures go into the repo, a PR, a commit message or `logs/`. The repo is public. Private data stays in `~/lcs-private/`.
- Each work package ends with the commands that prove it. Run them before you say it is done.

## 2. Read first, in this order

1. `CLAUDE.md`, all of it. The rules you will use most are in "Google Ads & GA4", the bookings ledger paragraph, "Email and invoices", and the enquiry assistant and pipeline paragraphs.
2. `docs/superpowers/specs/2026-10-14-cookieless-ad-attribution.md` and `docs/superpowers/specs/2026-10-23-cookieless-ad-source-design.md`: how an ad click is carried into an enquiry with consent and without it. The first spec also records the Data Manager rule WP2 rests on: an event may carry `userData` (a hashed email) as its only identifier.
3. `partials/analytics.html`: Consent Mode v2, with every consent default set to denied. It also holds `lcsLead()`, `lcsAttribution()`, `lcsAdVisit()`, `lcsClickIds()`, `lcsShortRef()` and `lcsLabelMessage()`, which adds "Sent from …" and "Ref: XXXX" / "Ad visit: …" to WhatsApp and email links when they are clicked. Edit the partial and run `./build.sh`; never edit the expanded copy in a page. `tests/test_lead_tracking.mjs` drives the partial in a headless browser; `tests/test_ad_attribution.py` checks the Ref and ad-visit flows.
4. `js/form.js`: the web form. It sends to Web3Forms with an hCaptcha guard and the `botcheck` honeypot, and adds the attribution fields (`gclid`/`gbraid`/`wbraid` with consent, `ad_visit` without, `ad_measurement` when the box is ticked). Since 31 Oct it also waits for the captcha, retries once and offers fallbacks (section 3).
5. `scripts/reports/enquiry_sources.py`: how every enquiry is graded A, B or C by ad source. Its docstring is the definition. This grading is the business's real measure of the ads, because Google's own conversion figures can't measure this volume. Tests: `tests/test_enquiry_sources.py`.
6. `scripts/bookings/pipeline.py` (`~/lcs-private/enquiries.csv`: columns `enquiry_id, first_seen, source, occasion, event_date, package, quoted_gbp, status, last_contact, booking_ref, gclid, followups, notes`; no name, email or phone; `source` is already one of `web form, email, whatsapp, phone, referral`, and `summary` prints `open_whatsapp`), `scripts/bookings/assistant_io.py`, `scripts/ads/lookup_ref.py` (four-character ref → gclid, from `click_view`, 90 days, gclids only) and `scripts/ads/upload_bookings.py` (the "Booked job" upload through the Data Manager API: the model for WP2). Tests: `tests/test_pipeline.py`, `tests/test_lookup_ref.py`, `tests/test_upload_bookings.py`.
7. `scripts/reports/weekly_review.py`, sections 3 (`conversions_section`, with `PRIMARY_ACTIONS`), 5 (GA4), 5c (GoatCounter: `scripts/reports/goatcounter.py` counts `enquiry-sent-whatsapp`, `-email`, `-call` and `-form` events from every visitor, cookies or not), 8 (wiring), 9b (`enquiries_section`) and 9c (the assistant's runs), and `.claude/agents/lcs-review-ads.md` and `lcs-review-bookings.md`, which read them.
8. `docs/utm-conventions.md`, `logs/ads-changes.md` and `logs/ga4-changes.md`, newest first. Check the logs before proposing anything, so you don't undo a recent change. `MANUAL-ACTIONS-REQUIRED.md` §12 holds the owner-only Ads screen notes that matter here (gap 5).

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
| Funeral campaign 23735776277 paused (spend guard: £125.64 in 28 days, no A or B enquiry) | `logs/ads-changes.md`, 2026-10-31 23:17 |
| "WhatsApp or email click" (7796284061) primary → secondary. A tap is not a sent message: funeral showed 2 conversions with no enquiry behind them. "Submit lead form" (7603963809) is now the only primary action, and `weekly_review.py`'s `PRIMARY_ACTIONS` says so | #437, `logs/ads-changes.md`, 2026-10-31 23:49 |
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
   - WhatsApp messages live only on the owner's phone. A WhatsApp enquiry reaches the pipeline only when the owner mentions it (the reply drafter and `/lcs-book` already take `source` "whatsapp"), and its "Ref:" line only when they paste it (the Monday question asks for it while `open_whatsapp` is above 0).
   - The Google Business Profile's Chat button already opens WhatsApp on the same number (`wa.me/447356042468`; MANUAL-ACTIONS §4 notes, on 29 Oct, that Google switched it on by itself), so Maps enquiries arrive on the phone too, with no "Sent from" label at all.
3. **The "Booked job" loop has never run with real data.** It works only for consented A-graded bookings, or form senders who ticked the ad-measurement box.
4. **Stale wording in three places** (the plan's first version named the wrong line):
   - `partials/analytics.html` lines 70–72 (the comment above `LCS_ADS`) still say "WhatsApp or email click" is a primary goal (owner decision, 26 Sep 2026). In every built page that comment sits near line 83, which is where the old note pointed; edit only the partial.
   - `docs/HANDOVER-2026-09-27-ads-analytics.md` line 23 (the goals table: "Primary: Submit lead form, WhatsApp or email click") and line 348 (the taps bullet) describe the pre-31 Oct state.
   - `logs/ga4-changes.md` records the `contact_message` key event and its two event-create rules (27 Sep) with the reason "primary in Google Ads". The key event itself is fine to keep: it is GA4-only, costs nothing, and section 5 reads key events by channel. Don't change it; just know the reason is historical.
5. **Legacy conversion actions and an alert nobody has looked at.** "Contact" (7566855536, codeless, fires on the thank-you page) and "Contact (1)" (7566867509, GA4 import) are secondary and enabled, kept for history. MANUAL-ACTIONS §12 adds two things the first version of this plan missed: on 29 Oct "Contact" showed a conversion on 26 Oct 2026, so it may be counting real form enquiries alongside "Submit lead form" (harmless while secondary, but it muddies section 3), and the same screen showed an **"Enhanced conversions not recording"** alert that was never investigated. Hiding the two actions is the owner's screen task. The alert is yours to read (WP1). Never delete either action.
6. **Calls from ad viewers are invisible.** That is the owner's choice; record it rather than "fix" it.
7. **`enquiries.csv` has no email column.** This is by design (no personal data in the sheet), and it decides WP2's shape: an enquiry can go to Google by its click ID, but not by hashed email unless a script fetches the address from the Zoho thread at upload time. See WP2.

## 5. Work packages, in order

### WP1. Small fixes and one read-only check (no approval needed beyond the PR)
- Reword the comment in `partials/analytics.html` lines 70–72 to: "WhatsApp or email click" is a secondary action since 31 Oct 2026 (a tap is not a sent message; sent messages are counted by their Ref / Ad visit lines in the pipeline) and "Call click" a secondary one. Run `./build.sh` (expect the ~165-file partial diff) and `node tests/test_lead_tracking.mjs` if Playwright is installed.
- Update the two stale lines in `docs/HANDOVER-2026-09-27-ads-analytics.md` (gap 4) to the 31 Oct state, dated.
- **Read the "Enhanced conversions not recording" alert** through the Google Ads MCP (read-only): `conversion_action` rows for "Submit lead form" with `conversion_action.status`, `type`, and the enhanced-conversions fields the API exposes, plus `conversion_tracking_setting` on the customer. If the alert means the form's user-data hashes never arrive (the lead is sent from thank-you.html after a redirect: `lcsLead()`), reproduce with a consented test enquiry marked "TEST – please ignore" only with the owner's OK, retract it afterwards the way `scripts/ads/retract_test_lead_2026_10_23.py` did, and fix the partial. If it means Google wants the "customer data terms" or a different tag setting, that is a screen task: add it to MANUAL-ACTIONS §12 with what to click. Either way, write what you found under §12.
- After 9 November, read `form_error` × `error_type` × `error_detail` in GA4 (run_report on event `form_error` with those dimensions). If one cause dominates (for example Web3Forms rejecting iOS requests), fix it in `js/form.js`, or propose a second submission route as an owner decision. Never remove the hCaptcha check or the honeypot.

**Proof:** `.venv/bin/python tests/run_ci_tests.py` passes; `git diff --stat` shows only the partial, the built pages, the handover doc and MANUAL-ACTIONS; the merged PR's deploy succeeds (`scripts/reports/routine_health.py`).

### WP2. An "Enquiry received" offline conversion, for every channel (spec first)
**Goal:** Google Ads counts real enquiries, not taps, from every channel the consent rules allow.

**Design to spec in `docs/superpowers/specs/2026-11-xx-enquiry-conversion-design.md`.** Decisions already settled by what exists:

- **A new conversion action,** "Enquiry received", category Submit lead form (so it sits beside the web-form action in the Ads screens), counting one per click, no value (count-only: `value_settings.default_value` 0 and `always_use_default_value` true), secondary first, primary only once the owner agrees and it has four weeks of data. Create it with a dated script cloned from `scripts/ads/create_booked_job_action_2026_09.py` (validate, approve, apply, log). Check first that the Data Manager accepts an event with no `conversionValue` for a count-only action; if it insists on one, send `0` with currency `GBP` and say so in the spec.
- **Source of truth:** `~/lcs-private/enquiries.csv`, read with `enquiry_sources.grade_rows()` so the upload and the Monday report agree on what A means. Upload only grade A: a `gclid`/`gbraid:`/`wbraid:` in the `gclid` column (the site adds it only with cookie consent, which is the `adUserData` consent the upload asserts), or a "ref: XXXX" note already resolved by `lookup_ref.py` into the `gclid` column. A ref note with no resolved gclid is not uploadable; print it as a skip with the `lookup_ref.py` command to run.
- **Email-only uploads: not in version 1.** `enquiries.csv` holds no email (gap 7), and the form's `ad_measurement: yes` reaches the sheet only as a note. Fetching the address from the Zoho thread at upload time is possible (`scripts/bookings/lcs_mcp.py` is a read-only MCP client the bookings scripts already use) but adds a Mail read to an Ads script, so leave it out until the click-ID path has run for real. Note it under "later" in the spec, with the `lcs_mcp.py` route.
- **Dedup and timing:** `transactionId` = the enquiry's `enquiry_id` (the Zoho thread id), so a row can never count twice, and a later "Booked job" upload for the same client is a different action and does not collide. `eventTimestamp`: `first_seen` is a date, not a time; use 23:59:59 Europe/London on that day, as late as the day allows, so it falls after the click (`upload_bookings.py`'s `to_datetime` is the pattern). Skip a row whose `first_seen` is more than 90 days after the click (`lookup_ref.py` cannot find older clicks anyway).
- **Script:** `scripts/ads/upload_enquiries.py`, modelled line for line on `upload_bookings.py`: Data Manager `events:ingest`, `validateOnly` unless `--apply`, the same `consent` block, a new `uploaded_at`-style marker. `enquiries.csv` has no spare column, so record uploads in a private sidecar `~/lcs-private/enquiry-uploads.json` (`{enquiry_id: timestamp}`, mode 600), never in the sheet, and never in the repo. Log a count only in `logs/ads-changes.md`.
- **Tests:** `tests/test_upload_enquiries.py` in the style of `tests/test_upload_bookings.py`: grade A with a gclid uploads; a gbraid row carries `adIdentifiers.gbraid`; grade B never uploads; an already-uploaded id is skipped; a ref note with no gclid is skipped with the lookup command; a `first_seen` more than 90 days after the click is skipped; validate-only writes nothing. Add it to `tests/run_ci_tests.py`.
- **Never upload B-graded enquiries.** "Ad visit" carries no click ID, and the owner rejected `url_passthrough` on 23 Oct 2026 on ICO consent grounds: don't reopen that without legal advice.
- **Schedule:** the Monday review proposes the upload ("UPLOAD would send n", from a validate-only run inside `lcs-review-bookings`), and the owner approves it with the rest of that week's decisions. Add the line to `.claude/agents/lcs-review-bookings.md` and the dispatcher prompt (Appendix A of the handover), dated.
- **Verify** with a validate-only run against the one real A-graded enquiry of the season, then `--apply` after approval, then check section 3 the following Monday shows "Enquiry received" with 1.

**Proof:** `tests/run_ci_tests.py` passes; `logs/ads-changes.md` has the creation row and the first upload row; Monday section 3 lists the action as secondary ENABLED.

### WP3. WhatsApp Business Platform: a feasibility and decision document (spec, no build)

**Owner decision, 1 November 2026: not if it costs money.** The owner will not change their WhatsApp set-up if it means paying Meta. The Cloud API needs a payment method on file and bills per message (question 3 below), so WP3 and WP4 are closed unless Meta offers a route with no payment method and no charge; check that one point first, and if it does not exist write nothing more. The free fallback is the way forward: the owner forwards a WhatsApp enquiry to office@ from the share sheet, or tells Claude in a live chat (the reply drafter and `/lcs-book` already take "whatsapp" as a source). The rest of this package is kept for the record and for that one check.
**Goal:** decide whether the Cloud API should feed WhatsApp enquiries into the pipeline automatically. Write `docs/superpowers/specs/2026-11-xx-whatsapp-business-platform.md` for the owner. Check every fact below against Meta's current documentation on the day you write it, and cite it. What follows is what was found on 1 November 2026, mostly from Meta's developer pages and vendor write-ups: leads, not settled facts.

**What it would buy:**
- WhatsApp enquiries land in the pipeline automatically, with their "Ref:" or "Ad visit:" line parsed, so they are graded A/B like email.
- A-graded WhatsApp enquiries feed WP2's upload.
- The assistant drafts replies (only if a draft route exists; see question 5).
- The Monday report counts WhatsApp properly. It no longer needs the "did any WhatsApp enquiry turn into a booking?" question.
- With coexistence, the owner's own replies from the phone arrive as echo webhooks, so the pipeline could move an enquiry to "quoted" without anyone typing it.

**Questions the spec must answer:**
1. **The number.**
   - Is 07356 042468 on the WhatsApp Business app or personal WhatsApp? (Google Business Profile already offers it as the Chat button, so it is a public business channel either way.)
   - **Coexistence** (found 1 Nov): Meta's Embedded Signup documentation says the coexistence flow starts by itself when the number entered is already on the WhatsApp Business app, and the business keeps using the phone app while Cloud API is enabled on the same number; onboarding sends a QR code to the number and asks the business to accept terms. Vendor write-ups date the launch to May 2025 and name a minimum app version (2.24.17) and supported country codes; none confirmed UK availability outright, so check Meta's eligibility page. Two risks to record: Meta's "reconnect offboarded coexistence clients" page says changing phone or re-registering the app offboards the API side until the owner opts in again, and messages fail meanwhile; and onboarding offers to sync chat history from the app to the API, which the design must decline.
   - If coexistence is not available for the UK or the number, the choice is a second number or moving the existing one. That is a business decision with a real cost to the owner's workflow.
2. **Meta requirements:** a Meta Business portfolio, business verification for Alma Consort Ltd (trading as London Choral Service), display name approval, and a payment method.
3. **Cost** (found 1 Nov; verify on Meta's pricing page): billing has been per delivered message, by category and recipient country, since 1 July 2025. From 1 October 2026 service messages (replies in the 24-hour customer-service window) are charged too, after a free allowance that most sources put at 1,000 a month per business number; utility templates in the window lost their free tier the same day. UK rates quoted by vendors: marketing about $0.0635, utility and authentication about $0.0220, or in GBP about £0.0458 and £0.0159. At this business's volume (a few dozen WhatsApp messages a month) the cost is pence; the ceiling question in section 7 is about the Meta payment method, not the amount.
   - Replies the owner sends inside the window are the normal case; under coexistence they are sent from the phone app and may not be billed as API messages at all. Check.
   - Follow-ups after the window would need approved utility templates, and a quote follow-up is arguably marketing: PECR applies (question 6).
4. **Hosting.**
   - The site is static GitHub Pages, so it can't receive webhooks.
   - Options: a small serverless function (Cloudflare Workers or similar) that verifies Meta's `X-Hub-Signature-256`, answers the verification challenge, and queues only sender, timestamp, message id and text for the owner's Mac to pull; or a local poller if Meta offers one (it does not for inbound messages; webhooks are the only push).
   - Whatever receives the messages must not keep message text beyond what the pipeline needs, and must drop the queue once pulled.
   - Secrets go in the macOS Keychain (as `lcs-starling-read` and `lcs-pagespeed` do) or the host's secret store. Never in the repo, which is public.
5. **The drafts-only rule.**
   - The owner sends every client message. A Cloud API token can send messages, so the design must make sending impossible from Claude's side, the way `.claude/hooks/zoho_guard.py` does for Zoho: a guard hook, no send tool exposed, and a system-user token scoped to read webhooks only if Meta's permission model allows it (check `whatsapp_business_messaging` versus `whatsapp_business_management`).
   - WhatsApp has no draft concept through the API. The realistic design is **receive and log only**, with the owner replying from the phone app. Say so plainly. A drafted reply could still be written to a private file the owner copies from, as the assistant does for emails without IMAP.
   - An automatic acknowledgement ("Thanks, Luca will reply within one working day") is an owner decision, and it breaks the drafts-only rule unless the owner explicitly changes it.
6. **Privacy and law.**
   - Meta becomes a processor of enquiry data. `privacy.html` already lists "WhatsApp (Meta), if you message us there" among recipients (line 631) and says we keep what people tell us there (line 604); it needs a sentence that messages are also received through Meta's business platform and stored in our enquiry records, and the retention period.
   - UK GDPR lawful basis: replying to an enquiry is pre-contractual.
   - Retention: keep no message text in the repo, and in `~/lcs-private/` only what the pipeline needs (the enquiry row, no text).
   - PECR for any template the business starts: no marketing templates without consent. Quote follow-ups by WhatsApp are not in scope for the first version.
   - The owner's 23 Oct consent rulings still apply. A WhatsApp message carries a Ref only if the visitor accepted cookies.
7. **Ads products that open WhatsApp** (found 1 Nov). Click-to-WhatsApp ads are a Meta (Facebook/Instagram) product: out of scope for this account. Google Ads has **business message assets** (Click-to-Message to WhatsApp on search results), described on support.google.com (answer 14888522) and in the Ads API docs; the API side is allowlisted, and the feature has been called beta. A third-party list names the UK among iOS-available countries, unverified. If the feature appears under Assets in the account, note it for the owner, with the point that it would send clicks to the phone without any "Sent from … Ref:" label unless Google passes one, so attribution would need the WP4 intake first. Never add one without approval; the targeting rules (choirs of four or more, no solo-singer searches) are unaffected by the asset type.
8. **Recommendation:** build or don't build, with the cheapest design that meets 1–6. Two fallbacks that need no API are fine and should be costed against it: the owner forwards WhatsApp enquiries to office@ by the share sheet, and the assistant handles them like email (the drafter already accepts "whatsapp" as a source); or the owner tells Claude in a live chat, as `/lcs-book` already does for agreed bookings.

**Deliverable:** the spec, plus one batched question to the owner covering the number, the Meta payment method, auto-acknowledgement yes or no, and go or no go.

### WP4. Build the WhatsApp intake (closed by the 1 November decision above unless WP3's no-cost check passes and the owner approves)
- **Plan first:** `docs/superpowers/plans/2026-11-xx-whatsapp-intake.md`, in the house plan style, tasks with tests.
- **Webhook receiver:** verifies the signature, answers Meta's GET verification, then appends sender, timestamp, message id and text to a private queue that only the owner's Mac reads. Prefer a pull model, so nothing private sits on a third-party host longer than the pull interval.
- **`assistant_io.py` `whatsapp-inbox`:** pulls the queue, hands each message to the enquiry assistant's run as a new message with `source` "whatsapp" (already a valid `pipeline.py` source) and `enquiry_id` the WhatsApp conversation id (the sender's number must never be the id: `pipeline.py` output prints ids). "Ref:" / "Ad visit:" are parsed into the existing `gclid` column and `ad visit:` note by the same code the drafter uses for email, so `enquiry_sources.py` grades it with no special case.
- **A guard hook** that makes sending impossible (`.claude/hooks/whatsapp_guard.py`), plus tests in the style of `tests/test_zoho_guard.py`, and a line in `.claude/hooks/mcp_bypass_guard.py`'s tests that the Meta endpoints cannot be called from Bash either.
- **The Monday report:** section 9c (the assistant's runs) and section 9b gain WhatsApp counts; `lcs-review-bookings.md` drops the "open WhatsApp enquiries" question once counts are automatic (the dispatcher prompt in Appendix A too, dated).
- **Verify:** a test message through Meta's test number, its pipeline row (id, no number), its grade and, with a test ref, the WP2 validate-only upload. Then the owner's own phone, once.

**Proof:** `tests/run_ci_tests.py` passes with the new guard tests; `pipeline.py summary` shows the test row under `whatsapp`; no file in the repo or `logs/` holds a phone number or message text (`git grep -n "447\|+44"` over the PR's files).

### WP5. Reporting check (once WP2 is live)
- Add a line to section 3 or 9b that sets Google Ads' "Enquiry received" count beside the pipeline's A-graded count for the same week. A gap points to a broken upload.
- Add a second line to section 5c: GoatCounter's WhatsApp and email taps beside the pipeline's WhatsApp and email enquiries for the week, so the owner sees the tap-to-message ratio from every visitor, not only the consented ones.
- Keep the spend guard on A/B grades, not Ads conversions (owner decision, 26 Oct 2026).

**Proof:** `tests/test_weekly_review_snapshot.py` updated and passing; one saved Monday report shows both lines.

## 6. Looked at and set aside

So the next agent doesn't re-open them:

- **`url_passthrough` and carrying a click ID without consent:** rejected by the owner on 23 Oct 2026 (ICO guidance). Not without legal advice.
- **Google lead form assets:** dismissed on 26 Oct (standing approval b): a Google-hosted form skips the site's hCaptcha and consent check.
- **Smart bidding (Maximize conversions):** dismissed; owner rule is manual CPC, and the volume is far too low.
- **Call tracking or call buttons:** owner decision, 24 Oct: WhatsApp and email first, no Call buttons. The number is text.
- **Click-to-WhatsApp ads:** a Meta product; this account advertises on Google only.
- **Hiding "Contact" and "Contact (1)":** the API refused on 26 Oct; it is a screen task in MANUAL-ACTIONS §12, and §12's 29 Oct note says to check first whether "Contact" is still counting real enquiries.
- **Making "Booked job" or "Enquiry received" primary now:** no data yet. Secondary first, by the same rule `create_booked_job_action_2026_09.py` states.
- **Paying Meta for the WhatsApp Business Platform:** owner decision, 1 Nov 2026: WhatsApp stays as it is if connecting it means paying. Enquiries from WhatsApp reach the pipeline through the share-sheet forward or a live chat.
- **A watchdog or extra routine for any of this:** owner decision, 31 Oct: fold checks into the Monday review and the assistant's existing runs.

## 7. Owner decisions to batch (one question)
1. WP2: create "Enquiry received" as a count-only secondary action now, and make it primary later once it has data?
2. WP3: decided 1 November 2026 (no change to WhatsApp if it costs money). Ask only if Meta turns out to offer a no-payment-method route, and then: the number, an automatic acknowledgement or none, go or no go.
3. Privacy notice wording for WhatsApp (draft it; the owner approves it).
4. WP1, only if the enhanced-conversions alert needs a screen change: what to click, as a MANUAL-ACTIONS item.

## 8. Rules that bite
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
- **Private data:** `enquiries.csv` has no names, emails or numbers, and stays that way; any new private file goes in `~/lcs-private/` with mode 600 and never in the repo.
- **Before merging:** `.venv/bin/python tests/run_ci_tests.py` locally. Never merge while "Check and stage public files" is failing or running. Afterwards, check that main's deploy succeeded (`scripts/reports/routine_health.py`).
- **Keep `graphify-out/` out of these PRs.**
