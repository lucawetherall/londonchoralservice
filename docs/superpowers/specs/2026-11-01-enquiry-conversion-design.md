# "Enquiry received": an offline conversion for every channel

**Date:** 2026-11-01
**Status:** Approved 1 Nov 2026 (decisions 1, 3 and 4 as recommended). "Enquiry received" was created that day as a secondary action (`conversionActions/7885302154`, logged in `logs/ads-changes.md`). The privacy sentence in 3b went live with the same PR. The first upload (one enquiry) was applied on 1 Nov after the deploy, and Google accepted it. WP2 of `docs/superpowers/plans/2026-10-31-ad-tracking-and-whatsapp-handoff.md`.

## Problem

Since 31 Oct, "Submit lead form" is the only primary conversion, and it fires only for a web form sent with cookie consent. A WhatsApp message or an email from an ad visitor is counted in the private pipeline (grade A or B in `enquiry_sources.py`), never in Google Ads. The Ads interface therefore under-reports enquiries, and nothing checks the pipeline's A-graded count against what Google sees.

## Design

### 1. The conversion action (`scripts/ads/create_enquiry_received_action_2026_11.py`)

- Name "Enquiry received", type offline upload (`UPLOAD_CLICKS`), category Submit lead form, one per click, 90-day click-through window.
- No value (default £0, always used). "Booked job" carries the money; this one counts enquiries.
- **Secondary.** It sits in the same goal category as the site's "Submit lead form" tag, so a consented form enquiry is counted by both. While the action is secondary that only matters in reporting. Making it primary is a later owner decision, and "Submit lead form" goes secondary at the same time. Otherwise one enquiry counts twice and bidding would see double.
- Validate-only on 1 Nov 2026: Google accepted the operation; nothing was changed.

### 2. The upload (`scripts/ads/upload_enquiries.py`)

Modelled on `upload_bookings.py`: Data Manager API (`events:ingest`), validate-only by default, `--apply` after approval, a count only in `logs/ads-changes.md`.

- **What goes up:** a pipeline row (`~/lcs-private/enquiries.csv`) with a click reference in its `gclid` column (a gclid, `gbraid:` or `wbraid:`, or the gclid `lookup_ref.py` resolved from a "Ref: XXXX" line), first seen on or after 27 Sep 2026. Every channel counts: web form, email, WhatsApp and phone. The site keeps a click ID only for a visitor who allowed cookies, and has done so since 27 Sep, so the reference is the consent: `adUserData` granted, `adPersonalization` denied.
- **Order ID:** the `enquiry_id` (the Zoho thread id, or the id a WhatsApp enquiry was entered under), so a row can never count twice. The new pipeline column `ads_uploaded_at` is stamped after an accepted `--apply`. `pipeline.py add` refuses it as input.
- **Conversion time:** 23:59 London time on `first_seen`, which falls after any click that day, or a minute ago for an enquiry first seen today. The pipeline keeps dates, not times.
- **Never:**
  - a B-graded enquiry ("Ad visit": no click ID; the owner rejected `url_passthrough` on 23 Oct 2026 on ICO consent grounds);
  - an unresolved "Ref:" note (listed with that reason);
  - an enquiry first seen more than 90 days ago;
  - any email address, hashed or not.

### 3. Why no hashed email

The handoff plan suggested sending a form sender who ticked the ad-measurement box with their hashed email, as `upload_bookings.py` does. The box and `privacy.html` promise otherwise: "We send nothing for an enquiry that doesn't become a booking." Sending an enquiry would break that promise, so the email-only path is left out. A ticked-box enquiry that also carries a click reference still goes up, on the cookie consent behind that reference.

The path can be added later if the owner approves new wording for the box and the notice. That is a privacy policy call (owner decision 4 below). In practice it adds little: a booking from that enquiry already goes up as "Booked job" by hashed email.

### 3b. The privacy notice must say it first

`privacy.html` covers the click reference in a WhatsApp message or email (the four-character code) only for bookings: "When an enquiry becomes a booking, we match that code to the click … and may report the booking to Google Ads". Before the first `--apply`, that sentence changes (owner decision 3), the build runs and the change is live:

> When you send an enquiry, we match that code to the click in our Google Ads account and may tell Google Ads, with its click reference, that the click led to an enquiry and, later, to a booking. That lets us spend our advertising budget on the searches that bring enquiries and bookings.

The web form's click reference is already covered: with cookies allowed, the Google Ads tag reports that enquiry itself, as the notice says.

### 4. The Monday review

- Section 9b of `weekly_review.py` ends with `"Enquiry received" upload: UPLOAD would send <n> · sent so far <m>`, plus skip reasons as counts. It shows no ids.
- `lcs-review-bookings` copies that line under UPLOAD. It reads the report rather than running the script, so the scheduled run needs no new allowed command. The line counts rows, so it shows a number before the action exists; the script itself refuses to run until the action is created.
- The dispatcher lists "[upload] Enquiry received" among the week's decisions (handover Appendix A). Once approved, `upload_enquiries.py --apply` runs once and commits only its log line, through a PR.

### 5. Later: the reporting check (WP5)

Once uploads have run for a few weeks, section 3 or 9b sets Google Ads' "Enquiry received" count for the week beside the pipeline's A-graded count. A gap points to a broken upload. The spend guard stays on A/B grades (owner decision, 26 Oct 2026).

## Testing

- `tests/test_upload_enquiries.py`:
  - every channel is ready;
  - gbraid and wbraid keep their kind;
  - the end-of-day and same-day timestamps;
  - ad visits and non-ad rows are left out silently;
  - an unresolved Ref is listed;
  - the 90-day and 27 Sep cut-offs;
  - no email ever goes, even with the box ticked;
  - stamping touches only the uploaded rows.
- `tests/test_pipeline.py`: `add` refuses `ads_uploaded_at`.
- `tests/test_weekly_proposals.py`: section 9b's upload line counts only the A-graded row.
- Live: the action's validate-only create (1 Nov 2026, accepted). After approval, create the action, run `upload_enquiries.py` validate-only, then `--apply` for the one A-graded enquiry the pipeline holds.

## Owner decisions

Answered 1 Nov 2026: 1 yes, 3 yes (with one more wording fix: the ad-measurement paragraph now says "We send no copy of your email for an enquiry that doesn't become a booking", since a ticked-box enquiry with a click reference now goes up on its cookie consent), 4 no. Decision 2 stays for later.


1. Create "Enquiry received" as a secondary action now (Google Ads: does not exist → created, secondary).
2. Later: make it primary, with "Submit lead form" going secondary at the same time.
3. The `privacy.html` sentence in 3b, live before the first upload.
4. Optional: new wording for the ad-measurement box and `privacy.html` that lets a ticked-box enquiry go up by hashed email. Recommended: no, because the gain is small.
