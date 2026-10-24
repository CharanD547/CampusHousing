"""Provider boundary. Missing classroom routing is never replaced by straight-line math."""
from typing import Protocol


class RoutingAdapter(Protocol):
    def estimate(self, candidate, building, commitment, mode, route_date, preferences) -> dict: ...


class UnconfiguredRoutingAdapter:
    provider = 'not_configured'

    def estimate(self, candidate, building, commitment, mode, route_date, preferences):
        return dict(candidate_id=candidate['id'], commitment_id=commitment.id,
                    destination_id=building['id'], mode=mode, minutes=None, status='unavailable',
                    route_date=route_date.isoformat(), provider=self.provider,
                    context={'arrival_time_local': commitment.arrival_time_local.isoformat(),
                             'arrival_buffer_minutes': commitment.arrival_buffer_minutes if commitment.arrival_buffer_minutes is not None else preferences.arrival_buffer_minutes,
                             'weekdays': commitment.weekdays, 'timezone': 'America/New_York',
                             'origin_basis': candidate['coordinate_basis']},
                    coverage_notes=['No verified building-to-building routing provider is configured. The retained GTFS adapter supports only historical campus transit-center examples.'],
                    evidence_ids=[])
