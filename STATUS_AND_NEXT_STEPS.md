# CitiSevik revision status

## Implemented in this build
- Avoided-rework scenario: ₹68L separate vs ₹62L coordinated, ₹6L illustrative difference.
- Separate intervention rationale and option-specific score breakdown.
- Priority area rank / percentile / score drivers; top area preselected; selected cell outline persists on map.
- Case sorting by urgency and date; guarded workflow transitions.
- Seed water pipeline replacement project and project form option.
- Outcome measures: flagged / verified clashes, repeat complaints after fix, average acknowledgement days.
- Citizen-only report and status page, with tracking reference + private code; citizen API requests are denied access to staff views.
- Public locality alignment check with 1/3 approximate locality references within 500m of top ten flood-screening cells.
- Five-step guided presenter walkthrough.
- Plain label “Rule-based response suggestions”.
- Mumbai Hindmata / King's Circle case reference added alongside Singapore and other international precedents.

## Verification performed
- Python compile passed.
- JavaScript syntax check passed.
- 7 backend tests passed.
- TestClient smoke checks returned HTTP 200 for staff pages and APIs.
- Citizen API was denied access to staff project records (403); report status lookup without token returned 404 and with correct token returned 200.
- Browser screenshot automation could not be completed in this environment; do a visual check on the user's Windows machine before presenting.

## Remaining limitations to disclose
- Role switcher and API role checks are a prototype simulation, not production identity/authentication. A real deployment needs login, secure sessions, user-to-role assignment and server-side ownership checks.
- ₹68L / ₹62L comparison is an illustrative scenario, not measured savings.
- Public locality match uses approximate centroids, not exact geocoded incident points. It is an exploratory alignment check, not predictive validation.
- Synthetic complaints / project records; no live BMC or NMMC connection.
- No verified utility network geometry or calibrated flood model.
- Outcome measures will be sparse until real verification and post-fix follow-up are recorded.

### Latest scoped update — Analytics page only
The Analytics page is now titled **Coordination & completion** and contains four sections: partner acknowledgements / waiting-on bottlenecks, completion funnel / overdue cases, conflict pipeline / illustrative avoided-rework amount, and outcomes / repeat complaints plus acknowledgement hours. Seeded examples are labelled illustrative. No other page was intentionally changed. Validation: Python compile, JavaScript syntax, 7 backend tests, and fresh-database analytics smoke checks passed.
