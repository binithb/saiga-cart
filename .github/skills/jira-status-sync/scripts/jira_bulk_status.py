#!/usr/bin/env python3
"""Batch query Jira ticket status via REST API."""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import base64


def query_jira(base_url: str, keys: list[str], auth_header: str | None = None) -> dict[str, str]:
    results = {}
    jql = f"key in ({','.join(keys)})"
    url = f"{base_url.rstrip('/')}/rest/api/3/search?jql={urllib.parse.quote(jql)}&fields=status,summary"
    
    req = urllib.request.Request(url)
    if auth_header:
        req.add_header("Authorization", auth_header)
    req.add_header("Accept", "application/json")
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for issue in data.get("issues", []):
                results[issue["key"]] = issue["fields"]["status"]["name"]
    except Exception as e:
        print(f"Error querying Jira: {e}", file=sys.stderr)
    return results


def main():
    parser = argparse.ArgumentParser(description="Query Jira statuses.")
    parser.add_argument("keys", nargs="+", help="Jira issue keys")
    parser.add_argument("--url", default=os.getenv("JIRA_BASE_URL", "https://jira.atlassian.net"))
    args = parser.parse_args()

    token = os.getenv("JIRA_API_TOKEN")
    email = os.getenv("JIRA_USER_EMAIL")
    auth = None
    if token and email:
        auth = "Basic " + base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("utf-8")
    elif token:
        auth = f"Bearer {token}"

    statuses = query_jira(args.url, args.keys, auth)
    print(json.dumps(statuses, indent=2))


if __name__ == "__main__":
    main()
