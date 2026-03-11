# Google Timeline Mileage Report

This script turns exported Google Timeline JSON into CSV files you can open in Excel or Google Sheets:

- `daily_summary.csv`: one row per day with total miles, driving miles, destinations, and a suggested category
- `trip_details.csv`: one row per travel segment
- `visit_details.csv`: one row per place visit

## Important Google Maps Timeline change

As of Google's Timeline migration, Timeline for web browsers is going away and Timeline data now lives on your device. The supported export path is from your phone.

Official Google help:

- Android export steps: <https://support.google.com/maps/answer/6258979?co=GENIE.Platform%3DAndroid&hl=en>
- Timeline moved off the web: <https://support.google.com/maps/answer/14169818?co=GENIE.Platform%3DAndroid&hl=en-HR>

## How to get your Timeline data from Android

1. On your Android phone, open `Settings`.
2. Go to `Location` -> `Location services` -> `Timeline`.
3. Tap `Export Timeline data`.
4. Save the exported JSON file somewhere accessible.
5. Move that JSON file to this computer.

If you still have an older Google Takeout export with `Location History (Timeline)` JSON files, this script can also read the common `timelineObjects` format.

## Run it

```bash
python3 timeline_mileage_report.py /path/to/location-history.json
```

You can also point it at a folder:

```bash
python3 timeline_mileage_report.py /path/to/folder/of/json/files
```

The script writes CSVs into `output/` by default.

## Desktop wizard

If you want a click-through desktop app instead of the command line:

```bash
python3 timeline_mileage_wizard.py
```

The wizard walks through:

1. how to export Timeline from Android
2. choosing the JSON file or folder
3. choosing where to save the CSVs
4. optionally picking a classification config
5. generating the report

## Use a classification config

You can give the script a simple JSON file with keywords to help mark days as business or personal:

```bash
python3 timeline_mileage_report.py /path/to/location-history.json \
  --config classification.example.json \
  --timezone America/New_York
```

The keyword matching is intentionally simple:

- if a day's destinations match only business keywords, it is labeled `business`
- if they match only personal or home keywords, it is labeled `personal`
- otherwise it is labeled `review`

You should still review the CSV before using it for tax or reimbursement records.

## Notes

- Distance is taken from Google's segment data when available.
- If Google does not include a segment distance, the script estimates it from path coordinates.
- The safest workflow is to export Timeline from your phone at least once per month and archive the JSON.
