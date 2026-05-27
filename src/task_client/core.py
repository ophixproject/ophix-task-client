"""
task_client.core
~~~~~~~~~~~~~~~~
Domain library for the Ophix task client.

Import from here in Tier 2 clients:

    from task_client.core import get_tasks
"""

from typing import Dict, List, Optional

import requests

from client_core.core import api_get, api_post, build_client_headers, resolve_server_config
from task_client._config import CLIENT_CONFIG


def get_tasks(
    schedule=None,    # type: Optional[str]
    scheduler=None,   # type: Optional[str]
    server_url=None,  # type: Optional[str]
    api_token=None,   # type: Optional[str]
    ca_cert=None,     # type: Optional[str]
):
    # type: (...) -> List[Dict]
    """
    Fetch the task list from the task server.

    schedule  — if given, only tasks from that named schedule are returned.
    scheduler — if given, only tasks assigned to that scheduler type are
                returned (e.g. 'cron', 'systemd', 'wts').
    """
    server_url, api_token, ca_cert = resolve_server_config(
        CLIENT_CONFIG, server_url, api_token, ca_cert,
    )
    url = "{}/api/tasks/".format(server_url.rstrip("/"))
    headers = build_client_headers(CLIENT_CONFIG, api_token=api_token)
    params = {}
    if schedule:
        params["schedule"] = schedule
    if scheduler:
        params["scheduler"] = scheduler
    response = api_get(url, headers=headers, params=params, verify=ca_cert or True)
    response.raise_for_status()
    return response.json()


def create_task(
    schedule,                    # type: str
    name,                        # type: str
    command,                     # type: str
    description="",              # type: str
    scheduler="",                # type: str
    interval="",                 # type: str
    run_at=None,                 # type: Optional[str]
    starts_at=None,              # type: Optional[str]
    ends_at=None,                # type: Optional[str]
    stdout_handling="inherit",   # type: str
    stderr_handling="inherit",   # type: str
    log_file="",                 # type: str
    server_url=None,             # type: Optional[str]
    api_token=None,              # type: Optional[str]
    ca_cert=None,                # type: Optional[str]
):
    # type: (...) -> Dict
    """
    Create a task on the task server within the named schedule.

    Returns {"status": "created"|"skipped", "id": <int>}.
    """
    server_url, api_token, ca_cert = resolve_server_config(
        CLIENT_CONFIG, server_url, api_token, ca_cert,
    )
    url = "{}/api/tasks/".format(server_url.rstrip("/"))
    headers = build_client_headers(CLIENT_CONFIG, api_token=api_token)
    headers["Content-Type"] = "application/json"
    payload = {
        "schedule": schedule,
        "scheduler": scheduler,
        "name": name,
        "command": command,
        "description": description,
        "interval": interval,
        "run_at": run_at,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "stdout_handling": stdout_handling,
        "stderr_handling": stderr_handling,
        "log_file": log_file,
    }
    response = api_post(url, headers=headers, json=payload, verify=ca_cert or True)
    response.raise_for_status()
    return response.json()
