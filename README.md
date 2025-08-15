# BrowserForensics Tool

## Description
This tool parses browser history SQLite files (Chrome, Edge, Firefox) and exports them to CSV files with timestamps in UTC.

---

## Usage

Run the script with one browser history files as arguments:

```bash
python BrowserForensics.py NAME_OF_HISTORY_FILE OUTPUT_NAME.csv

OR

BrowserForensics.exe NAME_OF_HISTORY_FILE OUTPUT_NAME.csv
```

Currently working to have this take numerous browsers all in one.

## Chrome History Location

```bash
C:\Users\<USERNAME>\AppData\Local\Google\Chrome\User Data\Default\History
```

## Edge History Location

```bash
C:\Users\<USERNAME>\AppData\Local\Microsoft\Edge\User Data\Default\History
```

## FireFox History Location

```bash
C:\Users\<USERNAME>\AppData\Roaming\Mozilla\Firefox\Profiles\<RANDOM>.default-release\places.sqlite
```
