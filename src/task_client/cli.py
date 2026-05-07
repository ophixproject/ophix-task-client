"""
task_client.cli
~~~~~~~~~~~~~~~
Command-line interface for the Ophix task client.

Entry point: task-client (registered in pyproject.toml).
"""

import argparse
import json
import os
import secrets
import sys
import urllib3
from pathlib import Path
from typing import Optional

import requests
from dotenv import find_dotenv, set_key, dotenv_values

from task_client.core import (
    ENV_FILE_NAME,
    TASKSERVER_URL,
    TASKSERVER_API_TOKEN,
    TASKSERVER_CA_CERT,
    _resolve_server_config,
    build_client_headers,
    get_client_version,
    get_tasks,
    in_venv,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_project_root():
    # type: () -> Path
    cwd = Path.cwd()
    venv_root = in_venv()
    if venv_root:
        return venv_root.parent
    for parent in [cwd] + list(cwd.parents):
        if (
            (parent / "requirements.txt").exists()
            or (parent / ".git").exists()
            or (parent / ".env").exists()
        ):
            return parent
    return cwd


def get_or_create_env():
    # type: () -> Path
    existing = find_dotenv(filename=ENV_FILE_NAME, usecwd=True)
    if existing:
        return Path(existing)
    root = find_project_root()
    path = root / ENV_FILE_NAME
    path.touch()
    return path


def _post_json(url, payload, api_token=None, ca_cert=None, verify_ssl=True):
    # type: (str, dict, Optional[str], Optional[str], bool) -> requests.Response
    headers = build_client_headers(api_token=api_token)
    headers["Content-Type"] = "application/json"
    verify = ca_cert or verify_ssl
    return requests.post(url, headers=headers, json=payload, verify=verify)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_quickstart(args):
    server_url = args.server_url.rstrip("/")
    client_name = args.client_name

    env_path = get_or_create_env()

    # Step 1: set server URL
    set_key(str(env_path), TASKSERVER_URL, server_url)
    print("Server URL saved.")

    # Step 2: download CA cert
    urllib3.disable_warnings()
    ca_path = env_path.parent / "taskserver-ca.pem"
    try:
        resp = requests.get("{}/ca-cert/".format(server_url), verify=False)
        resp.raise_for_status()
        ca_path.write_text(resp.text)
        set_key(str(env_path), TASKSERVER_CA_CERT, str(ca_path))
        print("CA certificate saved to {}.".format(ca_path))
    except Exception as e:
        print("WARNING: Could not download CA cert: {}".format(e))
        print("You can download it manually with: task-client download ca-cert")

    # Step 3: register
    new_token = secrets.token_hex(32)
    ca_cert = str(ca_path) if ca_path.exists() else None
    try:
        resp = _post_json(
            "{}/api/register/".format(server_url),
            {"name": client_name, "token": new_token},
            ca_cert=ca_cert,
        )
        resp.raise_for_status()
        set_key(str(env_path), TASKSERVER_API_TOKEN, new_token)
        print("Client '{}' registered. Token saved to {}.".format(client_name, env_path))
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 409:
            print("Client '{}' is already registered on this server.".format(client_name))
        else:
            print("Registration failed: {}".format(e))
            sys.exit(1)


def cmd_set(args):
    env_path = get_or_create_env()
    if args.key == "server":
        set_key(str(env_path), TASKSERVER_URL, args.value)
        print("Server URL set to {}.".format(args.value))
    else:
        print("Unknown key '{}'. Valid keys: server".format(args.key))
        sys.exit(1)


def cmd_download(args):
    if args.what == "ca-cert":
        server_url, _, _, env_path = _resolve_server_config(
            exit_on_error=False,
            return_env_path=True,
            ignore_missing_keys=[TASKSERVER_API_TOKEN],
        ) if False else (None, None, None, None)

        # Re-resolve with relaxed token check
        env_path_str = find_dotenv(filename=ENV_FILE_NAME, usecwd=True)
        from dotenv import load_dotenv
        if env_path_str:
            load_dotenv(env_path_str)
        server_url = os.getenv(TASKSERVER_URL)
        if not server_url:
            print("Server URL not set. Run: task-client set server <url>")
            sys.exit(1)

        env_path = Path(env_path_str) if env_path_str else get_or_create_env()
        ca_path = env_path.parent / "taskserver-ca.pem"

        urllib3.disable_warnings()
        try:
            resp = requests.get("{}/ca-cert/".format(server_url.rstrip("/")), verify=False)
            resp.raise_for_status()
            ca_path.write_text(resp.text)
            set_key(str(env_path), TASKSERVER_CA_CERT, str(ca_path))
            print("CA certificate saved to {}.".format(ca_path))
        except Exception as e:
            print("Failed to download CA cert: {}".format(e))
            sys.exit(1)
    else:
        print("Unknown target '{}'. Valid targets: ca-cert".format(args.what))
        sys.exit(1)


def cmd_register(args):
    server_url, _, ca_cert, env_path = _resolve_server_config(
        exit_on_error=True,
        return_env_path=True,
    )
    env_path = Path(env_path) if env_path else get_or_create_env()
    new_token = secrets.token_hex(32)
    try:
        resp = _post_json(
            "{}/api/register/".format(server_url.rstrip("/")),
            {"name": args.name, "token": new_token},
            ca_cert=ca_cert,
        )
        resp.raise_for_status()
        set_key(str(env_path), TASKSERVER_API_TOKEN, new_token)
        print("Registered as '{}'. Token saved.".format(args.name))
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 409:
            print("Client '{}' is already registered.".format(args.name))
        else:
            print("Registration failed: {}".format(e))
            sys.exit(1)


def cmd_fetch(args):
    try:
        tasks = get_tasks()
        print(json.dumps(tasks, indent=2, default=str))
    except Exception as e:
        print("Failed to fetch tasks: {}".format(e))
        sys.exit(1)


def cmd_rotate_token(args):
    server_url, old_token, ca_cert, env_path = _resolve_server_config(
        exit_on_error=True,
        return_env_path=True,
    )
    env_path = Path(env_path)
    new_token = secrets.token_hex(32)
    try:
        resp = _post_json(
            "{}/api/rotate-token/".format(server_url.rstrip("/")),
            {"token": new_token},
            api_token=old_token,
            ca_cert=ca_cert,
        )
        resp.raise_for_status()
        set_key(str(env_path), TASKSERVER_API_TOKEN, new_token)
        print("Token rotated successfully.")
    except Exception as e:
        print("Token rotation failed: {}".format(e))
        sys.exit(1)


def cmd_info(args):
    env_path_str = find_dotenv(filename=ENV_FILE_NAME, usecwd=True)
    values = dotenv_values(env_path_str) if env_path_str else {}
    print("task-client {}".format(get_client_version()))
    print("Config file: {}".format(env_path_str or "(not found)"))
    print("  {}: {}".format(TASKSERVER_URL, values.get(TASKSERVER_URL, "(not set)")))
    token = values.get(TASKSERVER_API_TOKEN, "")
    print("  {}: {}".format(TASKSERVER_API_TOKEN, "{}...".format(token[:8]) if token else "(not set)"))
    print("  {}: {}".format(TASKSERVER_CA_CERT, values.get(TASKSERVER_CA_CERT, "(not set)")))


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser():
    # type: () -> argparse.ArgumentParser
    parser = argparse.ArgumentParser(
        prog="task-client",
        description="Ophix task client — fetch scheduled tasks from a task server.",
    )
    parser.add_argument("--version", action="version", version="task-client {}".format(get_client_version()))

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # quickstart
    p = sub.add_parser("quickstart", help="Set server, download CA cert, and register in one step.")
    p.add_argument("server_url", help="Task server URL (e.g. https://tasks.internal)")
    p.add_argument("client_name", help="Name to register this client as")

    # set
    p = sub.add_parser("set", help="Set a configuration value.")
    p.add_argument("key", help="Key to set (server)")
    p.add_argument("value", help="Value to set")

    # download
    p = sub.add_parser("download", help="Download resources from the server.")
    p.add_argument("what", help="What to download (ca-cert)")

    # register
    p = sub.add_parser("register", help="Register this client with the task server.")
    p.add_argument("name", help="Client name to register")

    # fetch
    sub.add_parser("fetch", help="Fetch and print active tasks as JSON.")

    # rotate-token
    sub.add_parser("rotate-token", help="Rotate the API token.")

    # info
    sub.add_parser("info", help="Show current configuration.")

    return parser


COMMANDS = {
    "quickstart": cmd_quickstart,
    "set": cmd_set,
    "download": cmd_download,
    "register": cmd_register,
    "fetch": cmd_fetch,
    "rotate-token": cmd_rotate_token,
    "info": cmd_info,
}


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    handler = COMMANDS.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
