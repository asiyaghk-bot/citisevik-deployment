# CitiSevik — consolidated revision changelog

## Decision support and coordination
- Added ₹68L separate vs ₹62L coordinated scenario (₹6L illustrative avoided rework).
- Marked drainage after resurfacing as High repeat-excavation risk when uncoordinated.
- Added distinct rationale and option-specific score contributions for each intervention.
- Added rank, percentile and full score-driver breakdown for priority cells.
- Preselects top-ranked area in comparison; Compare selection outlines the corresponding map cell.
- Added a water pipeline replacement project to the seed register and project form.

## Workflow and citizen access
- Added strict submitted → acknowledged → in-progress → resolved → verified transition checks.
- Added urgency and date sorting to case list.
- Citizen view only exposes report submission and tracking; report tracking requires reference plus private code; staff endpoints reject citizen-role requests.
- Added repeat-after-fix detection for new citizen reports matching a previously resolved citizen report within 150 m / 90 days.

## Measurement and presentation
- Replaced department league table with outcome measures: conflicts flagged / verified, repeat complaints after fix, average acknowledgement time.
- Added approximate public-location alignment check: 1/3 locality references within 500 m of top-ten modelled flood-screening cells. It is explicitly labelled exploratory, not model validation.
- Added five-step 90-second guided demo scenario.
- Renamed Smart Municipal Response Engine to Rule-based response suggestions.
- Kept Singapore and Copenhagen examples; added a Mumbai Hindmata / King's Circle drainage benchmark.

## Verification
- Python compile: passed.
- JavaScript syntax: passed.
- Backend tests: 7 passed.
- Test coverage includes coordination comparison values, option score breakdowns, public-location check output, workflow transition guards, and citizen tracking-code access.

## Known limits
- The ₹68L / ₹62L scenario is illustrative, not measured savings.
- Public location centroids are approximate and do not come with exact point coordinates from the cited reporting.
- Header-based role switching is a prototype access simulation, not production authentication.
- Seed data remains synthetic and local; no municipal system is connected.

## Analytics redesign (31 Oct 2026)
- Replaced department analytics with Coordination & Completion analytics only; no department league table.
- Added partner acknowledgement completion percentage and a case-level Waiting on bottleneck list with department and days waiting.
- Added a cumulative completion funnel, in-progress count and overdue open cases.
- Added flagged → verified → coordinated conflict pipeline and linked the illustrative ₹6L avoided-rework scenario (₹68L separate vs ₹62L coordinated).
- Added repeat complaint follow-up counts and average acknowledgement time in hours.
- Seeded illustrative case statuses, partner acknowledgements, repeat follow-ups and acknowledgement timestamps so the page demonstrates non-zero examples.
- Every analytics panel is labelled illustrative; zeros are explicitly not evidence that no real-world event occurred.
- No other page was intentionally changed.

## Analytics micro-fix (31 October 2026)
- Clarified the road-repair / drainage dependency using the project register's month-level dates: December 2026 completion to February 2027 start is approximately 8.7 weeks; recommendation is drainage and underground utilities before final resurfacing.
- Completion funnel now distinguishes cumulative in-progress cases from the count currently in progress.
- Conflict pipeline now lists project IDs, flagged/verified/coordinated status, verifier role and verification/co-ordination timestamps. The illustrative ₹6L scenario is attached only to the coordinated road/drainage repeat-excavation conflict.
- Repeat-rate display uses the division symbol (÷).
- Analytics page only; no other page UI changed.
