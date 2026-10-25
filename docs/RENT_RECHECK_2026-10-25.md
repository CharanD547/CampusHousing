# Rent recheck and UI polish — October 25, 2026

## Scope and evidence

Rechecked the rent-source URLs for every one of the 44 priced catalog properties. The directory still contains 47 guide references; three references have no priced catalog plans. The resulting catalog contains 304 plans, including five newly captured plans. Forty distinct URLs support 45 property/source groups (some URLs serve multiple properties).

21 source groups were checked against rendered browser text; 24 against bounded HTTP page text. All stored minimum and maximum amounts were found in those sources. **This is an amount-presence check, not certification that every plan, billing period, fee, lease term or availability is current.** Source pages can contain filter options, deposits and multiple terms; a numeric match alone must never promote a record to a verified quote. Browser snapshots and raw text are retained locally under ignored `var/rent-recheck-20261025/`.

## Corrections

- Added Edge’s 4-bedroom townhouse at $1,285; Hub’s 1x1+ at $2,019 and 4x4 Balcony at $1,175; Knollwood’s 3-bedroom condo at $2,225 and 268 Sheliah townhome at $2,500. Asking figures only.
- Upgraded Hub from a third-party listing to its official operator source.
- Replaced non-specific Knollwood portal roots with the operator floor-plan pages. Retained existing offer identifiers and expanded supported ranges, including the grouped townhome row to $2,200–$2,500.
- Houston Street plans now cite their own operator portal; the 703 Clay listing retains its separate source.
- Range upper bounds now survive catalog serialization and display. Room and whole-unit figures have separate rows and no combined numeric headline.
- Cards and property details show current check status, billing basis and a visible availability reminder. “Research option” replaces the misleading blanket “Criteria match” badge without changing the existing backend inclusion policy.
- All nearby distance/radius labels and provider descriptions use miles; requests retain meters (0.62, 1.55, 3.11 miles correspond to the existing 1,000/2,500/5,000-meter radii).

## Verification

- 93 Python tests and 25 Node tests passed; one existing upstream deprecation warning.
- Fresh SQLite HTTP release workflow passed with 304 offers and 350 campus buildings; zero live paid provider requests in that test.
- All 304 detail templates rendered against the actual running catalog without exceptions or invalid numeric output.
- All 44 property pages opened in visible Chrome at phone width with price evidence panels and no horizontal overflow or invalid numeric output. Desktop Explore retained 44 unique cards and 44 evidence summaries.
- Radius selector and keyboard navigation checked in visible Chrome. No new Places or Routes calls were needed; the Google browser map itself rendered.
- Backed up SQLite databases before applying catalog changes. Catalog/source versions retain replaced records; saved briefs remain frozen. No commit or push performed.

## Per-property source checks

| Property | Source check |
|---|---|
| Foxridge | Rendered source; stored amounts present |
| Alight Blacksburg | Retrieved source; stored amounts present |
| Union Blacksburg | Rendered source; stored amounts present |
| Terrace View | Rendered source; stored amounts present |
| Windsor Hills | Rendered source; stored amounts present |
| The Mill | Retrieved source; stored amounts present |
| The Edge Apartments & Townhomes | Rendered source; stored amounts present |
| Tech Terrace | Rendered source; stored amounts present |
| Haven Blacksburg (Haven on North Main) | Rendered source; stored amounts present |
| Old Row on North Main | Retrieved source; stored amounts present |
| Collegiate Court | Retrieved source; stored amounts present |
| The Lofts at 316 | Rendered source; stored amounts present |
| Kent Square Condos | Retrieved source; stored amounts present |
| Chase Apartments (The Chase) | Rendered source; stored amounts present |
| Downtown Boutique & Historic Rentals | Retrieved source, Rendered source; stored amounts present |
| Hub Blacksburg | Rendered source; stored amounts present |
| Park37 | Retrieved source; stored amounts present |
| Fourteen35 Apartments | Retrieved source; stored amounts present |
| Collegiate Suites & Hunters Ridge | Rendered source; stored amounts present |
| Chasewood Downs | Rendered source; stored amounts present |
| Shawnee Apartments | Rendered source; stored amounts present |
| Stonegate & Carlton Scott | Retrieved source; stored amounts present |
| Brexx at Blacksburg / The Retreat | Retrieved source; stored amounts present |
| Smith's Landing | Retrieved source; stored amounts present |
| Pack Place Apartments | Retrieved source; stored amounts present |
| The Farm | Rendered source; stored amounts present |
| Maple Ridge Townhomes | Rendered source; stored amounts present |
| The Summit at Uptown | Retrieved source; stored amounts present |
| 1711 Apartments | Retrieved source; stored amounts present |
| Cedar Pointe Apartments | Rendered source; stored amounts present |
| Cedarfield Apartments & Townhomes | Rendered source; stored amounts present |
| Additional North Main Rentals | Retrieved source; stored amounts present |
| The Vue Apartments | Rendered source; stored amounts present |
| The Reserve at Knollwood | Rendered source; stored amounts present |
| The Crossing at Knollwood | Rendered source; stored amounts present |
| Knollwood Condominium | Retrieved source; stored amounts present |
| Knollwood Townhomes | Retrieved source; stored amounts present |
| Highlands at Huckleberry Ridge | Retrieved source; stored amounts present |
| Pheasant Run Townhomes | Retrieved source; stored amounts present |
| Clover Valley (Phase I & CV2) | Retrieved source; stored amounts present |
| University Terrace & Progress St | Retrieved source; stored amounts present |
| Seneca Drive & Toms Creek Condos | Retrieved source; stored amounts present |
| Hearthstone / Creekside / Hilltop | Retrieved source; stored amounts present |
| Oak Manor & Camelot Court | Retrieved source; stored amounts present |


The full structured check, timestamps, source URLs and amounts are in `data/rent-source-recheck.json`. Exact availability, mandatory fees and conflicting billing descriptions still require a written operator quote.
