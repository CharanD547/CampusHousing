from roomwise import config


def test_local_dotenv_keys_load_without_repr_exposure(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'ROOT',tmp_path)
    for name in ('ROOMWISE_MAPS_JAVASCRIPT_API_KEY','ROOMWISE_PLACES_API_KEY','ROOMWISE_ROUTES_API_KEY'):
        monkeypatch.delenv(name,raising=False)
    (tmp_path/'.env').write_text('ROOMWISE_MAPS_JAVASCRIPT_API_KEY=test-browser-value\nROOMWISE_PLACES_API_KEY=test-private-value\n')
    settings=config.Settings.from_env()
    assert settings.maps_javascript_api_key=='test-browser-value'
    assert settings.places_api_key=='test-private-value'
    assert settings.routes_api_key==''
    assert 'test-browser-value' not in repr(settings) and 'test-private-value' not in repr(settings)
    monkeypatch.setenv('ROOMWISE_PLACES_API_KEY','process-override')
    assert config.Settings.from_env().places_api_key=='process-override'


def test_credentials_file_is_not_served(client):
    assert client.get('/.env').status_code==404
    assert client.get('/assets/../../.env').status_code==404
