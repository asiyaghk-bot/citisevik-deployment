# CitiSevik revision notes

## This revision
- Kept the older, cleaner map layout and retained the hybrid map approach.
- Kept all seven map layers: Projects, Flood, Traffic, People, Air quality, Complaints and Priority areas.
- Retained hover details for project markers, complaint clusters, potential clashes and risk-screening areas.
- Retained the map priority-action summary for complaint clusters, potential project clashes and high-priority open cases.
- Decision Support now uses approximate locality labels: Near Sion, Near Matunga and Near Wadala, rather than generic north/south sample-area names.
- Technical grid cell IDs remain available as secondary references only.
- Slightly softened the light surfaces without switching to a dark theme.
- Cases & Workflow includes department, status and High-to-Low / Low-to-High priority filters.

## Important location qualification
The locality names are approximate nearest-locality labels based on hand-set reference points within the Matunga–Wadala–Sion sample map. They are not official ward boundaries, precise geocoding, or proof of municipal jurisdiction. Verify the exact locality and road-owning authority before operational use.

## Validation
- Backend Python compile: passed.
- Automated backend tests: 4 passed.
- Frontend JavaScript syntax check: passed.
- API smoke checks for map data, overlays, priority areas and intervention comparison: HTTP 200.
- Priority area API returned locality labels including Near Sion, Near Matunga and Near Wadala across the sample grid.
- Full browser visual QA across every map layer is still recommended on the user's machine; this build does not claim that has been completed.
