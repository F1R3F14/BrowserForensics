# BrowserForensics Tool

## Overview
This is a lightweight tool for parsing browser history artifacts from:
- Google Chrome
- Microsoft Edge (Chromium)
- Mozilla Firefox

It extracts browsing data from SQLite databases and exports them into a **normalized CSV format (UTC timestamps)** for analysis.

---

## Features
- Supports Chrome, Edge, and Firefox history artifacts  
- Converts timestamps to **UTC for timeline consistency**  
- Outputs clean, analysis-ready CSV files  
- Simple CLI usage (script or compiled EXE)  

---

## Usage

Run the tool with a history file as input:

    python BrowserForensics.py <HISTORY_FILE> -o <OUTPUT.csv>

or using the compiled binary:

    BrowserForensics.exe <HISTORY_FILE> -o <OUTPUT.csv>

### Example

    BrowserForensics.exe History Edge -o combined.csv

> Note: You can process multiple history files at the same time

---

## Artifact Locations

### Google Chrome

    C:\Users\<USERNAME>\AppData\Local\Google\Chrome\User Data\Default\History

### Microsoft Edge (Chromium)

    C:\Users\<USERNAME>\AppData\Local\Microsoft\Edge\User Data\Default\History

### Mozilla Firefox

    C:\Users\<USERNAME>\AppData\Roaming\Mozilla\Firefox\Profiles\<PROFILE>\places.sqlite

---

## Browser Sync Analysis (IR Use Case)

This tool focuses on **local history artifacts**, but investigators should also determine whether **browser syncing is enabled**

## Sync Artifact Locations

### Google Chrome

    C:\Users\<USER>\AppData\Local\Google\Chrome\User Data\Default\Preferences

**Key Fields to Review:**
- `sync.has_setup_completed`
- `account_info.email`
- `synced_preferences.sync_disabled`

---

### Mozilla Firefox

    C:\Users\<USER>\AppData\Roaming\Mozilla\Firefox\Profiles\<PROFILE>\prefs.js

**Key Fields to Review:**
- `services.sync.username`
- `services.sync.engine.*`

---

### Microsoft Edge

    C:\Users\<USER>\AppData\Local\Microsoft\Edge\User Data\Default\Preferences

**Key Fields to Review:**
- `sync.has_setup_completed`
- `account_info.email`
- `synced_preferences.sync_disabled`

---

## Sync Status Interpretation

| Indicator | Meaning |
|----------|--------|
| `has_setup_completed = true` | Sync configured |
| `account_info present` | User signed in |
| `sync_disabled = true` | Sync blocked (often policy) |
| Sync data present | Active or previously active sync |

---

## Investigation Notes

- Sync enabled → Data may exist outside the endpoint  

- Correlate with:
  - Login artifacts  
  - Token/session activity  
  - Other endpoints tied to the same account  

---

## Roadmap
- Multi-browser ingestion (single command)   

---
