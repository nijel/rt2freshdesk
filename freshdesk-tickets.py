#!/usr/bin/env python
"""
Quick and dirty attempt to migrate issues from Request Tracker to Freshdesk.
"""

import http.client
import json
import logging
import os
import pickle
import sys
from tempfile import TemporaryDirectory

from freshdesk.api import API

DEBUG = False

if DEBUG:
    # Logging for requests
    http.client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


COMMENT_TEMPLATE = """
Ticket imported from Request Tracker

Created: {Created}
Resolved: {Resolved}
Status: {Status}
"""


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

with open("rt2freshdesk.json") as handle:
    config = json.load(handle)


target = API(config["freshdesk_host"], config["freshdesk_key"], version=2)


STATUSMAP = {"new": 2, "open": 2, "resolved": 5, "rejected": 5, "deleted": 5}

# Fetch user mappings
USERMAP = {}
for contact in target.contacts.list_contacts():
    USERMAP[contact.email] = contact.id
for agent in target.agents.list_agents():
    USERMAP[agent.contact["email"]] = agent.id


# Create tickets
with TemporaryDirectory(prefix="rt2freshdesk") as tempdir:
    for ticket in tickets:
        label = "RT-{}".format(ticket["ticket"]["id"].split("/")[1])
        if label != "RT-993":
            continue
        print("Importing {}".format(label))

        kwargs = {}
        # Update owner (if set)
        if ticket["ticket"]["Owner"] != "Nobody":
            kwargs["responder_id"] = USERMAP[
                users[ticket["ticket"]["Owner"]]["EmailAddress"]
            ]

        # Create new ticket
        new_ticket = target.tickets.create_ticket(
            email=users[ticket["ticket"]["Creator"]]["EmailAddress"],
            subject="{} [{}]".format(ticket["ticket"]["Subject"], label),
            type=ticket["ticket"]["Queue"],
            description=ticket["history"][0]["Content"],
            status=STATUSMAP[ticket["ticket"]["Status"]],
            source=1,
            **kwargs,
        )
        # Add comment with metadata
        target.comments.create_note(
            new_ticket.id,
            COMMENT_TEMPLATE.format(**ticket["ticket"]),
            private=True,
            user_id=USERMAP[config["fallback_user"]],
        )

        for item in ticket["history"]:
            if item["Type"] not in ("Correspond", "Comment"):
                continue
            files = []
            for a, title in item["Attachments"]:
                data = attachments[a]
                if data["Filename"] in ("", "signature.asc"):
                    continue
                filename = os.path.join(tempdir.name, data["Filename"])
                with open(filename, "wb") as handle:
                    handle.write(data["Content"])
                files.append(filename)

            target.comments.create_note(
                new_ticket.id,
                item["Content"],
                private=item["Type"] == "Comment",
                user_id=USERMAP[users[item["Creator"]]["EmailAddress"]],
                attachments=files,
            )
