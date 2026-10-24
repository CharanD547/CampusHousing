"""Only explicitly supplied, source-backed building records are accepted."""
import json
from roomwise.api.errors import APIError
from roomwise.config import ROOT


class CampusRepository:
    def __init__(self, path=None):
        self.campuses = json.loads((path or ROOT/'data/campuses.json').read_text(encoding='utf-8'))['campuses']

    def get(self, campus_id):
        campus = next((c for c in self.campuses if c['id'] == campus_id), None)
        if campus is None:
            raise APIError('unsupported_campus', 'This campus is not supported.', 404)
        return campus

    def building(self, campus_id, building_id):
        building = next((b for b in self.get(campus_id)['buildings'] if b['id'] == building_id), None)
        if not building or not building.get('source') or building.get('verified') is not True:
            raise APIError('unknown_building', 'Choose a source-verified building; ambiguous destinations are not inferred.')
        return building
