import pandas as pd
import streamlit as st
from core import *

st.set_page_config(page_title="Attendance Early Warning", layout="wide")
st.title("🎓 Attendance & Marks Early-Warning System")

with st.sidebar:
    st.header("Upload")
    fa = st.file_uploader("Attendance CSV", type="csv")
    fm = st.file_uploader("Test results CSV", type="csv")
    ft = st.file_uploader("Teacher free slots CSV", type="csv")
    use_sample = st.checkbox("Use sample data", value=not (fa and fm))

if use_sample or not (fa and fm):
    att, marks, slots = sample()
else:
    att, marks = pd.read_csv(fa), pd.read_csv(fm)
    slots = pd.read_csv(ft) if ft else pd.DataFrame(columns=["teacher_email", "slot"])

df = analyze(att, marks, slots)
risk = at_risk(df)

c1, c2, c3 = st.columns(3)
c1.metric("Records", len(df))
c2.metric("Below 85%", int((df.att_status == "BELOW").sum()))
c3.metric("Weak/falling marks", int((df.marks_flag != "").sum()))

tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Send alerts", "Book appointment", "Weekly summary"])

with tab1:
    a, b = st.columns(2)
    a.subheader("Department-wise risk")
    a.bar_chart(risk.groupby("dept").size())
    b.subheader("Subject-wise risk")
    b.bar_chart(risk.groupby("subject").size())
    st.subheader("Most at-risk first")
    st.dataframe(risk[["name", "dept", "subject", "pct", "needed", "att_status",
                       "marks_flag", "risk"]], use_container_width=True)

with tab2:
    st.write("Emails go to the student, with the subject teacher and adviser on CC. "
             "Students below 85% also get an automatic call. Dry-run unless credentials are set.")
    if st.button("🚨 Send all alerts now"):
        log = []
        for _, r in risk.iterrows():
            log.append(send_email(r.email, [r.teacher_email, r.advisor_email],
                                  f"Attendance alert: {r.subject} at {r.pct:.0%}", email_body(r)))
            if r.att_status == "BELOW":
                log.append(place_call(r.phone, r["name"], r.subject, r.pct, r.needed))
        st.code("\n".join(log))
    if len(risk):
        st.subheader("Sample email preview")
        st.text(email_body(risk.iloc[0]))

with tab3:
    st.write("At-risk student picks a free slot from the teacher's timetable.")
    if len(risk):
        who = st.selectbox("Student", risk["name"].unique())
        row = risk[risk["name"] == who].iloc[0]
        opts = slots[slots.teacher_email == row.teacher_email].slot.tolist()
        slot = st.selectbox("Free slot", opts or ["none"])
        if st.button("Book"):
            st.success(f"Booked {who} with {row.teacher_email} at {slot}")
            st.code(send_email(row.teacher_email, [row.email], f"Appointment: {who} @ {slot}",
                               f"{who} booked {slot}."))

with tab4:
    txt = weekly_text(df)
    st.text(txt)
    if st.button("Send weekly summary to advisers"):
        for adv in df.advisor_email.unique():
            st.code(send_email(adv, [], "Weekly at-risk summary", txt))

st.sidebar.download_button("Download sample attendance CSV", sample()[0].to_csv(index=False), "attendance.csv")
st.sidebar.download_button("Download sample marks CSV", sample()[1].to_csv(index=False), "marks.csv")
st.sidebar.download_button("Download sample slots CSV", sample()[2].to_csv(index=False), "slots.csv")