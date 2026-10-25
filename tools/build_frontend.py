"""Build the supplied dependency-free frontend for same-origin FastAPI serving."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
frontend=ROOT/'CampusHousing-main'
source=frontend/'src'
shell=(source/'shell.html').read_text(encoding='utf-8')
shell=shell.replace('/*CSS*/',(source/'styles.css').read_text(encoding='utf-8')).replace('/*HERO*/','/assets/hero.webp')
scripts=['data.js','core.js','views1.js','views2.js','views3.js','api.js','assistant.js','maps.js','data-tools.js','housing-guide.js','app.js']
shell=shell.replace('<script>\n/*JS*/\n</script>','\n'.join(f'<script defer src="/assets/{name}"></script>' for name in scripts))
split=shell.index('<a class="sr"')
head,body=shell[:split],shell[split:]
document='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+head+'</head><body>'+body+'</body></html>\n'
(frontend/'index.html').write_text(document,encoding='utf-8')
print(f'Built {frontend / "index.html"}')
