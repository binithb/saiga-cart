#!/usr/bin/env python3
"""Batch query Jira ticket status via REST API."""

import argparse
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def load_local_env() -> None:
    """Load credentials from .env.local or .env if present."""
    search_dirs = [Path.cwd(), Path(__file__).resolve().parents[4]]
    for directory in search_dirs:
        for filename in (".env.local", ".env"):
            env_file = directory / filename
            if env_file.is_file():
                try:
                    for line in env_file.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
                except Exception:
                    pass
                return


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
    load_local_env()
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
