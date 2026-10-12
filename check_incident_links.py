import csv
import urllib.error
import urllib.request

CSV_FILE = "data/failure_scenarios.csv"

with open(CSV_FILE, newline="", encoding="utf-8-sig") as file:
    incidents = list(csv.DictReader(file))

print(f"Checking {len(incidents)} incident links...\n")

for incident in incidents:
    incident_id = incident["incident_id"]
    url = incident["source_url"].strip()

    if not url:
        print(f"{incident_id}: MISSING LINK")
        continue

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.status
            final_url = response.geturl()

            if 200 <= status < 400:
                print(f"{incident_id}: HTTP {status} - OPENED")
                if final_url != url:
                    print(f"  Redirected to: {final_url}")
            else:
                print(f"{incident_id}: HTTP {status} - CHECK")

    except urllib.error.HTTPError as error:
        print(f"{incident_id}: HTTP {error.code} - CHECK")
    except Exception as error:
        print(f"{incident_id}: COULD NOT VERIFY - {error}")
