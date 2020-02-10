# rt2freshdesk

Request tracker to Freshdesk migration script. This is not an out of box solution
for everybody, you will probably have to customize it.

Known issues:

* Disabled users from RT can not be accessed by API, thus will lack email
  address and will fail to be created. Enable all users prior to the migration.
* Timestamps are not preserved. The Freshdesk API doesn't seem to allow this.
* Freshdesk will send notification for all actions, you probably want to disable
  outgoing mail for time of import.
* Type field on Freshdesk is used to map queues from RT, please define correct values manually.

Usage:

    # Dump Request Tracker data into local cache
    rt-dump.py

    # Dump users into CSV suitable for Freshdesk import
    freshdesk-users.py
