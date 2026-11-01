# WhatsApp Business Platform: feasibility and decision

**Date:** 2026-11-01
**Status:** Decided 1 Nov 2026: no Cloud API; the forward-to-office@ route in section 9 is built. WP3 of `docs/superpowers/plans/2026-10-31-ad-tracking-and-whatsapp-handoff.md`.
**Decision (owner, 1 Nov 2026):** "i need linked devices". Coexistence unlinks them (section 2), and moving the number fully to the API ends the phone app, so the Cloud API is out while that holds. Everything else as recommended.

Facts were checked against Meta's and Google's documentation on 1 Nov 2026. Meta's developer docs moved to `developers.facebook.com/documentation/business-messaging/whatsapp/…`, and many older `/docs/whatsapp/…` links now fail. Anything marked **unconfirmed** came from a third party, or from no source at all.

## 1. What it would buy

- WhatsApp enquiries land in the pipeline on their own, with their "Ref:" or "Ad visit:" line parsed, so `enquiry_sources.py` grades them like email.
- A-graded ones feed the "Enquiry received" upload (spec 2026-11-01-enquiry-conversion-design).
- The Monday report counts WhatsApp without asking the owner.
- It would **not** give drafted replies. Section 5 explains why.

## 2. The number (07356 042468)

- **Coexistence exists.** A number on the WhatsApp Business app (version 2.24.17 or later) can be connected to the Cloud API through Embedded Signup while the owner keeps using the phone app. Sources: [onboarding Business app users](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users.md), updated Apr 2026.
  - **What syncs:** contacts, up to 180 days of one-to-one history (no groups), and the owner's own sent messages as `smb_message_echoes` webhooks.
  - **What the phone loses:**
    - disappearing messages, view-once and live location in one-to-one chats;
    - broadcast lists, which become read-only;
    - every linked device, which is unlinked (up to four can be relinked; not Windows).
  - **Inactivity:** if the phone app goes unused for about 14 days, Meta removes the link.
  - **Needs a partner.** Meta's page says the onboarding is run by a Solution Partner (a BSP) or a Tech Provider. A business that tried it on its own app was blocked ([forum thread](https://developers.facebook.com/community/threads/1866465831217430/), no answer from Meta). So this means paying a BSP; self-onboarding is **unconfirmed** and looks unsupported.
  - **UK numbers:** Meta's page has no country list. BSPs [360dialog](https://docs.360dialog.com/partner/waba-management/phone-number-and-hosting/using-whatsapp-app-and-cloud-api-simultaneously) and [Chakra](https://chakrahq.com/article/whatsapp-coexistence-live-eu-uk-europe-whatsapp-business-for-api-live/amp/) list the UK as supported, Chakra since Oct 2025. **Unconfirmed by Meta.**
- **Personal WhatsApp** isn't covered by coexistence. If the number is on personal WhatsApp, it would first have to move to the Business app (**unconfirmed** how that move treats history).
- **Moving the number fully to the Cloud API, without coexistence,** means deleting its WhatsApp account. After that the phone app no longer works on that number ([phone numbers](https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/phone-numbers.md)). That breaks the owner's way of working. Not recommended.
- **A second number** keeps the phone untouched. But the site, Google Business Profile and printed material all give 07356 042468, and clients would message the old one.

## 3. Meta requirements

- A Meta Business portfolio, a developer app with the WhatsApp use case, a WhatsApp Business Account and a system-user token ([get started](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started.md)).
- **Business verification** of Alma Consort Ltd is not needed to start. It lifts the limit on messages the business starts (250 people a day before verification) ([messaging limits](https://developers.facebook.com/documentation/business-messaging/whatsapp/messaging-limits.md)). A receive-only intake never meets that limit.
- **Display name:** approval governs whether the name shows, not whether messages flow ([display names](https://developers.facebook.com/documentation/business-messaging/whatsapp/display-names.md)).
- **Payment method:** receiving is free. From 1 Oct 2026, Meta stops delivering a business's service messages once its free tier is used up, if no payment method is on file ([pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing.md)). Messages the owner sends from the phone app under coexistence are free and don't count. A card would still be wise.

## 4. Cost

- **Meta** ([pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing.md)):
  - Meta charges per message sent by the business, since 1 July 2025; receiving is free.
  - Service replies inside the 24-hour window are free up to 1,000 a month per number from 1 Oct 2026, then charged.
  - Templates (utility, marketing) are charged. Only templates can be sent outside the window.
  - Meta's marketing page still says service messages are free ([platform pricing](https://whatsappbusiness.com/products/platform-pricing/)). The developer page is newer.
  - UK rates didn't render on Meta's page. Third-party figures (around 1.6p for utility, 4–5p for marketing) are **unconfirmed**.
- **For receive-and-log only, Meta's cost is £0.** The owner keeps replying from the phone app.
- **A BSP's monthly fee** is the real cost, and coexistence needs one. It is not quoted here; get a quote before deciding.
- **Hosting:** a Cloudflare Worker and queue on the free tier would carry this volume. **Unconfirmed** for this use; check the current free-tier limits when building.
- **Setup and upkeep:** a few days of build, plus a link that dies after 14 idle days, plus a third party (the BSP) holding enquiry data.

## 5. The drafts-only rule

- **No permission receives without sending.** `whatsapp_business_messaging` both receives the message webhooks and sends; `whatsapp_business_management` doesn't deliver messages ([permissions](https://developers.facebook.com/documentation/business-messaging/whatsapp/permissions.md)). So the receiver's token *could* send. The only control is ours:
  - the receiver holds no code that calls the send endpoint;
  - Claude is given no WhatsApp send tool;
  - a guard hook refuses any request to `graph.facebook.com/*/messages`, with tests in the style of `tests/test_zoho_guard.py`;
  - the token lives in the Worker's secret store, never on the Mac.

  A BSP dashboard can also send, but only the owner would hold that login.
- **No drafts.** The Cloud API has no draft concept (nothing in the docs). Under coexistence, a message sent through the API appears in the phone's chat as already sent. The realistic design is **receive and log only**, with the owner replying from the phone app.
- **An automatic acknowledgement** ("Thanks, Luca will reply within one working day") would be software sending to clients. It breaks the drafts-only rule unless the owner changes it. Not recommended.

## 6. Hosting design (if built)

- Webhooks need a public HTTPS endpoint with a valid certificate. Setup uses a GET handshake, and each POST is signed (`X-Hub-Signature-256`, HMAC of the body with the app secret) ([webhooks](https://developers.facebook.com/docs/graph-api/webhooks/getting-started)). GitHub Pages can't host one, and there is no API to pull past messages, so a small receiver is unavoidable.
- **The receiver**, a Cloudflare Worker:
  - verifies the signature and answers 200;
  - keeps only the message id (wamid), timestamp, a keyed hash of the sender's `wa_id`, and the parsed "Ref: XXXX" / "Ad visit: …" line;
  - keeps the text only while the Mac hasn't fetched it, so `lcs-reply-drafter` can set the occasion;
  - holds it all in a queue the Mac pulls (pull model) and deletes on fetch.
- **Retries:** Meta retries for up to 7 days ([webhooks overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview)), so the receiver dedupes on wamid.
- **On the Mac:** a `whatsapp` source in `pipeline.py`, keyed by the hashed sender plus the first wamid, holding no names. The Ref is resolved by `lookup_ref.py` as today.

## 7. Privacy and law

- **Meta** is a processor for Cloud API messages and keeps them up to 30 days ([data privacy](https://developers.facebook.com/documentation/business-messaging/whatsapp/data-privacy-and-security.md); [data processing terms](https://www.whatsapp.com/legal/business-data-processing-terms)). A BSP is a second processor.
- **`privacy.html`** would need a WhatsApp section: who processes the message (Meta, the BSP, Cloudflare), what we keep (no message text after intake), how long, and the lawful basis.
- **Lawful basis:** steps taken at the enquirer's request before a contract (UK GDPR Art. 6(1)(b)).
- **PECR:** no marketing templates without consent; the design sends nothing at all.
- **Consent for refs:** the 23 Oct rulings stand. A message carries a Ref only if the visitor allowed cookies, and never a click ID without consent.

## 8. Ads on WhatsApp: out of scope

- **Click-to-WhatsApp ads** are a Meta product, bought in Meta Ads Manager ([click-to-WhatsApp](https://whatsappbusiness.com/products/create-ads-that-click-to-whatsapp/)). The business runs Google Ads only.
- **Google Ads message assets** can open WhatsApp from a search ad ([message assets](https://support.google.com/google-ads/answer/14888522)). The feature is in beta, needs conversion-based bidding (the account bids manual CPC), and doesn't list the UK (**unconfirmed**).
  - It doesn't fit the targeting rules either: a one-tap "message us" invites solo-singer and quick-price chats that the negatives keep out.
  - Not recommended.

## 9. Recommendation

**Don't build the Cloud API intake now.**

- WhatsApp enquiries from ads are rare: the whole season since 1 Sep produced one A-graded enquiry.
- The build needs a paid BSP and a public receiver.
- It changes how the owner's phone works: disappearing messages, broadcast lists, linked devices, and the 14-day link.
- It can't draft replies.

**Cheapest route that meets most of the goals: forward to office@.**

1. When a WhatsApp enquiry arrives, the owner uses WhatsApp's own Export chat (chat → More → Export chat, without media → Mail; [WhatsApp help](https://faq.whatsapp.com/en/android/23756533), **partly unconfirmed**). Alternatively, they copy the first message into an email to office@londonchoralservice.com with the subject "WhatsApp enquiry".
2. The enquiry assistant then treats a message from the owner's own address with that subject as a WhatsApp enquiry. It adds a pipeline row with source `whatsapp`, takes the Ref or Ad visit from the text, and **drafts nothing** (the client is on WhatsApp, and the owner replies there).
3. The Monday question about WhatsApp bookings stays only as a fallback.

Built 1 Nov 2026:
- The dispatcher (Appendix E and the live task) sorts a message from office@ or luca@almaconsort.com to office@ with a subject starting "WhatsApp enquiry" as a WHATSAPP COPY, ahead of QUOTES.
- `lcs-reply-drafter` runs only steps 2 and 4 for it: a pipeline row with its own thread id, source `whatsapp`, the client's message date and notes starting "whatsapp copy". It never drafts.
- `pipeline.followups_due` never chases a row noted "whatsapp copy": its thread is Luca's own email.
- A copy that carries a Ref goes to Google as "Enquiry received" like any other enquiry.

**How Luca sends one (iPhone):** in the chat, press and hold the client's message, tap Forward, then the share button, then Mail. Choose office@ (or luca@almaconsort.com) as the sender, send it to office@londonchoralservice.com, and start the subject with "WhatsApp enquiry". Several messages can be ticked before tapping share. Keep the client's own text whole, Ref or Ad visit line included.

**Look again** if WhatsApp enquiries carrying a Ref become regular (say five a month), or if ad spend grows well beyond this season's.

## Owner decisions (answered 1 Nov 2026)

Answered: (1) moot, since linked devices rule out coexistence; (2) none; (3) no; (4) no go on the Cloud API, go on the forward route; (5) none needed.


1. **The number:** is 07356 042468 on the WhatsApp Business app or personal WhatsApp? Only matters if (4) is go.
2. **Monthly cost ceiling** for a BSP and Meta, if built. Recommended: none; don't build.
3. **Automatic acknowledgement:** recommended no; it breaks drafts-only.
4. **Go or no go:**
   - recommended: no go on the Cloud API;
   - go on the forward-to-office@ route instead.
5. **Privacy notice:** none needed for the forward route. The email the owner forwards is our own record of the enquiry, already covered by "If you write, ring or message us on WhatsApp instead, we keep what you tell us there". Cloud API wording would be drafted only on a go.
