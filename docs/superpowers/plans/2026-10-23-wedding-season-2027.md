# Wedding Season 2027 Plan (wedding-leads)

> **For agentic workers:** Google Ads rules are in CLAUDE.md ("Google Ads & GA4"): reads through the MCP tools, changes only through `scripts/ads/` (validate-only, current → new with a reason, Luca's approval per change set, a row in `logs/ads-changes.md`), pause and never delete, £5/day cap in `scripts/ads/budget_cap.py`, choir searches only. Load `writing-site-copy` and `stop-slop` before any ad or page copy. Booking values and margins are private (`~/lcs-private/`); this file carries none of them.

**Goal:** Have the wedding-leads campaign (23739971001) ready before January 2027, when couples engaged over Christmas start booking ceremony music: better expected CTR on "wedding choir", a bid check on 5 January, a budget rule that only moves when the data says so, and a landing page that matches the ads.

**Planned with:** `claude-ads:ads-plan`, `claude-ads:ads-math`, `claude-ads:ads-creative`, `ad-creative`. Data read 23 Oct 2026: Google Ads (MCP and Keyword Planner historical metrics, read-only), Search Console, the private ledger (aggregates only, not repeated here).

## Where the campaign stands (23 Oct 2026)

- **Since the 28 Sep reset** (manual CPC, choir keywords only, presence targeting, 07:00–20:00): 142 impressions, 14 clicks, £44.17 over 24 days. Average CPC £3.16, about £1.84 a day against a £4 budget. Search impression share 63%; 32% lost to ad rank, 5% to budget; 48% top-of-page.
- **April to September** ran on the old set-up (broad match, singer keywords, Maximise clicks) and is not a baseline for choir searches.
- **Quality Score.** The two "wedding choir" keywords (phrase £4.00, exact £4.50) carry most impressions and score 5: ad relevance above average, landing page average, expected CTR **below average**. "wedding choir hire", "choir for wedding ceremony", "choir for wedding" and the London exacts score 7. Google's first-page estimate for "wedding choir" is £3.28 (exact) and £3.72 (phrase); top of page £4.45 and £5.12.
- **Search terms since 28 Sep** are all choir searches ("wedding choir", "hire a choir for wedding", "wedding choirs", "choir for wedding ceremony"); nothing new to exclude. The four house negatives (singer, soloist, solo, vocalist) and the rest of the negative list stay.
- **Assets.** Six enabled sitelinks (prices, quote, repertoire, music guide, listen, about), the price list, the "Types" snippet, the call asset, the logo, and the six account-level callouts. Ad 826000407486 was refreshed today and rates Average.

## Seasonality

Keyword Planner, UK, Oct 2025 to Sep 2026, for wedding-choir searches combined (it rounds small volumes, so read the shape, not the units):

| Oct | Nov | Dec | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 170 | 140 | 100 | 140 | 110 | 180 | 130 | 160 | 130 | 110 | 140 | 130 |

"wedding choir" alone sits at 50 a month in ten months of twelve, 30 in December and February. Choir searches do not surge in January the way venue and dress searches do; the low point is December and the high is March. Search Console shows the same flat line for "wedding choir" (40–42 impressions a month since August). The site's own organic weddings.html sits at an average position of 34, so the ads carry the commercial searches.

**Reading:** the January opportunity is to be in the auction at a good position when the 2027 couples search, not to spend more. With spend at half the budget, the limit is ad rank on a small pool of searches.

## Break-even (ads-math)

`maximum cost per booking = booking value × contribution margin`

The plan uses the published Small Choir price (£1,150, `pricing.html`) as a floor for booking value; the ledger's wedding average is in the private dashboard. Margin after singers is private, so three cases:

| Margin | Break-even cost per booking at £1,150 |
|---|---|
| 30% | £345 |
| 40% | £460 |
| 50% | £575 |

At today's pace (about 18 clicks and £55 a month) the campaign spends £330 to £660 in six to twelve months. One wedding booking from the ads in that time pays for it in every case above. The click-to-enquiry and enquiry-to-booking rates are not measurable from Ads at this volume (most senders decline cookies, so "Submit lead form" understates; see the 23 Oct form diagnosis), so the test is bookings in the ledger with an ad source, counted by the Monday review's section 11.

## Actions

| # | When | What | Guardrail | Success measure | Exit |
|---|---|---|---|---|---|
| 1 | 23 Oct, on approval | Add a second responsive search ad to "Ad group 1": `scripts/ads/wedding_season_rsa_2026_10_23.py` (copy below). The current ad stays. | Validate-only first; Luca's approval; log row | "wedding choir" expected CTR moves to Average by the 5 Jan check | April 2027: pause the ad with the lower CTR once each has 300+ impressions; never remove |
| 2 | 5 Jan 2027, Monday review | Bid check. If lost-to-rank is still above 25% over the last 28 days, propose [wedding choir] exact £4.50 → £5.00 and "wedding choir" phrase £4.00 → £4.50 in one dated script | A bid change, not a budget change, answers lost-to-rank (marketing-skills plan, `lcs-review-ads`) | Search impression share above 70% by February | If cost per click rises above £4.50 with no enquiry in 28 days, return to today's bids |
| 3 | Mondays, Jan–Mar 2027 | Budget rule. Keep £4. If budget-lost share passes 10% on two Mondays running, propose £5 (the cap) | Never above `budget_cap.py`; no window change in `data/budget-windows.yml` unless the rule fires | Budget-lost stays under 10% | Back to £4 from 1 April if raised |
| 4 | Mondays | Search terms and negatives through the Monday review as now | Never add singer, soloist, solo or vocalist keywords | Every spend line is a choir search | — |
| 5 | Before 5 Jan | weddings.html proposals below, done by whichever session owns the page then | Another session is editing weddings.html (23 Oct) | Landing page experience stays Average or better | — |
| 6 | April 2027 | Review: ad test result, bookings with an ad source, whether to refresh "Book Your 2027 Wedding Choir" for 2028 | — | — | — |

**Not changing:** the £4 budget (spend runs at half of it), the 07:00–20:00 schedule (the evening hours took clicks with no conversions on the old set-up; too few clicks since to test again), the keyword set (close variants already cover "wedding choirs" and "hire a choir for wedding"), presence targeting and the home-county locations, manual CPC, the Wedding Planning audience at +20%. No new sitelinks or callouts: six sitelinks and six account callouts already serve.

## The new ad (action 1)

Final URL `weddings.html`, display path `/wedding-choir/hire`, no pins. "wedding choir" appears in five headlines and three descriptions; the current ad has it in two of each and pins its price headline. Every claim traces to `weddings.html`, `pricing.html` or `about.html`; the script checks lengths, prices and the house-rule patterns before sending.

Headlines: Wedding Choir in London · Hire a Wedding Choir · London Wedding Choir Hire · Book Your 2027 Wedding Choir · Wedding Choir from £1,150 · Four to Twelve Voices · Choir for Your Church Wedding · Processional to Recessional · Zadok for the Processional · Add an Organist for £250 · Conservatoire-Trained Singers · Music Planned with You · Quote Within 1 Working Day · Church or Country House · The London Choral Service

Descriptions:
- Wedding choir hire with rehearsals, sheet music and travel within London included.
- Prices from £1,150 for four voices, £1,400 for five, £1,600 for six, £2,000 for eight.
- We plan the processional, hymns, register signing and recessional with your wedding choir.
- Wedding choir singers from the Royal Academy, Royal College and Guildhall. Send your date.

**Test hypothesis:** the unpinned ad with the keyword in more lines beats ad 826000407486 on CTR for "wedding choir" searches by April 2027. With about 150 impressions a month split across two ads, judge CTR only; conversions are too few to compare.

## weddings.html for January (proposals only)

Another session is editing the page on 23 Oct (new hero, H1 "Hire a wedding choir in London"). After it lands:

1. **Reply time.** "How it works" step 1 says "We call you back within hours"; the hero form, the about page and the ads say "within one working day". Pick one; the ads use the working day.
2. **2027 line in the hero offer.** The ad says "Book Your 2027 Wedding Choir"; the page has "Around six months ahead is ideal" lower down. One hero line such as "Booking for 2027? Around six months ahead is ideal, and we take later dates too" carries the message from ad to page.
3. **"Last updated: August 2026".** Refresh it with the January edit so a couple reading in January does not see a stale date.
4. **Choir examples first.** The "Hear our musicians" list ends on Ave Maria by a soloist. Keep it, but lead with the choral pieces the ad names (Zadok, Ubi Caritas), so a choir search lands on a choir.
5. **Form.** The wedding date field is optional and sits below the occasion select. For wedding traffic, prefill "Wedding" in the occasion select when the visitor arrives on weddings.html, and ask for the venue, which every quote needs.
6. **Check (not this page):** `pricing.html` FAQ JSON-LD says "All prices include fees and taxes". Alma Consort Ltd is not VAT-registered; "No VAT is added" says it without suggesting VAT is inside the price.

## Verification

- `python scripts/ads/wedding_season_rsa_2026_10_23.py` prints the change and "Google accepted every operation"; after `--apply`, `logs/ads-changes.md` has the row and the MCP shows two enabled ads in "Ad group 1".
- 5 Jan 2027: `keyword_view` for the two "wedding choir" keywords shows expected CTR and Quality Score; the Monday report's section 4 shows lost-to-rank and lost-to-budget for wedding-leads.
