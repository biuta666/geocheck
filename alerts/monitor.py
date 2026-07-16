"""GEO Alert System v2 - Gatus-inspired state machine.

Rules:
  - Score drop > 10% over 3 days  →  High alert after 2 consecutive checks
  - Score drop > 5%  →  Medium alert after 3 consecutive checks  
  - Citation loss  →  Medium alert
  - New competitor detected  →  Medium alert
  - Recovery detected  →  Info alert
"""
import os, sys, json, datetime, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import get_conn

ALERT_STATES = {}  # In-memory state machine: {brand_key: {fail_count, success_count, last_state}}


def _state_key(brand_name: str, rule_type: str) -> str:
    return hashlib.md5(f"{brand_name}:{rule_type}".encode()).hexdigest()[:16]


def _get_state(brand_name: str, rule_type: str):
    key = _state_key(brand_name, rule_type)
    if key not in ALERT_STATES:
        ALERT_STATES[key] = {"fail_count": 0, "success_count": 0, "last_state": "ok", "last_alert": None}
    return ALERT_STATES[key]


def check_alerts(brand_name: str) -> list:
    """Check all alert rules using state machine pattern."""
    conn = get_conn()
    bid = conn.execute("SELECT id FROM brands WHERE name=?", (brand_name,)).fetchone()
    if not bid:
        conn.close()
        return []
    bid = bid["id"]

    alerts = []

    # ── Rule 1: Score drop ──────────────────────────────
    recent = conn.execute("""
        SELECT date(v.created_at) as day, ROUND(AVG(v.score),1) as avg_score
        FROM visibility_results v JOIN responses r ON v.response_id = r.id
        JOIN queries q ON r.query_id = q.id
        WHERE q.brand_id=? AND v.created_at > datetime('now', '-3 days')
        GROUP BY day ORDER BY day
    """, (bid,)).fetchall()
    previous = conn.execute("""
        SELECT ROUND(AVG(v.score),1) as avg_score
        FROM visibility_results v JOIN responses r ON v.response_id = r.id
        JOIN queries q ON r.query_id = q.id
        WHERE q.brand_id=? AND v.created_at BETWEEN datetime('now', '-7 days') AND datetime('now', '-3 days')
    """, (bid,)).fetchone()
    conn.close()

    # Compute citation change
    citation_change = _get_citation_change(bid)

    if len(recent) >= 2 and previous and previous["avg_score"]:
        current = recent[-1]["avg_score"] or 0
        prev = previous["avg_score"] or 0

        if prev > 0:
            drop_pct = round((prev - current) / prev * 100, 1)
            state = _get_state(brand_name, "score_drop")

            if drop_pct > 10:
                state["fail_count"] += 1
                state["success_count"] = 0
                # Gatus-style: alert after failure_threshold consecutive failures
                if state["fail_count"] >= 2 and state["last_state"] != "alerting":
                    state["last_state"] = "alerting"
                    alerts.append({
                        "type": "score_drop",
                        "severity": "high",
                        "title": f"Score Dropped {drop_pct}% (Alert #{state['fail_count']})",
                        "detail": f"GEO Score dropped from {prev} to {current}. Threshold: 10%.",
                        "threshold": 10, "actual": drop_pct,
                        "engine": "gatus-state-machine",
                    })
            elif drop_pct > 5:
                state["fail_count"] += 1
                state["success_count"] = 0
                if state["fail_count"] >= 3 and state["last_state"] != "alerting":
                    state["last_state"] = "alerting"
                    alerts.append({
                        "type": "score_drop",
                        "severity": "medium",
                        "title": f"Score Dropped {drop_pct}%",
                        "detail": f"GEO Score dropped from {prev} to {current}.",
                        "threshold": 5, "actual": drop_pct,
                        "engine": "gatus-state-machine",
                    })
            else:
                # Recovery: increment success counter
                state["success_count"] += 1
                if state["last_state"] == "alerting" and state["success_count"] >= 2:
                    state["last_state"] = "recovered"
                    alerts.append({
                        "type": "score_recovery",
                        "severity": "info",
                        "title": "Score Recovered",
                        "detail": f"Score stabilized at {current}. Previous alert cleared.",
                        "engine": "gatus-state-machine",
                    })
                elif state["last_state"] == "alerting":
                    state["fail_count"] = max(0, state["fail_count"] - 1)

            # Reset if stable for too long
            if state["last_state"] == "recovered" and state["success_count"] >= 5:
                state["last_state"] = "ok"
                state["fail_count"] = 0
                state["success_count"] = 0

    # ── Rule 2: Citation change ────────────────────────
    if citation_change.get("lost", 0) > 0:
        alerts.append({
            "type": "citation_loss",
            "severity": "medium",
            "title": f"Citations Decreased by {citation_change['lost']}",
            "detail": f"{citation_change['lost']} citation sources no longer reference this brand.",
            "engine": "gatus-state-machine",
        })

    if not alerts:
        alerts.append({
            "type": "no_alert",
            "severity": "info",
            "title": "All Systems Normal",
            "detail": f"Current score: {recent[-1]['avg_score'] if recent else 'N/A'}. No significant changes detected.",
            "engine": "gatus-state-machine",
        })

    return alerts


def _get_citation_change(brand_id: int, days: int = 14) -> dict:
    """Check if citation count has changed significantly."""
    conn = get_conn()
    recent = conn.execute("""
        SELECT COUNT(DISTINCT domain) as count FROM citations c
        JOIN responses r ON c.response_id = r.id
        JOIN queries q ON r.query_id = q.id
        WHERE q.brand_id=? AND c.created_at > datetime('now', '-3 days')
    """, (brand_id,)).fetchone()
    previous = conn.execute("""
        SELECT COUNT(DISTINCT domain) as count FROM citations c
        JOIN responses r ON c.response_id = r.id
        JOIN queries q ON r.query_id = q.id
        WHERE q.brand_id=? AND c.created_at BETWEEN datetime('now', '-7 days') AND datetime('now', '-3 days')
    """, (brand_id,)).fetchone()
    conn.close()
    rc = recent["count"] if recent else 0
    pc = previous["count"] if previous else 0
    return {"lost": max(0, pc - rc), "gained": max(0, rc - pc), "current": rc, "previous": pc}


def format_alert_email(brand_name: str, alerts: list) -> str:
    """Format alerts as HTML email with Gatus-inspired status layout."""
    alert_items = ""
    for a in alerts:
        colors = {"high": "#f87171", "medium": "#fbbf24", "info": "#60a5fa"}
        icons = {"high": "CRITICAL", "medium": "WARNING", "info": "INFO"}
        alert_items += f"""
        <div style="border-left:3px solid {colors.get(a['severity'],'#888')};padding:12px;margin:10px 0;background:rgba(255,255,255,0.03);border-radius:8px">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <strong>{a['title']}</strong>
            <span style="font-size:0.7rem;color:{colors.get(a['severity'],'#888')};font-weight:600">{icons.get(a['severity'],'INFO')}</span>
          </div>
          <p style="color:#8892a4;font-size:0.85rem;margin:0">{a['detail']}</p>
        </div>"""

    return f"""<!DOCTYPE html>
<html><body style="background:#0b1121;color:#e8edf5;font-family:sans-serif;padding:30px">
<div style="max-width:600px;margin:0 auto">
<div style="text-align:center;padding:20px 0;border-bottom:1px solid rgba(255,255,255,0.08)">
<div style="font-size:0.7rem;background:rgba(124,58,237,0.12);color:#a78bfa;padding:2px 12px;border-radius:20px;display:inline-block;margin-bottom:8px">GEOCheck ALERT</div>
<h1 style="font-size:1.2rem;color:#e8edf5">{brand_name}</h1>
<p style="color:#8892a4;font-size:0.85rem">{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</div>
{alert_items}
<div style="border-top:1px solid rgba(255,255,255,0.08);padding:16px 0;text-align:center;color:#5a6474;font-size:0.8rem;margin-top:20px">
Powered by GEOCheck v2 Alert Engine &middot; Gatus-inspired state machine
</div>
</div></body></html>"""


def get_alert_config(project_id: int) -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM alerts WHERE project_id=?", (project_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_alert_config(project_id: int, alert_type: str = "score_change",
                     threshold: float = 10.0, email: str = ""):
    conn = get_conn()
    existing = conn.execute("SELECT id FROM alerts WHERE project_id=? AND alert_type=?",
                            (project_id, alert_type)).fetchone()
    if existing:
        conn.execute("UPDATE alerts SET threshold=?, notification_email=?, enabled=1 WHERE id=?",
                     (threshold, email, existing["id"]))
    else:
        conn.execute("INSERT INTO alerts (project_id, alert_type, threshold, notification_email) VALUES (?,?,?,?)",
                     (project_id, alert_type, threshold, email))
    conn.commit()
    conn.close()
