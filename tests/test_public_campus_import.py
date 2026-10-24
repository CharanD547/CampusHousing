import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('collect_vt',Path(__file__).parents[1]/'tools/backend/collect_vt_public_data.py')
collector=importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def test_public_buildings_exclude_ambiguous_future_remote_and_missing_records():
    features=[{'attributes':dict(objectid=i,name=f'Building {i}',bldg_num=str(i),status='Existing Conditions',
                               bldg_use='Academic',latitude=37.23,longitude=-80.42)} for i in range(25)]
    features.extend([features[0],{'attributes':{**features[1]['attributes'],'status':'Planned'}},
                     {'attributes':{**features[2]['attributes'],'bldg_num':'remote','latitude':38}},
                     {'attributes':{**features[3]['attributes'],'bldg_num':'<Null>'}}])
    records=collector.building_records({'features':features},'2026-10-24')
    assert len(records)==24 and not any(b['id']=='vt-0' for b in records)
    assert all(b['coordinate_basis']=='official_gis_building_location' for b in records)
    with pytest.raises(ValueError):
        collector.building_records({'features':features,'exceededTransferLimit':True},'2026-10-24')
