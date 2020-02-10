#!/usr/bin/env python
"""
Quick and dirty attempt to migrate issues from Request Tracker to Freshdesk.
"""

import json
import os
import pickle
import sys

from rt import Rt

TEMPLATE = """{
"freshdesk_host": "",
"freshdesk_key": "",
"rt_url": "",
"rt_user": "",
"rt_pass": ""
}
"""


if not os.path.exists("rt2freshdesk.json"):
    print("Missing rt2freshdesk.json!")
    print("Create one based on following template:")
    print(TEMPLATE)
    sys.exit(1)

with open("rt2freshdesk.json") as handle:
    config = json.load(handle)


source = Rt(config["rt_url"], config["rt_user"], config["rt_pass"])
if not source.login():
    print("Failed to login to RT!")
    sys.exit(2)

# Load RT from remote
users = {}
attachments = {}
tickets = []
queues = set()


def ensure_user(username):
    if username not in users:
        users[username] = source.get_user(username)


for i in range(1, 2000):
    print("Loading ticket {}".format(i))
    ticket = source.get_ticket(i)
    if ticket is None:
        break
    queues.add(ticket["Queue"])
    ensure_user(ticket["Creator"])
    ensure_user(ticket["Owner"])
    history = source.get_history(i)
    for item in history:
        for a, title in item["Attachments"]:
            attachments[a] = source.get_attachment(i, a)
        ensure_user(item["Creator"])
    tickets.append({"ticket": ticket, "history": history})
with open("rt2freshdesk.cache", "wb") as handle:
    data = pickle.dump(
        {
            "users": users,
            "queues": queues,
            "tickets": tickets,
            "attachments": attachments,
        },
        handle,
    )
