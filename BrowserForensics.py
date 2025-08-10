import sqlite3
import csv
import os
import sys
from datetime import datetime

# Chrome/Edge/Brave timestamp offset (microseconds since 1601-01-01 UTC)
BROWSER_TIME_OFFSET_MICROSECONDS = 11644473600000000
# Firefox timestamp offset (microseconds since Unix epoch 1970-01-01 UTC)
FIREFOX_TIME_DIVISOR = 1_000_000

def chrome_time_to_datetime(chrome_time):
    """Convert Chrome timestamp to formatted UTC datetime."""
    if chrome_time:
        try:
            dt = datetime.utcfromtimestamp(
                (chrome_time - BROWSER_TIME_OFFSET_MICROSECONDS) / 1_000_000
            )
            return dt.strftime("%-m/%-d/%Y  %-I:%M:%S %p UTC") if os.name != "nt" else dt.strftime("%#m/%#d/%Y  %#I:%M:%S %p UTC")
        except Exception:
            return None
    return None

def firefox_time_to_datetime(firefox_time):
    """Convert Firefox timestamp (microseconds since Unix epoch) to formatted UTC datetime."""
    if firefox_time:
        try:
            dt = datetime.utcfromtimestamp(firefox_time / FIREFOX_TIME_DIVISOR)
            return dt.strftime("%-m/%-d/%Y  %-I:%M:%S %p UTC") if os.name != "nt" else dt.strftime("%#m/%#d/%Y  %#I:%M:%S %p UTC")
        except Exception:
            return None
    return None

def detect_browser(cursor):
    """Detect DB type based on known tables."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}

    if {"urls", "visits"}.issubset(tables):
        return "chromium"
    elif {"moz_places", "moz_historyvisits"}.issubset(tables):
        return "firefox"
    else:
        return None

def parse_chromium(cursor):
    """Extract history & downloads from Chromium-based DB."""
    results = []

    # Browsing history
    try:
        query_history = """
        SELECT urls.url, urls.title, urls.visit_count, urls.last_visit_time, visits.visit_time
        FROM urls, visits
        WHERE urls.id = visits.url
        ORDER BY visits.visit_time DESC;
        """
        for url, title, visit_count, last_visit, visit_time in cursor.execute(query_history):
            results.append({
                "Type": "Visit",
                "URL": url,
                "Title": title,
                "Visit Count": visit_count,
                "Last Visit (UTC)": chrome_time_to_datetime(last_visit),
                "Visit Time (UTC)": chrome_time_to_datetime(visit_time),
                "Download Path": "",
                "Download Size (bytes)": "",
                "Referrer": ""
            })
    except sqlite3.Error:
        pass

    # Downloads
    try:
        query_downloads = """
        SELECT current_path, target_path, start_time, total_bytes, tab_url, tab_referrer_url
        FROM downloads;
        """
        for current_path, target_path, start_time, total_bytes, tab_url, tab_referrer_url in cursor.execute(query_downloads):
            results.append({
                "Type": "Download",
                "URL": tab_url,
                "Title": "",
                "Visit Count": "",
                "Last Visit (UTC)": "",
                "Visit Time (UTC)": chrome_time_to_datetime(start_time),
                "Download Path": target_path or current_path,
                "Download Size (bytes)": total_bytes,
                "Referrer": tab_referrer_url
            })
    except sqlite3.Error:
        pass

    return results

def parse_firefox(cursor):
    """Extract history & downloads from Firefox DB."""
    results = []

    # Browsing history
    try:
        query_history = """
        SELECT moz_places.url, moz_places.title, moz_places.visit_count, moz_places.last_visit_date, moz_historyvisits.visit_date
        FROM moz_places
        JOIN moz_historyvisits ON moz_places.id = moz_historyvisits.place_id
        ORDER BY moz_historyvisits.visit_date DESC;
        """
        for url, title, visit_count, last_visit, visit_time in cursor.execute(query_history):
            results.append({
                "Type": "Visit",
                "URL": url,
                "Title": title,
                "Visit Count": visit_count,
                "Last Visit (UTC)": firefox_time_to_datetime(last_visit),
                "Visit Time (UTC)": firefox_time_to_datetime(visit_time),
                "Download Path": "",
                "Download Size (bytes)": "",
                "Referrer": ""
            })
    except sqlite3.Error:
        pass

    # Downloads
    try:
        query_downloads = """
        SELECT target, startTime, totalBytes, source
        FROM moz_downloads;
        """
        for target, start_time, total_bytes, source in cursor.execute(query_downloads):
            results.append({
                "Type": "Download",
                "URL": source,
                "Title": "",
                "Visit Count": "",
                "Last Visit (UTC)": "",
                "Visit Time (UTC)": firefox_time_to_datetime(start_time),
                "Download Path": target,
                "Download Size (bytes)": total_bytes,
                "Referrer": ""
            })
    except sqlite3.Error:
        pass

    return results

def export_history(db_path, output_csv):
    if not os.path.exists(db_path):
        print(f"[!] History database not found: {db_path}")
        return

    # Copy DB to avoid locks
    temp_db = "temp_history.db"
    with open(db_path, 'rb') as src, open(temp_db, 'wb') as dst:
        dst.write(src.read())

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    browser_type = detect_browser(cursor)
    if not browser_type:
        print("[!] Unknown or unsupported browser history database.")
        conn.close()
        os.remove(temp_db)
        return

    print(f"[+] Detected {browser_type.capitalize()} database.")
    results = parse_chromium(cursor) if browser_type == "chromium" else parse_firefox(cursor)

    conn.close()
    os.remove(temp_db)

    # Write to CSV
    if results:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"[+] Export complete: {output_csv}")
        print(f"[+] Records exported: {len(results)}")
    else:
        print("[!] No history or download data found.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python BrowserForensics.py <path_to_history_db> [output_csv]")
        sys.exit(1)

    history_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "browser_history_export.csv"
    export_history(history_path, output_file)
