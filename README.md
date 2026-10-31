# CitiSevik — revised working prototype

A self-contained municipal infrastructure decision-support prototype built with **FastAPI + SQLite + vanilla HTML/CSS/JS**. It runs locally and does not require Emergent credits, paid APIs or a cloud database.

## Run locally

1. Install Python 3.10+.
2. Double-click `Run_CitiSevik_Windows.bat` (Windows), or run the Mac/Linux shell script.
3. Open `http://127.0.0.1:8000`.

The first launch installs the small Python dependencies, creates SQLite and seeds the sample project / complaint records. API documentation: `http://127.0.0.1:8000/docs`.

## What changed in this revision

- **Avoided-rework comparison:** illustrative ₹68 lakh separate works vs ₹62 lakh coordinated package, showing ₹6 lakh potential avoided rework. Uncoordinated drainage after resurfacing is marked High repeat-excavation risk.
- **Option-specific rationales and score breakdowns:** drainage, road repair, green/blue retention and combined package each show their own drivers.
- **Priority explanation:** ranked areas show rank, percentile, overall score and component drivers. Compare preselects the top-ranked area; selecting another area highlights its grid cell on the map.
- **Workflow guards:** start requires acknowledgement; resolve requires work in progress; verify requires resolved status. Case lists can be sorted high-to-low / low-to-high urgency, newest or oldest.
- **More infrastructure context:** seeded water-pipeline replacement project creates another utility coordination example.
- **Outcome measures:** potential conflicts flagged vs manually verified, repeat complaints after a recorded fix, and average days to acknowledge. Empty measures are shown as zero / unavailable with a caveat, not as proof of success.
- **Citizen view:** citizens see only a report form and status tracking. A submitted report returns a reference and private tracking code; the status endpoint requires both. Staff views are hidden from the citizen interface and staff endpoints reject the citizen role.
- **Public-location alignment check:** 1 of 3 approximate public locality references (Matunga, Sion, Wadala) is within 500 m of one of the ten highest flood-screening cells. This is a coarse exploratory location-alignment check, not predictive validation; the source articles do not supply exact point coordinates.
- **90-second guided demo:** a five-step presenter walkthrough for road repair, drainage / pipeline coordination, complaint cluster, response suggestions and intervention comparison.
- Renamed “Smart Municipal Response Engine” to **Rule-based response suggestions**.
- Global case studies retain Singapore and Copenhagen and add a Mumbai example (Hindmata / King's Circle holding and pumping measures) for local comparison.

## Prototype data and honest limitations

- The map includes the supplied 208-cell / 3,558-road dataset, water geometry and modelled screening indices.
- Seeded projects and complaints are illustrative; citizen-entered demo reports are stored locally.
- Flood, air and density metrics are screening proxies, not validated predictions.
- Project clashes are potential proximity / schedule alerts until checked against utility records and site conditions.
- ₹68L vs ₹62L is a scenario assumption, not measured savings or a municipal estimate. Other intervention costs are placeholders.
- The public-location check uses approximate locality centroids and coarse grid cells. It is not a formal validation study.
- **Role handling is prototype-level:** citizen UI restrictions, endpoint role checks and report tracking codes are implemented, but the role selector is not a real identity provider. Do not deploy publicly or store real personal data. Production use needs authenticated accounts, secure sessions, ownership checks, audit controls and municipal approval.
- No live BMC/NMMC integration, real notifications, field inspection, verified utility GIS, calibrated flood/traffic models or production deployment.
- Global case studies are reference examples, not automatic recommendations; local feasibility still needs engineering review.

## Reset demo data

Stop the server and delete `app/backend/citisevik.sqlite3`. It will be recreated and reseeded at next launch.
