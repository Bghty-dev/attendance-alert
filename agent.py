import os
import pandas as pd
from core import analyze, at_risk, email_body, send_email, place_call

ATT = os.getenv("ATT_URL", "data/attendance.csv")      # can be a Google Sheet "publish to web" CSV link
MARKS = os.getenv("MARKS_URL", "data/marks.csv")
SLOTS = os.getenv("SLOTS_URL", "data/slots.csv")
STATE = "data/notified.csv"
DEMO_EMAIL = os.getenv("DEMO_EMAIL")   # redirects every email to you (safe demo)
DEMO_PHONE = os.getenv("DEMO_PHONE")   # redirects every call to you


def write_email(r):
    base = email_body(r)
    if not os.getenv("ANTHROPIC_API_KEY"):
        return base
    import anthropic
    c = anthropic.Anthropic()
    msg = c.messages.create(
        model="claude-sonnet-5-5", max_tokens=500,
        messages=[{"role": "user", "content":
                   "You are the academic office of a college. Rewrite this as a warm, supportive, "
                   "concise email. Keep every number exactly as given. Do not invent facts. "
                   "Output the email body only.\n\n" + base}])
    return msg.content[0].text


def main():
    df = analyze(pd.read_csv(ATT), pd.read_csv(MARKS), pd.read_csv(SLOTS))
    risk = at_risk(df)
    try:
        done = set(pd.read_csv(STATE).key)
    except Exception:
        done = set()
    log = []
    for _, r in risk.iterrows():
        key = f"{r.student_id}|{r.subject}|{r.att_status}|{bool(r.marks_flag)}"
        if key in done:
            continue
        to = DEMO_EMAIL or r.email
        cc = [] if DEMO_EMAIL else [r.teacher_email, r.advisor_email]
        log.append(send_email(to, cc, f"Attendance alert: {r.subject} at {r.pct:.0%}", write_email(r)))
        if r.att_status == "BELOW":
            log.append(place_call(DEMO_PHONE or r.phone, r["name"], r.subject, r.pct, r.needed))
        done.add(key)
    pd.DataFrame({"key": sorted(done)}).to_csv(STATE, index=False)
    print("\n".join(log) or "No new alerts.")


main()