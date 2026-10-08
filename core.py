import math, os, smtplib, random
from email.message import EmailMessage
import pandas as pd
import requests

THRESH = 0.85


def analyze(att, marks, slots=None):
    df = att.merge(marks, on=["student_id", "subject"], how="left")
    df["pct"] = (df.attended / df.held).round(4)
    df["needed"] = df.apply(
        lambda r: 0 if r.pct >= THRESH
        else math.ceil(round((THRESH * r.held - r.attended) / (1 - THRESH), 6)), axis=1)
    df["att_status"] = df.pct.apply(lambda p: "BELOW" if p < THRESH else "CLOSE" if p < 0.90 else "OK")
    df["marks_flag"] = df.apply(
        lambda r: "WEAK/FALLING" if (r.latest_test < 50 or r.latest_test - r.prev_test <= -10) else "", axis=1)
    df["risk"] = (df.att_status.map({"BELOW": 50, "CLOSE": 25, "OK": 0})
                  + (df.marks_flag != "") * 30 + df.needed.clip(upper=20))
    df = df.sort_values("risk", ascending=False).reset_index(drop=True)
    if slots is not None:
        free = slots.groupby("teacher_email").slot.apply(lambda s: ", ".join(s.head(3))).to_dict()
        df["free_slots"] = df.teacher_email.map(free).fillna("none listed")
    return df


def at_risk(df):
    return df[df.risk > 0]


def email_body(r):
    msg = (f"Hi {r['name']},\n\nYour attendance in {r.subject} is {r.pct:.0%}, "
           f"against the required 85%.\n")
    if r.needed > 0:
        msg += f"You must attend {r.needed} classes IN A ROW to get back to 85%.\n"
    else:
        msg += "You are close to the limit. Please do not miss more classes.\n"
    if r.marks_flag:
        msg += f"Your recent marks are weak or falling ({r.prev_test:.0f} -> {r.latest_test:.0f}).\n"
    msg += f"\nBook time with your teacher. Free slots: {r.get('free_slots', 'n/a')}\n"
    msg += "Your teacher and faculty adviser have been notified.\n"
    return msg


def send_email(to, cc, subject, body):
    user, pwd = os.getenv("SMTP_USER"), os.getenv("SMTP_PASS")
    if not user:
        return f"[DRY-RUN] To:{to} CC:{cc} | {subject}"
    m = EmailMessage()
    m["From"], m["To"], m["Cc"], m["Subject"] = user, to, ", ".join(cc), subject
    m.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pwd)
        s.send_message(m)
    return f"[SENT] {to}"


def place_call(phone, name, subject, pct, needed):
    key = os.getenv("VAPI_KEY")
    if not key:
        return f"[DRY-RUN CALL] {phone}: {name}, {subject} at {pct:.0%}, needs {needed} in a row"
    r = requests.post(
        "https://api.vapi.ai/call",
        headers={"Authorization": f"Bearer {key}"},
        json={"assistantId": os.getenv("VAPI_ASSISTANT_ID"),
              "phoneNumberId": os.getenv("VAPI_PHONE_ID"),
              "customer": {"number": phone},
              "assistantOverrides": {"variableValues": {
                  "name": name, "subject": subject,
                  "percent": f"{pct:.0%}", "needed": str(needed)}}})
    return f"[CALL {r.status_code}] {phone}"


def weekly_text(df):
    top = at_risk(df).head(15)
    lines = [f"- {r['name']} | {r.dept} | {r.subject} | {r.pct:.0%} | needs {r.needed} | risk {r.risk:.0f}"
             for _, r in top.iterrows()]
    by_dept = at_risk(df).groupby("dept").size().to_string()
    return "Weekly at-risk summary\n\nTop students:\n" + "\n".join(lines) + f"\n\nBy department:\n{by_dept}\n"


def sample():
    random.seed(7)
    depts = {"CSE": ["DSA", "DBMS"], "ECE": ["Signals", "VLSI"]}
    att, marks, slots = [], [], []
    n = 0
    for d, subs in depts.items():
        t = f"teacher_{d.lower()}@example.com"
        for day in ["Mon 11:00", "Tue 14:00", "Thu 10:00"]:
            slots.append({"teacher_email": t, "slot": day})
        for i in range(8):
            n += 1
            for s in subs:
                held = random.randint(30, 40)
                att.append({"student_id": n, "name": f"Student{n}", "email": f"student{n}@example.com",
                            "phone": f"+9199000000{n:02d}", "dept": d, "subject": s,
                            "teacher_email": t, "advisor_email": f"advisor_{d.lower()}@example.com",
                            "held": held, "attended": int(held * random.uniform(0.62, 1.0))})
                p = random.randint(40, 90)
                marks.append({"student_id": n, "subject": s, "prev_test": p,
                              "latest_test": max(10, p + random.randint(-25, 10))})
    return pd.DataFrame(att), pd.DataFrame(marks), pd.DataFrame(slots)