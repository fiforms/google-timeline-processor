# Google Timeline Mileage Report

This project turns exported Google Maps Timeline JSON into CSV files you can open in Excel or Google Sheets:

- `daily_summary.csv`: one row per day with total miles, driving miles, destinations, and a suggested category
- `trip_details.csv`: one row per travel segment
- `visit_details.csv`: one row per place visit

## Install Python And Tkinter

The GUI requires Python 3 and Tkinter.

## Windows

1. Install Python 3 from <https://www.python.org/downloads/windows/>.
2. During installation, enable `Add python.exe to PATH`.
3. Tkinter is normally included with the standard Windows installer.
4. Verify:

```powershell
python --version
python -c "import tkinter; print(tkinter.TkVersion)"
```

## macOS

Recommended: install the official Python build from python.org, because it usually includes working Tk support.

1. Install Python 3 from <https://www.python.org/downloads/macos/>.
2. Verify:

```bash
python3 --version
python3 -c "import tkinter; print(tkinter.TkVersion)"
```

If you use Homebrew Python and Tkinter fails, install Tk and use a Python build linked against it:

```bash
brew install python-tk
python3 -c "import tkinter; print(tkinter.TkVersion)"
```

## Ubuntu Or Debian

```bash
sudo apt update
sudo apt install -y python3 python3-tk
python3 --version
python3 -c "import tkinter; print(tkinter.TkVersion)"
```

If your active Python comes from `pyenv`, `asdf`, or another custom build tool, you may need to rebuild Python after installing Tk development libraries:

```bash
sudo apt install -y tk-dev tcl-dev
pyenv uninstall 3.10.13
pyenv install 3.10.13
python3 -c "import tkinter; print(tkinter.TkVersion)"
```

## Fedora

```bash
sudo dnf install -y python3 python3-tkinter
python3 --version
python3 -c "import tkinter; print(tkinter.TkVersion)"
```

## Use The GUI

Start the wizard:

```bash
python3 timeline_mileage_wizard.py
```

On Windows, use:

```powershell
python timeline_mileage_wizard.py
```

The wizard walks through:

1. how to export Timeline data from your Android phone
2. choosing a Timeline JSON file or a folder of JSON files
3. choosing where to save the CSV reports
4. optionally choosing a classification config file
5. generating the report

When the report finishes, it writes:

- `daily_summary.csv`
- `trip_details.csv`
- `visit_details.csv`

## Important Google Maps Timeline change

Google moved Timeline off the browser and onto your device. The supported workflow is to export Timeline data from your phone, then process that export locally.

Official Google help:

- Android export steps: <https://support.google.com/maps/answer/6258979?co=GENIE.Platform%3DAndroid&hl=en>
- Timeline moved off the web: <https://support.google.com/maps/answer/14169818?co=GENIE.Platform%3DAndroid&hl=en-HR>

## How To Export Timeline Data From Android

1. On your Android phone, open `Settings`.
2. Go to `Location` -> `Location services` -> `Timeline`.
3. Tap `Export Timeline data`.
4. Save the exported JSON file somewhere accessible.
5. Move that JSON file to this computer.

If you still have an older Google Takeout export with `Location History (Timeline)` JSON files, this project can also read the common `timelineObjects` format.

## Classification Config

You can optionally provide a JSON file with keywords to help mark days as business or personal. A starter example is included in `classification.example.json`.

The keyword matching is intentionally simple:

- if a day's destinations match only business keywords, it is labeled `business`
- if they match only personal or home keywords, it is labeled `personal`
- otherwise it is labeled `review`

You should still review the CSV before using it for tax or reimbursement records.

## Notes

- Distance is taken from Google's segment data when available.
- If Google does not include a segment distance, the script estimates it from path coordinates.
- If Google does not include place names or addresses, the report falls back to coordinates.
- The safest workflow is to export Timeline from your phone at least once per month and archive the JSON.

## CLI Usage

Basic usage:

```bash
python3 timeline_mileage_report.py /path/to/location-history.json
```

You can also point it at a folder:

```bash
python3 timeline_mileage_report.py /path/to/folder/of/json/files
```

Specify output folder, timezone, and classification config:

```bash
python3 timeline_mileage_report.py /path/to/location-history.json \
  --output-dir output \
  --timezone America/New_York \
  --config classification.example.json
```

Show command help:

```bash
python3 timeline_mileage_report.py --help
```
