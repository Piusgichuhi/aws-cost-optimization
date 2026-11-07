from scanners import find_orphaned_volumes, find_unattached_eips, find_idle_instances
from exemptions import is_exempt
from tracker import track_first_seen, past_grace, mark_deleted, clear_resolved
from cleaner import clean_resource
from reporter import build_report, send_report
from config import DRY_RUN

def lambda_handler(event, context):
    findings = (find_orphaned_volumes() + find_unattached_eips()
                + find_idle_instances())
    flagged, to_clean, exempt = [], [], []

    for r in findings:
        if is_exempt(r):
            exempt.append(r)
            continue
        item = track_first_seen(r)
        (to_clean if past_grace(item) else flagged).append(r)

    deleted = []
    for r in to_clean:
        clean_resource(r)
        if not DRY_RUN:
            mark_deleted(r["id"])
        deleted.append(r)

    clear_resolved({r["id"] for r in findings})
    send_report(build_report(flagged + (deleted if DRY_RUN else []), 
                             [] if DRY_RUN else deleted, exempt))
    return {"found": len(findings), "flagged": len(flagged),
            "cleaned": len(deleted), "exempt": len(exempt)}