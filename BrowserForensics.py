import sqlite3
import csv
import os
import sys
import json
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


def decode_chromium_transition(transition):
    """
    Chromium transition is a bitmask:
      - low byte = core transition type
      - upper bits = qualifiers
    """
    if transition is None:
        return "", "", ""

    core_types = {
        0: "LINK",
        1: "TYPED",
        2: "AUTO_BOOKMARK",
        3: "AUTO_SUBFRAME",
        4: "MANUAL_SUBFRAME",
        5: "GENERATED",
        6: "START_PAGE",
        7: "FORM_SUBMIT",
        8: "RELOAD",
        9: "KEYWORD",
        10: "KEYWORD_GENERATED"
    }

    qualifiers = {
        0x00800000: "BLOCKED",
        0x01000000: "FORWARD_BACK",
        0x02000000: "FROM_ADDRESS_BAR",
        0x04000000: "HOME_PAGE",
        0x08000000: "FROM_API",
        0x10000000: "CHAIN_START",
        0x20000000: "CHAIN_END",
        0x40000000: "CLIENT_REDIRECT",
        0x80000000: "SERVER_REDIRECT"
    }

    core = transition & 0xFF
    core_name = core_types.get(core, f"Unknown({core})")

    qual_list = [name for bit, name in qualifiers.items() if transition & bit]
    qual_text = ", ".join(qual_list) if qual_list else ""

    return core, core_name, qual_text


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
    """Extract history & downloads from Chromium-based DB, including transition/chain context."""
    results = []

    # Browsing history
    try:
        query_history = """
        SELECT
            visits.id,
            urls.url,
            urls.title,
            urls.visit_count,
            urls.last_visit_time,
            visits.visit_time,
            visits.from_visit,
            visits.transition,
            visits.segment_id,
            visits.opener_visit
        FROM urls
        JOIN visits ON urls.id = visits.url
        ORDER BY visits.visit_time DESC;
        """

        for row in cursor.execute(query_history):
            (
                visit_id,
                url,
                title,
                visit_count,
                last_visit,
                visit_time,
                from_visit,
                transition,
                segment_id,
                opener_visit
            ) = row

            transition_core_raw, transition_core, transition_qualifiers = decode_chromium_transition(transition)

            results.append({
                "Type": "Visit",
                "Visit ID": visit_id,
                "URL": url,
                "Title": title,
                "Visit Count": visit_count,
                "Last Visit Raw": last_visit,
                "Visit Time Raw": visit_time,
                "Last Visit (UTC)": chrome_time_to_datetime(last_visit),
                "Visit Time (UTC)": chrome_time_to_datetime(visit_time),
                "Visit Type": transition_core,
                "Visit Type Raw": transition_core_raw,
                "Transition Core": transition_core,
                "Transition Qualifiers": transition_qualifiers,
                "Transition Raw": transition,
                "From Visit ID": from_visit,
                "Segment ID": segment_id,
                "Opener Visit ID": opener_visit,
                "Download Path": "",
                "Download Size (bytes)": "",
                "Referrer": ""
            })
    except sqlite3.Error as e:
        print(f"[!] Chromium history query failed: {e}")

    # Downloads
    try:
        query_downloads = """
        SELECT current_path, target_path, start_time, total_bytes, tab_url, tab_referrer_url
        FROM downloads;
        """
        for current_path, target_path, start_time, total_bytes, tab_url, tab_referrer_url in cursor.execute(query_downloads):
            results.append({
                "Type": "Download",
                "Visit ID": "",
                "URL": tab_url,
                "Title": "",
                "Visit Count": "",
                "Last Visit Raw": "",
                "Visit Time Raw": start_time,
                "Last Visit (UTC)": "",
                "Visit Time (UTC)": chrome_time_to_datetime(start_time),
                "Visit Type": "",
                "Visit Type Raw": "",
                "Transition Core": "",
                "Transition Qualifiers": "",
                "Transition Raw": "",
                "From Visit ID": "",
                "Segment ID": "",
                "Opener Visit ID": "",
                "Download Path": target_path or current_path,
                "Download Size (bytes)": total_bytes,
                "Referrer": tab_referrer_url
            })
    except sqlite3.Error as e:
        print(f"[!] Chromium downloads query failed: {e}")

    return results


def parse_firefox(cursor):
    """Extract history & downloads from Firefox DB (old & modern)."""
    results = []

    # Browsing history
    try:
        query_history = """
        SELECT
            moz_places.url,
            moz_places.title,
            moz_places.visit_count,
            moz_places.last_visit_date,
            moz_historyvisits.visit_date,
            moz_historyvisits.visit_type
        FROM moz_places
        JOIN moz_historyvisits ON moz_places.id = moz_historyvisits.place_id
        ORDER BY moz_historyvisits.visit_date DESC;
        """
        for url, title, visit_count, last_visit, visit_time, visit_type in cursor.execute(query_history):
            results.append({
                "Type": "Visit",
                "Visit ID": "",
                "URL": url,
                "Title": title,
                "Visit Count": visit_count,
                "Last Visit Raw": last_visit,
                "Visit Time Raw": visit_time,
                "Last Visit (UTC)": firefox_time_to_datetime(last_visit),
                "Visit Time (UTC)": firefox_time_to_datetime(visit_time),
                "Visit Type": visit_type,
                "Visit Type Raw": visit_type,
                "Transition Core": "",
                "Transition Qualifiers": "",
                "Transition Raw": "",
                "From Visit ID": "",
                "Segment ID": "",
                "Opener Visit ID": "",
                "Download Path": "",
                "Download Size (bytes)": "",
                "Referrer": ""
            })
    except sqlite3.Error as e:
        print(f"[!] Firefox history query failed: {e}")

    # Old Firefox downloads table
    try:
        cursor.execute("SELECT target, startTime, totalBytes, source FROM moz_downloads;")
        for target, start_time, total_bytes, source in cursor.fetchall():
            results.append({
                "Type": "Download",
                "Visit ID": "",
                "URL": source,
                "Title": "",
                "Visit Count": "",
                "Last Visit Raw": "",
                "Visit Time Raw": start_time,
                "Last Visit (UTC)": "",
                "Visit Time (UTC)": firefox_time_to_datetime(start_time),
                "Visit Type": "",
                "Visit Type Raw": "",
                "Transition Core": "",
                "Transition Qualifiers": "",
                "Transition Raw": "",
                "From Visit ID": "",
                "Segment ID": "",
                "Opener Visit ID": "",
                "Download Path": target,
                "Download Size (bytes)": total_bytes,
                "Referrer": ""
            })
    except sqlite3.Error:
        pass

    # Modern Firefox downloads in moz_annos
    try:
        query_downloads_modern = """
        SELECT
            p.url AS source_url,
            d_file.content AS target_path,
            d_meta.content AS meta_json
        FROM moz_places p
        JOIN moz_annos d_file ON p.id = d_file.place_id
        JOIN moz_anno_attributes a_file ON d_file.anno_attribute_id = a_file.id
        LEFT JOIN moz_annos d_meta ON p.id = d_meta.place_id
        LEFT JOIN moz_anno_attributes a_meta ON d_meta.anno_attribute_id = a_meta.id
        WHERE a_file.name = 'downloads/destinationFileURI'
          AND a_meta.name = 'downloads/metaData';
        """
        for source_url, target_path, meta_json in cursor.execute(query_downloads_modern):
            total_bytes = ""
            start_time = ""
            if meta_json:
                try:
                    meta = json.loads(meta_json)
                    total_bytes = meta.get("fileSize", "")
                    start_time = meta.get("startTime", 0)
                except Exception:
                    pass

            results.append({
                "Type": "Download",
                "Visit ID": "",
                "URL": source_url,
                "Title": "",
                "Visit Count": "",
                "Last Visit Raw": "",
                "Visit Time Raw": start_time if start_time else "",
                "Last Visit (UTC)": "",
                "Visit Time (UTC)": firefox_time_to_datetime(start_time) if start_time else "",
                "Visit Type": "",
                "Visit Type Raw": "",
                "Transition Core": "",
                "Transition Qualifiers": "",
                "Transition Raw": "",
                "From Visit ID": "",
                "Segment ID": "",
                "Opener Visit ID": "",
                "Download Path": target_path.replace("file://", "") if target_path else "",
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

    temp_db = "temp_history.db"
    with open(db_path, "rb") as src, open(temp_db, "wb") as dst:
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

    if results:
        results.sort(
            key=lambda x: x["Visit Time Raw"] if x["Visit Time Raw"] not in ("", None) else 0,
            reverse=True
        )

        fieldnames = [
            "Type",
            "Visit ID",
            "URL",
            "Title",
            "Visit Count",
            "Last Visit Raw",
            "Visit Time Raw",
            "Last Visit (UTC)",
            "Visit Time (UTC)",
            "Visit Type",
            "Visit Type Raw",
            "Transition Core",
            "Transition Qualifiers",
            "Transition Raw",
            "From Visit ID",
            "Segment ID",
            "Opener Visit ID",
            "Download Path",
            "Download Size (bytes)",
            "Referrer"
        ]

        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
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
