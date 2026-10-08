import pandas as pd
from core import *

df = analyze(pd.read_csv("data/attendance.csv"), pd.read_csv("data/marks.csv"))
txt = weekly_text(df)
print(txt)
for adv in df.advisor_email.unique():
    print(send_email(adv, [], "Weekly at-risk summary", txt))