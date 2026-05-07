"""
task_client.core
~~~~~~~~~~~~~~~~
Core library for the Ophix task client.

Provides get_tasks() for fetching the active task list from a task server.
Import from here in Tier 2 clients:

    from task_client.core import get_tasks
"""

import os
import platform
import sys
from pathlib import Path
from typing import Dict, List, Optional

import requests
from dotenv import find_dotenv, load_dotenv

try:
    import distro
except ImportError:
    distro = None

from task_client._version import __version__

ENV_FILE_NAME = ".task.env"

TASKSERVER_URL = "TASKSERVER_URL"
TASKSERVER_API_TOKEN = "TASKSERVER_API_TOKEN"
TASKSERVER_CA_CERT = "TASKSERVER_CA_CERT"


def get_client_version():
    # type: () -> str
    return __version__


def in_venv():
    # type: () -> Optional[Path]
    if hasattr(sys, "real_prefix") or sys.prefix != sys.base_prefix:
        return Path(sys.prefix)
    return None


def detect_os_flavour():
    # type: () -> str
    system = platform.system()
    if system == "Linux" and distro:
        name = distro.name(pretty=True)
        version = distro.version(best=True)
        if name and version:
            return "{} {}".format(name, version)
        return name or "Linux"
    if system == "Darwin":
        return "macOS {}".format(platform.mac_ver()[0])
    if system == "Windows":
        return "Windows {}".format(platform.release())
    return system


def build_client_headers(api_token=None):
    # type: (Optional[str]) -> Dict[str, str]
    headers = {
        "X-Task-Client-Version": get_client_version(),
        "X-Task-Python-Version": "{}.{}.{}".format(
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        ),
        "X-Task-OS-Type": platform.system().lower(),
        "X-Task-OS": detect_os_flavour(),
    }
    venv_path = in_venv()
    if venv_path:
        headers["X-Task-Venv-Name"] = venv_path.name
    if api_token:
        headers["Authorization"] = "Token {}".format(api_token)
    return headers


def _resolve_server_config(
    server_url=None,        # type: Optional[str]
    api_token=None,         # type: Optional[str]
    ca_cert=None,           # type: Optional[str]
    exit_on_error=True,     # type: bool
    return_env_path=False,  # type: bool
):
    # type: (...) -> tuple
    """
    Resolve server configuration from arguments, .task.env, or environment.
    """
    env_path_found = None
    task_env_path = find_dotenv(filename=ENV_FILE_NAME, usecwd=True)
    if task_env_path:
        load_dotenv(task_env_path)
        env_path_found = task_env_path

    server_url = server_url or os.getenv(TASKSERVER_URL)
    api_token = api_token or os.getenv(TASKSERVER_API_TOKEN)
    ca_cert = ca_cert or os.getenv(TASKSERVER_CA_CERT)

    errors = []
    if not server_url:
        errors.append("Server URL not set ({})".format(TASKSERVER_URL))
    if not api_token or len(api_token) != 64:
        errors.append(
            "API token missing or invalid ({} — must be 64 hex chars)".format(TASKSERVER_API_TOKEN)
        )
    if ca_cert:
        ca_path = Path(ca_cert)
        if not ca_path.exists():
            errors.append("CA cert file not found at {}".format(ca_cert))
        else:
            ca_cert = str(ca_path.resolve())

    if errors:
        msg = "\n".join(errors)
        if exit_on_error:
            print("Error resolving server config:\n{}".format(msg))
            sys.exit(1)
        else:
            raise ValueError(msg)

    if return_env_path:
        return server_url, api_token, ca_cert, env_path_found
    return server_url, api_token, ca_cert


def get_tasks(
    schedule=None,    # type: Optional[str]
    server_url=None,  # type: Optional[str]
    api_token=None,   # type: Optional[str]
    ca_cert=None,     # type: Optional[str]
):
    # type: (...) -> List[Dict]
    """
    Fetch the task list from the task server.

    If schedule is given, only tasks from that named schedule are returned.
    Without it, tasks from all enabled schedules for the client are returned.

    Includes disabled tasks (enabled=False) so Tier 2 clients can comment
    them out rather than silently removing them. Time bounds are enforced
    server-side.
    """
    server_url, api_token, ca_cert = _resolve_server_config(server_url, api_token, ca_cert)
    url = "{}/api/tasks/".format(server_url.rstrip("/"))
    headers = build_client_headers(api_token=api_token)
    params = {"schedule": schedule} if schedule else {}
    response = requests.get(url, headers=headers, params=params, verify=ca_cert or True)
    response.raise_for_status()
    return response.json()


def create_task(
    schedule,           # type: str
    name,               # type: str
    command,            # type: str
    description="",     # type: str
    interval="",        # type: str
    run_at=None,        # type: Optional[str]
    starts_at=None,     # type: Optional[str]
    ends_at=None,       # type: Optional[str]
    stdout_handling="inherit",  # type: str
    stderr_handling="inherit",  # type: str
    log_file="",        # type: str
    server_url=None,    # type: Optional[str]
    api_token=None,     # type: Optional[str]
    ca_cert=None,       # type: Optional[str]
):
    # type: (...) -> Dict
    """
    Create a task on the task server within the named schedule.

    The client must have can_update access to the schedule. If a task with
    the same command already exists in the schedule (enabled or disabled),
    the server skips creation and returns {"status": "skipped", "id": <int>}.

    Returns {"status": "created"|"skipped", "id": <int>}.
    """
    server_url, api_token, ca_cert = _resolve_server_config(server_url, api_token, ca_cert)
    url = "{}/api/tasks/".format(server_url.rstrip("/"))
    headers = build_client_headers(api_token=api_token)
    headers["Content-Type"] = "application/json"
    payload = {
        "schedule": schedule,
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
    response = requests.post(url, headers=headers, json=payload, verify=ca_cert or True)
    response.raise_for_status()
    return response.json()
