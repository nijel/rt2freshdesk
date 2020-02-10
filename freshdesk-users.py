#!/usr/bin/env python
"""
Quick and dirty attempt to migrate issues from Request Tracker to Freshdesk.
"""

import os
import pickle
import sys
from csv import DictWriter

if not os.path.exists("rt2freshdesk.cache"):
    print("Missing RT data")
    sys.exit(2)

# Load RT from cache
with open("rt2freshdesk.cache", "rb") as handle:
    data = pickle.load(handle)
    users = data["users"]

with open("freshdesk-users.csv", "w") as handle:
    writer = DictWriter(handle, ["Name", "Email"])
    for user in users.values():
        if user["Privileged"]:
            print("Skipping privileged user {}".format(user["EmailAddress"]))
        writer.writerow({"Name": user["RealName"], "Email": user["EmailAddress"]})
