# Wikidata drafts: Luca Wetherall and The London Choral Service

Drafted 24 Oct 2026. Luca creates both items himself; Claude never creates a Wikidata account or edits Wikidata. Public facts only: this repo is public. Nothing here comes from `~/lcs-private`.

## 1. Will they survive? (WD:N, honestly)

Wikidata keeps an item if it meets **one** of three criteria ([WD:N](https://www.wikidata.org/wiki/Wikidata:Notability)): (1) it has a sitelink to a Wikimedia page, (2) it is a clearly identifiable entity described by serious, publicly available references, or (3) it fills a structural need (other items link to it). Neither item has a Wikipedia page, so both rest on criterion 2.

| Item | Verdict | Why |
|---|---|---|
| **Luca Wetherall** | Likely to survive, not certain | An independent institutional page (Oxford Faculty of Music), the Companies House officer record and a public ORCID iD each identify him. Wikidata is lenient with academics who have an ORCID. The weakness: the ORCID has no works listed, and no independent press or reviews were found. |
| **The London Choral Service / Alma Consort Ltd** | Borderline, and I would expect a deletion request to be plausible | One reliable, independent record exists (Companies House). Everything else is our own site, our own Google Business Profile and our own YouTube channel, which show it exists but not that it is notable. Wikidata does hold many registry-only companies, but patrollers do delete small ones with no independent coverage. |

**Recommendation: create Luca's item first.** Then create the business item only if you can add at least one independent source about it (a venue, cathedral, planner, funeral director or press page that names The London Choral Service). Without one, the business item is likely to be challenged. If it is deleted, nothing is lost on the site; the Companies House link stays in `sameAs`.

Two honest limits on the sources:

- No independent coverage of the business was found. Nothing here invents one.
- Delphian credits, the BBC Radio 3 broadcast of *The Blue Bird* and the BBC Singers performances are **not** in the drafts. The only third-party mention of the Radio 3 broadcast found is an aggregator page marked "data may be outdated", and the Delphian and BBC claims could not be verified from an independent page. Add them only with a Delphian catalogue page, a BBC programme page or similar, per claim.

Conflict of interest: Wikidata allows editing about yourself or your business if the statements are sourced and neutral (see [Wikidata:Autobiography](https://www.wikidata.org/wiki/Wikidata:Autobiography)). Say so on the item's talk page if asked. Keep to sourced facts, nothing promotional.

**Privacy (living person).** Companies House shows Luca's full name and birth month and year. Leave out date of birth, middle names, residence and any home address. Statements about living people must be sourced and conservative.

## 2. Item A: Luca Wetherall

Label (en): `Luca Wetherall`
Description (en): `British musician and conductor, doctoral researcher at the University of Oxford` (keep it to what the references support; do not write "Tutor in Music" unless the Oxford page states it)
Aliases: none needed.

| Label | Property (P-number) | Value | Reference URL |
|---|---|---|---|
| instance of | P31 | human (Q5) | none needed |
| ORCID iD | P496 | `0000-0001-9099-2485` | https://orcid.org/0000-0001-9099-2485 (public record: name Luca Wetherall; education entries; no works) |
| educated at | P69 | University of Oxford (Q34433) | https://www.music.ox.ac.uk/people/luca-wetherall (page lists a BA (Oxon) and a DPhil in progress) |
| educated at | P69 | Royal Holloway, University of London (search for the Q-id) | https://orcid.org/0000-0001-9099-2485 (education entry: MMus Musicology, start Sept 2023) |
| academic degree | P512 | Master of Music (search for the Q-id), qualifier P69 Royal Holloway | same ORCID record. The Oxford page also lists an MMus from the University of London |
| affiliation | P1416 | University of Oxford (Q34433), qualifier P1319/start time left blank | https://www.music.ox.ac.uk/people/luca-wetherall (page lists him as a DPhil student with teaching) |
| affiliation | P1416 | St Hugh's College, Oxford (search for the Q-id) | https://www.music.ox.ac.uk/people/luca-wetherall |
| occupation | P106 | musician (Q639669) | https://londonchoralservice.com/luca-wetherall.html (first-party; replace with an independent page if one turns up) |
| occupation | P106 | conductor (Q158852) | same page, same caveat |
| country of citizenship | P27 | United Kingdom (Q145) | https://find-and-update.company-information.service.gov.uk/company/16785727/officers (lists nationality British) |
| official website | P856 | `https://lucawetherall.co.uk` | none needed |
| described at URL | P973 | `https://www.music.ox.ac.uk/people/luca-wetherall` | none needed |

What the drafts deliberately leave out, and why:

- **Employer (P108) University of Oxford, "Tutor in Music".** Our pages say "Tutor in Music". The Oxford faculty page, as read for this draft, describes DPhil study, Clarendon Fund funding and a long list of teaching topics, but a formal employment title was not confirmed there. So the draft uses *affiliation* (P1416), which the page does support. Re-read the page; if it states a Tutor post, switch to P108 with that page as the reference.
- **Clarendon Scholar.** Supported by the faculty page (funding by the Clarendon Fund). Add `award received` (P166) only if you find the Q-id for Clarendon Scholarship and keep the faculty page as the reference.
- **Merton choral scholar, Director of Music at St Barnabas Ealing, Company Carpi, Delphian albums, BBC Radio 3.** Only our own page supports them here. Add each only with an independent URL (the church's own music page, Merton College, Delphian's catalogue, the BBC).
- **Notable performances, works, compositions.** Left out until independent sources exist.
- **Date and place of birth, sex or gender, residence.** Left out on purpose.

## 3. Item B: The London Choral Service (trading name of Alma Consort Ltd)

Create this only after Item A exists (or add a second source first; see section 1).

Modelling choice: the trading name and the company are one legal entity, so one item. Label it with the public trading name and record the legal name in `official name` and as an alias.

Label (en): `The London Choral Service`
Aliases (en): `London Choral Service`, `Alma Consort Ltd`
Description (en): `choir-for-hire business in London, United Kingdom, operating name of Alma Consort Ltd`

| Label | Property (P-number) | Value | Reference URL |
|---|---|---|---|
| instance of | P31 | business (Q4830453) | https://find-and-update.company-information.service.gov.uk/company/16785727 |
| instance of | P31 | private company limited by shares (Q6832945) | same Companies House page (type: private limited company) |
| official name | P1448 | `Alma Consort Ltd` (language: English) | same Companies House page |
| Companies House company ID | P2622 | `16785727` | same Companies House page |
| inception | P571 | 15 October 2025 (day precision) | same Companies House page (date of incorporation). This is the company's date, not the date the service started trading: do not present it as the start of trading |
| country | P17 | United Kingdom (Q145) | https://find-and-update.company-information.service.gov.uk/company/16785727 (registered office in England) |
| headquarters location | P159 | London (Q84) | same page (registered office: N1 7GU, London). Use the city, not the street address |
| official website | P856 | `https://londonchoralservice.com` | none needed |
| founded by | P112 | Luca Wetherall (Item A) | https://londonchoralservice.com/luca-wetherall.html (first-party, says he founded the service) |
| director / manager | P1037 | Luca Wetherall (Item A), start time 15 October 2025 | https://find-and-update.company-information.service.gov.uk/company/16785727/officers (Active director, appointed 15 Oct 2025) |
| industry | P452 | performing arts (search for the Q-id) | Companies House page (SIC 90010, Performing arts) |
| described at URL | P973 | `https://londonchoralservice.com/about.html` | none needed |

Do not add:

- **Musical ensemble (Q2088357).** The service is a booking business that assembles singers per job; Wikidata editors would likely read that as a business, not a standing ensemble. Use "business".
- **The second Companies House director** (resigned 22 Sep 2026): leave off.
- **Confirmation-statement and accounts dates, the registered-office street address, the company's SIC code beyond industry:** unneeded.
- **YouTube channel (P2397) and Google Maps ID:** optional and self-published; add only if you want them, after the main statements.
- **Any award, review rating, client or roster-size claim.** None, and the site rule against advertising roster size applies here too.

## 4. Click-by-click: create the items

Do Item A first.

1. Go to https://www.wikidata.org and choose **Create account** (top right). Use a username you are happy to have public. Confirm the email. Use the same account for both items.
2. Search Wikidata for `Luca Wetherall` and `London Choral Service`. Check no item exists (none did on 24 Oct 2026). If one does, edit it instead of creating a duplicate.
3. Open https://www.wikidata.org/wiki/Special:NewItem.
4. For Item A: Language `en`, Label `Luca Wetherall`, Description from section 2, no aliases. Choose **Create**.
5. On the new item page, under **Statements**, choose **add statement**. For each row of the section 2 table: type the property (for example `instance of`), pick it from the list, type the value, pick it from the list, then press the tick.
6. For the references: under the saved statement choose **add reference**, pick `reference URL` (P854), paste the URL and press the tick. Also add `retrieved` (P813) with today's date, which Wikidata editors expect on web references.
7. For `educated at` and `affiliation`, search for the college or university by name and check the description before choosing. If a value has no item (the Q-id above says "search"), leave it out; do not create new items for colleges.
8. Add the ORCID iD under `ORCID iD` (P496) exactly as `0000-0001-9099-2485`.
9. Reload and read the item once as a stranger would. Every statement should have a reference, or be self-evident (`instance of human`).
10. For Item B: repeat steps 3 to 8 with section 3. For `founded by` and `director / manager`, start typing `Luca Wetherall` and pick Item A (check the Q-id matches the item you just made). Note the Q-id of each item (shown top right after the title, for example `Q123456789`).
11. Link the two. The links are the two statements on Item B: `founded by` (P112) and `director / manager` (P1037), both pointing to Item A. Item A needs no reverse statement: Wikidata shows incoming links on its own page ("What links here").
12. After saving, check the **Watch** star on both pages so you see any edits or deletion nominations. Wikidata edits are public and permanent in the history.

If an editor tags either item for deletion (Wikidata:Requests for deletions), answer politely there with the independent sources; do not recreate a deleted item.

## 5. Follow-up on the site (not done in this PR)

Another session is editing the schema, so these edits are left for after the Q-ids exist. In each, add the URL `https://www.wikidata.org/wiki/Qxxxx` to the existing `sameAs` array. Use the real Q-id; never publish a placeholder.

| File | JSON-LD node | Add |
|---|---|---|
| `index.html` | `/#organization` `sameAs` (the list ending with the Companies House and YouTube URLs) | Item B URL |
| `index.html` | `/#organization` → `founder` (`luca-wetherall.html#person`) `sameAs` | Item A URL |
| `luca-wetherall.html` | `#person` `sameAs` | Item A URL |

Then run `./build.sh` (it validates the JSON-LD) and open a normal content PR. Optionally also mention the Wikidata items in `llms.txt`'s entity section if there is one, and add Item B's URL to `data/seo-fix-discovered-urls.yml` if that file is the home for discovered entity URLs (it is the single source of truth for unresolved schema values; do not invent the Q-id before it exists).

Do not add `sameAs` to Wikidata before the item exists and has been checked: a link to a deleted item does more harm than none.

## 6. Source list (all public)

- Companies House, company 16785727 (Active; private limited company; incorporated 15 Oct 2025; SIC 90010 Performing arts): https://find-and-update.company-information.service.gov.uk/company/16785727
- Companies House officers (Luca Wetherall, active director, appointed 15 Oct 2025, British): https://find-and-update.company-information.service.gov.uk/company/16785727/officers
- Oxford Faculty of Music people page: https://www.music.ox.ac.uk/people/luca-wetherall
- ORCID record: https://orcid.org/0000-0001-9099-2485 (public API: given name Luca, family name Wetherall; education: University of Oxford, and Royal Holloway MMus Musicology from 1 Sept 2023; no works)
- Site pages: `about.html`, `luca-wetherall.html`, `index.html` (JSON-LD)
- Wikidata policy: https://www.wikidata.org/wiki/Wikidata:Notability

Checked 24 Oct 2026: property P2622 is "Companies House company ID". Q5, Q4830453, Q6832945, Q34433, Q145 and Q84 were confirmed in a Wikidata search. Q639669 (musician) and Q158852 (conductor) are from memory, as are the property numbers other than P2622 (P31, P17, P159, P571, P112, P1037, P1448, P496, P69, P512, P1416, P106, P27, P856, P973, P452; all standard, but the property picker shows each label, so match it to the Label column): confirm each on the item's page before saving. Rows marked "search for the Q-id" were not looked up.
