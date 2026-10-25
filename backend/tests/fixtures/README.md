# Test Fixtures — raw Elexon API responses (T1.1)

Saved during T1.1 exploration spike. All requests are unauthenticated GET to
`https://data.elexon.co.uk/bmrs/api/v1`.

| File | Endpoint | Query params | Rows | Notes |
|---|---|---|---|---|
| `fuelhh_jan15_sample.json` | FUELHH/stream | settlementDateFrom/To=2026-01-15, fuelType=WIND | 48 | One day sample |
| `fuelhh_jan01_to_feb01.json` | FUELHH/stream | settlementDateFrom=2026-01-01, settlementDateTo=2026-02-01, fuelType=WIND | 1536 | Full January window |
| `windfor_publishdt_jan14.json` | WINDFOR/stream | publishDateTimeFrom=2026-01-14T00:00:00Z, publishDateTimeTo=2026-01-14T23:59:59Z | 584 | One publish-day sample; 8 vintages, 73 target periods |
| `windfor_publishdt_jan14_sample.json` | WINDFOR/stream | same as above | 584 | Duplicate (for ingest tests) |
| `windfor_dec29_to_dec31.json` | WINDFOR/stream | publishDateTimeFrom=2025-12-29T00:00:00Z, publishDateTimeTo=2025-12-31T23:59:59Z | 1752 | Confirms historical depth |

Fetched: 2026-10-26 (UTC). Do not modify — used as parser fixtures.
