"""Gmail triage CLI.

Commands:
  python triage.py report        Summarize inbox: category counts, top senders
  python triage.py run           Dry-run: show what each enabled rule in
                                  rules.yaml would do, without changing anything
  python triage.py run --apply   Actually apply the enabled rules

Rules are Gmail search queries (rules.yaml) — same syntax as the Gmail search
box — each paired with an action: archive, trash, or add_label:<Name>.
"""
import argparse
import sys
from collections import Counter

import yaml

from gmail_client import get_service

CATEGORY_LABELS = [
    "INBOX",
    "UNREAD",
    "CATEGORY_PERSONAL",
    "CATEGORY_SOCIAL",
    "CATEGORY_PROMOTIONS",
    "CATEGORY_UPDATES",
    "CATEGORY_FORUMS",
    "SPAM",
    "TRASH",
]


def cmd_report(service):
    print("Mailbox overview:\n")
    for label_id in CATEGORY_LABELS:
        try:
            label = service.users().labels().get(userId="me", id=label_id).execute()
        except Exception:
            continue
        print(f"  {label_id:22s} {label.get('messagesTotal', 0):>6} messages "
              f"({label.get('messagesUnread', 0)} unread)")

    print("\nTop senders in inbox (sample of last 300 messages):\n")
    resp = service.users().messages().list(
        userId="me", labelIds=["INBOX"], maxResults=300
    ).execute()
    ids = [m["id"] for m in resp.get("messages", [])]

    senders = Counter()

    def collect(request_id, response, exception):
        if exception is None:
            headers = response.get("payload", {}).get("headers", [])
            from_header = next((h["value"] for h in headers if h["name"] == "From"), "unknown")
            senders[from_header] += 1

    # Gmail caps batch requests at 100 inner calls
    for i in range(0, len(ids), 100):
        batch = service.new_batch_http_request()
        for mid in ids[i:i + 100]:
            batch.add(
                service.users().messages().get(
                    userId="me", id=mid, format="metadata", metadataHeaders=["From"]
                ),
                callback=collect,
            )
        batch.execute()

    for sender, count in senders.most_common(15):
        print(f"  {count:>4}  {sender}")


def resolve_label_id(service, name, cache={}):
    if name in cache:
        return cache[name]
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == name:
            cache[name] = label["id"]
            return label["id"]
    created = service.users().labels().create(
        userId="me", body={"name": name, "labelListVisibility": "labelShow",
                            "messageListVisibility": "show"}
    ).execute()
    cache[name] = created["id"]
    return created["id"]


def list_all_ids(service, query):
    ids = []
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId="me", q=query, pageToken=page_token, maxResults=500
        ).execute()
        ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def apply_action(service, ids, action):
    if not ids:
        return
    if action == "archive":
        for i in range(0, len(ids), 1000):
            chunk = ids[i:i + 1000]
            service.users().messages().batchModify(
                userId="me", body={"ids": chunk, "removeLabelIds": ["INBOX"]}
            ).execute()
    elif action == "trash":
        for mid in ids:
            service.users().messages().trash(userId="me", id=mid).execute()
    elif action.startswith("add_label:"):
        label_name = action.split(":", 1)[1]
        label_id = resolve_label_id(service, label_name)
        for i in range(0, len(ids), 1000):
            chunk = ids[i:i + 1000]
            service.users().messages().batchModify(
                userId="me", body={"ids": chunk, "addLabelIds": [label_id]}
            ).execute()
    else:
        raise ValueError(f"Unknown action: {action}")


def cmd_run(service, apply):
    with open("rules.yaml") as f:
        config = yaml.safe_load(f)

    for rule in config.get("rules", []):
        if not rule.get("enabled", False):
            print(f"[skip]    {rule['name']} (disabled)")
            continue

        ids = list_all_ids(service, rule["query"])
        label = "APPLY" if apply else "DRY-RUN"
        print(f"[{label}] {rule['name']}: {len(ids)} messages match "
              f"'{rule['query']}' -> {rule['action']}")

        if apply and ids:
            apply_action(service, ids, rule["action"])
            print(f"          done.")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("report")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--apply", action="store_true",
                             help="Actually perform actions (default is dry-run)")
    args = parser.parse_args()

    service = get_service()

    if args.command == "report":
        cmd_report(service)
    elif args.command == "run":
        cmd_run(service, apply=args.apply)


if __name__ == "__main__":
    main()
