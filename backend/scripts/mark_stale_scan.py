import sqlite3
from datetime import datetime, timezone

DB = "scanner.db"
SCAN_ID = 3

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("SELECT id, status FROM scans WHERE id=?", (SCAN_ID,))
row = cur.fetchone()
if not row:
    print("Scan not found:", SCAN_ID)
    raise SystemExit(0)

now = datetime.now(timezone.utc).isoformat(timespec="seconds")

cur.execute(
    "UPDATE scans SET status=?, error=?, finished_at=? WHERE id=?",
    ("failed", "stale queued scan (created before background tasks)", now, SCAN_ID),
)

con.commit()
con.close()
print(f"OK: scan {SCAN_ID} marked as failed")