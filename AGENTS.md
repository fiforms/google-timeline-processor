# AGENTS.md

## Purpose

This repository processes exported Google Maps Timeline JSON into spreadsheet-friendly mileage reports.

Main entry points:

- `timeline_mileage_report.py`: CLI and core parsing/report logic
- `timeline_mileage_wizard.py`: Tkinter desktop wizard that calls the shared report logic
- `classification.example.json`: sample keyword config for business/personal categorization

## Working Rules

- Keep the CLI and GUI on the same core code path. New report logic should go into `timeline_mileage_report.py` and be reused by the wizard.
- Preserve support for both common Google export shapes:
  - older `timelineObjects`
  - newer `semanticSegments`
- Expect Google exports to be inconsistent. Prefer tolerant parsing and graceful fallbacks over strict schema assumptions.
- If place names or addresses are missing, fall back to coordinates rather than leaving reports unusable.
- Do not introduce a network dependency unless explicitly requested. The current tool works fully offline after the user exports JSON from their phone.

## Testing

Before finishing changes, run:

```bash
python3 -m py_compile timeline_mileage_report.py timeline_mileage_wizard.py
python3 timeline_mileage_report.py sample_timeline.json --output-dir sample_output
```

Then inspect:

- `sample_output/trip_details.csv`
- `sample_output/visit_details.csv`
- `sample_output/daily_summary.csv`

If Tkinter is available in the active Python, also run:

```bash
python3 timeline_mileage_wizard.py
```

If Tkinter is missing, note that clearly instead of treating it as a code failure.

## Repository Hygiene

- Do not commit generated output from `output/` or `sample_output/`.
- Do not commit `__pycache__`, editor swap files, or LibreOffice lock files.
- Keep this project dependency-light. Prefer the standard library unless there is a strong reason otherwise.
- Update `README.md` when changing user workflow, export instructions, or launch commands.

## Common Improvements

- Better classification heuristics for business vs personal destinations
- Improved handling of new Google export formats
- Optional XLSX export
- Better destination labeling for coordinate-only segments

## Cautions

- Mileage output may be used for reimbursement or tax records, so avoid silent failures and surface parsing problems clearly.
- Do not claim browser Timeline access exists. Current supported workflow is exporting Timeline data from the phone and processing it locally.
