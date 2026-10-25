# Roomwise Maps plan

## Current property workflow

The local app also works without Google credentials: it serves Leaflet 1.9.4 locally and displays OpenStreetMap street tiles with visible attribution. Only the current viewport is requested; browser caching is retained. The map shows one marker per property with a sourced address point. All guide references remain in the main list. Detail pages without coordinates have a clearly labeled address-search embed, with no claimed point or distance. Google Places results are never plotted on the OpenStreetMap fallback.

Explore defaults to all 47 places, including the 41 insufficient-evidence entries. The 68 original priced floor plans and 72 newly researched operator figures are grouped on the right of their property cards. The new figures are observations, not automatically promoted lease quotes. Mobile cards stack prices below the property information. Map containers survive view rerenders, resize when shown, and retain the viewport when selecting a marker. Google Maps remains available when configured.

For the local OpenStreetMap mode, an explicit nearby search uses `https://overpass.maprva.org/api/interpreter` for the selected property, category and radius. Results are filtered to the radius and sorted by straight-line distance, capped at eight, cached in process memory for five minutes, attributed, and plotted as numbered pins. They are not persisted in workspaces, frozen briefs or training. Missing locations and provider failures stay visible. The existing daily request budget also caps these requests. Public service coverage is not proof of a business's current operation or hours.

Explore has one card and map marker per property. Select a plan to open its costs, sources and “Life around” section. Search restaurants, groceries, gas stations, cafes, pharmacies or libraries within 1, 2.5 or 5 km. Each explicit search requests at most eight results ranked by distance. It returns locations, addresses, Maps links and provider attribution; it does not request reviews, ratings, photos or opening hours.

Results show straight-line distances from the approximate property point. Numbered markers identify the returned places, and “Show on map” focuses one. Walk/drive/bike/transit directions open Google Maps using the property origin and destination place ID. The app never asks for device location. Those links do not require an additional app API call or establish a travel-time estimate inside Roomwise.

No Places results enter SQLite, exported briefs, assistant context or training data. Results exist in browser memory for the current property and are cleared on a different property search. A category/radius change requires a fresh explicit search. In-flight results from an earlier property or category cannot replace the current results. Empty results and provider/quota failures remain visible, with no invented fallback businesses.

The combined daily Places/Routes request cap still applies, including failures. At most eight slots (20% for smaller caps) are reserved for Places, so automatic route recomputations cannot consume every available slot. Existing spent attempts are never reset. Browser Maps SDK usage is outside this server cap and must also be controlled in Google Cloud.

## Next priorities

1. **Walking and driving times for selected essentials.** Add an explicit “Check travel times” action for the visible results, with one property origin and up to eight destinations. Routes `computeRouteMatrix` is a suitable candidate, but its budget must count billable origin/destination elements, not merely HTTP requests. Keep durations transient. Show straight-line distance until a supported route arrives; show unsupported rows separately. Test an eight-destination success, partial failure, quota exhaustion and mode changes.
2. **Grocery reach in housing comparisons.** Only on explicit user request, check a few selected properties and a declared walking threshold. Show provider/date/mode and missing coverage. Unknown reach must remain unknown, and grocery access must not become a neighborhood safety or demographic ranking. Do not search every property on each keystroke or page load.
3. **Place details on demand.** A clicked business could load opening hours and accessibility fields through Place Details, after verifying the exact fields' SKU and reuse rules. Display provider attribution and freshness. No global bulk details calls; missing hours must not be interpreted as closed.
4. **Saved planning inputs.** Save chosen categories, radius and intent. Re-fetch provider results when reopening a brief instead of retaining Google content. Establish retention rules for any persistent Place IDs before implementing them.
5. **Usability and spend controls.** Add category icons, keyboard focus between list and markers, request/remaining-budget visibility, mobile map expansion, and separate operational alerts for provider denial versus exhausted local quota. Keep private service keys server-side and restrict the browser key by origin/API.

For the existing campus commute flow, prioritize the active property or shortlist before a full-catalog refresh. The bundled GTFS fallback currently covers October 2026, direct bus trips and approximate walks; it does not establish live delays, transfers or travel after the feed expires.

## Required Google services

The implemented workflow uses Maps JavaScript API and Places API (New). Existing Routes API access covers the proposed travel-time work; it still needs a separate matrix adapter and budget accounting. Google Search grounding is unnecessary for nearby business lookup. A trained Gemma model does not supply current business locations, prices, route times or opening hours.

References: [Nearby Search](https://developers.google.com/maps/documentation/places/web-service/nearby-search), [Maps URLs](https://developers.google.com/maps/documentation/urls/get-started), [Route Matrix](https://developers.google.com/maps/documentation/routes/compute_route_matrix).
