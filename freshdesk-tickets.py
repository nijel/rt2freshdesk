#!/usr/bin/env python
"""
Quick and dirty attempt to migrate issues from Request Tracker to Freshdesk.
"""

import base64
import json
import os
import pickle
import sys

from freshdesk.api import API


TEMPLATE = """{
"freshdesk_host": "",
"freshdesk_key": "",
"rt_url": "",
"rt_user": "",
"rt_pass": ""
}
"""

COMMENT_TEMPLATE = """
Ticket imported from Request Tracker

Created: {Created}
Resolved: {Resolved}
"""


if not os.path.exists("rt2freshdesk.json"):
    print("Missing rt2freshdesk.json!")
    print("Create one based on following template:")
    print(TEMPLATE)
    sys.exit(1)

with open("rt2freshdesk.json") as handle:
    config = json.load(handle)


target = API(config["freshdesk_host"], config["freshdesk_key"])

if not os.path.exists("rt2freshdesk.cache"):
    print("Missing RT data")
    sys.exit(2)
# Load RT from cache
with open("rt2freshdesk.cache", "rb") as handle:
    data = pickle.load(handle)
users = data["users"]
queues = data["queues"]
tickets = data["tickets"]
attachments = data["attachments"]




STATUSMAP = {"new": 2, "open": 2, "resolved": 4, "rejected": 5, "deleted": 5}

USERMAP = {}

for user in target.user.all():
    USERMAP[user["email"].lower()] = user["login"]


def get_user(userdata):
    email = userdata["EmailAddress"]
    lemail = email.lower()
    # Search existing users
    if lemail not in USERMAP:
        for user in target.user.search({"query": email}):
            USERMAP[user["email"].lower()] = user["login"]
    # Create new one
    if lemail not in USERMAP:
        kwargs = {"email": email}
        if "RealName" in userdata:
            realname = userdata["RealName"]
            if ", " in realname:
                last, first = realname.split(", ", 1)
            elif " " in realname:
                first, last = realname.split(None, 1)
            else:
                last = realname
                first = ""
            kwargs["lastname"] = last
            kwargs["firstname"] = first
        user = target.user.create(kwargs)
        USERMAP[user["email"].lower()] = user["login"]

    return USERMAP[lemail]


# Create tickets
for ticket in tickets:
    label = "RT-{}".format(ticket["ticket"]["id"].split("/")[1])
    print("Importing {}".format(label))
    new = target.tickets.create_ticket(
        email=users[ticket["ticket"]["Creator"]]["EmailAddress"],
        subject="{} [{}]".format(ticket["ticket"]["Subject"], label),
        status=STATUSMAP[ticket["ticket"]["Status"]],
            "note": "RT-import:{}".format(ticket["ticket"]["id"]),
            "article": {
                "subject": ticket["ticket"]["Subject"],
                "body": ticket["history"][0]["Content"],
            },
        }
    )
    tag_obj.add("Ticket", new["id"], ticket["ticket"]["Queue"].lower().split()[0])
    ticket_article.create(
        {
            "ticket_id": new["id"],
            "body": COMMENT_TEMPLATE.format(**ticket["ticket"]),
            "internal": True,
        }
    )

    for item in ticket["history"]:
        if item["Type"] not in ("Correspond", "Comment"):
            continue
        files = []
        for a, title in item["Attachments"]:
            data = attachments[a]
            if data["Filename"] in ("", "signature.asc"):
                continue
            files.append(
                {
                    "filename": data["Filename"],
                    "data": base64.b64encode(data["Content"]).decode("utf-8"),
                    "mime-type": data["ContentType"],
                }
            )
        TicketArticle(get_freshdesk(on_behalf_of=get_user(users[item["Creator"]]))).create(
            {
                "ticket_id": new["id"],
                "body": item["Content"],
                "internal": item["Type"] == "Comment",
                "attachments": files,
            }
        )
