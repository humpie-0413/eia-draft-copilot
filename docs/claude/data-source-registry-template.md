# Data Source Registry Template

| Source Name | Provider | Access Type | Format | Geometry Basis | CRS | Update Cadence | Quota / Limits | Mandatory for MVP | Fallback | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| NIER 사업구역정보 | NIER | API | XML/JSON | Project area | ? | ? | ? | Yes | None | |
| NIER 결정내용정보 | NIER | API | XML/JSON | Procedure / case | N/A | ? | ? | Yes | EIASS page scrape/manual | |
| NIE 생태자연도 | NIE | API/WMS/WFS | XML/WMS/WFS | Baseline ecology | 5186 / convert | ? | ? | Yes | Cached layer | |
| KMA 단기예보 | KMA | API | JSON/XML | Grid | regional | frequent | ? | Optional | none | screening only |
| AirKorea | KECO | API | XML/JSON | Station | station | frequent | lower quota | Optional | none | screening only |
| 국토환경성평가지도 | Public | API | spatial | regional | ? | ? | ? | Optional | file cache | |
