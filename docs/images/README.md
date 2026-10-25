# Screenshots

These images show the running application on October 25, 2026.

| File | Shows |
|---|---|
| `roomwise-explore.png` | Explore: one card per property, billing labels, price ranges and an OpenStreetMap overview |
| `roomwise-property.png` | A property plan with whole-unit pricing, a splitting scenario and separately classified fees |
| `roomwise-compare.png` | Two plans compared with their original billing periods and unresolved lease facts |
| `roomwise-assistant.png` | The local research helper answering a billing question |

## How they were captured

- Run the app against an isolated data directory with providers disabled (`ROOMWISE_AI_PROVIDER=disabled`, maps and routes off, no API tokens), so no paid calls are made and personal workspace notes are not shown.
- Prices are historical asking figures from the dated catalog. They are not current quotes.
- The assistant image shows the labeled local helper. It is not a Gemma response.
- Map tiles come from OpenStreetMap and are subject to its attribution requirements.

These are illustrative captures of the interface, not evidence of any property's terms.
