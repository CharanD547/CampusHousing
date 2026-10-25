"""Configuration only; importing the package never starts providers or opens storage."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def now():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_token: str = field(default='',repr=False)
    allowed_origins: tuple[str, ...] = ()
    external_operations_enabled: bool = False
    ai_provider: str = 'disabled'
    ai_model: str = ''
    ai_api_key: str = field(default='', repr=False)
    ai_base_url: str = 'http://127.0.0.1:11434/v1'
    ai_daily_requests: int = 30
    maps_javascript_api_key: str = field(default='',repr=False)
    places_api_key: str = field(default='',repr=False)
    routes_api_key: str = field(default='',repr=False)
    maps_enabled: bool = False
    places_enabled: bool = False
    routes_enabled: bool = False
    accounts_required: bool = False
    local_operator_enabled: bool = False
    maps_daily_requests: int = 60
    public_access: bool = False

    @classmethod
    def from_env(cls):
        from starlette.config import Config
        config=Config(env_file=ROOT/'.env' if (ROOT/'.env').exists() else None,environ=os.environ)
        def get(key,default=''):return config(key,default=default)
        return cls(Path(get('ROOMWISE_DATA_DIR', ROOT/'var')),
                   get('ROOMWISE_API_TOKEN'),
                   tuple(x.strip() for x in get('ROOMWISE_CORS_ORIGINS').split(',') if x.strip()),
                   get('ROOMWISE_EXTERNAL_ENABLED','false').lower() == 'true',
                   get('ROOMWISE_AI_PROVIDER','disabled'),get('ROOMWISE_AI_MODEL'),
                   get('ROOMWISE_AI_API_KEY'),get('ROOMWISE_AI_BASE_URL','http://127.0.0.1:11434/v1'),
                   min(1000,max(0,int(get('ROOMWISE_AI_DAILY_REQUESTS','30')))),
                   get('ROOMWISE_MAPS_JAVASCRIPT_API_KEY'),get('ROOMWISE_PLACES_API_KEY'),get('ROOMWISE_ROUTES_API_KEY'),
                   get('ROOMWISE_MAPS_ENABLED','false').lower()=='true',get('ROOMWISE_PLACES_ENABLED','false').lower()=='true',
                   get('ROOMWISE_ROUTES_ENABLED','false').lower()=='true',
                   get('ROOMWISE_ACCOUNTS_REQUIRED','false').lower()=='true',
                   get('ROOMWISE_LOCAL_OPERATOR_ENABLED','false').lower()=='true',
                   min(60,max(0,int(get('ROOMWISE_MAPS_DAILY_REQUESTS','60')))),
                   get('ROOMWISE_PUBLIC_ACCESS','false').lower()=='true')
