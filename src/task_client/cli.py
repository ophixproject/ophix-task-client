"""
task_client.cli
~~~~~~~~~~~~~~~
Command-line interface for the Ophix task client.

Entry point: task-client (registered in pyproject.toml).
"""

import json
import sys

import requests

from client_core.commands import build_commands
from client_core.core import build_client_headers, resolve_server_config
from client_core.parser import make_main
from task_client._config import CLIENT_CONFIG
from task_client.core import create_task, get_tasks


# ---------------------------------------------------------------------------
# Domain-specific commands
# ---------------------------------------------------------------------------

def cmd_fetch(args):
    try:
        tasks = get_tasks()
        print(json.dumps(tasks, indent=2, default=str))
    except Exception as e:
        print("Failed to fetch tasks: {}".format(e))
        sys.exit(1)


def cmd_create_task(args):
    try:
        result = create_task(
            schedule=args.schedule,
            scheduler=args.scheduler or "",
            name=args.name,
            command=args.command,
            description=args.description or "",
            interval=args.interval or "",
            run_at=args.run_at,
            stdout_handling=args.stdout_handling,
            stderr_handling=args.stderr_handling,
            log_file=args.log_file or "",
        )
        status = result.get("status")
        task_id = result.get("id")
        if status == "created":
            if result.get("schedule_created"):
                print("Created schedule '{}'.".format(args.schedule))
            print("Created task #{}: {}".format(task_id, args.name))
        elif status == "skipped":
            print("Skipped (command already exists as task #{}): {}".format(task_id, args.command[:80]))
        else:
            print("Unexpected response: {}".format(result))
    except Exception as e:
        print("Failed to create task: {}".format(e))
        sys.exit(1)


def cmd_report(args):
    server_url, api_token, ca_cert = resolve_server_config(CLIENT_CONFIG)
    output = sys.stdin.read()
    if not output and not args.force:
        return
    try:
        headers = build_client_headers(CLIENT_CONFIG, api_token=api_token)
        headers["Content-Type"] = "application/json"
        resp = requests.post(
            "{}/api/tasks/{}/report/".format(server_url.rstrip("/"), args.task_id),
            headers=headers,
            json={"output": output, "stream": args.stream},
            verify=ca_cert or True,
        )
        resp.raise_for_status()
    except Exception:
        pass  # Silent failure — task ran; reporting is best-effort


# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------

COMMANDS = build_commands(CLIENT_CONFIG)

COMMANDS["fetch"] = {
    "help": "Fetch and print active tasks as JSON.",
    "arguments": [],
    "handler": cmd_fetch,
}

COMMANDS["create-task"] = {
    "help": "Create a task on the server.",
    "arguments": [
        {"name": "--schedule",  "required": True,
         "help": "Schedule name to add the task to"},
        {"name": "--scheduler", "default": "",
         "help": "Scheduler type (e.g. cron, systemd, wts)"},
        {"name": "--name",      "required": True,
         "help": "Task name"},
        {"name": "--command",   "required": True,
         "help": "Command to execute"},
        {"name": "--description", "default": "",
         "help": "Optional description"},
        {"name": "--interval",  "default": "",
         "help": "Cron expression or systemd calendar spec for recurring tasks"},
        {"name": "--run-at",    "dest": "run_at",    "default": None,
         "help": "ISO datetime for one-off tasks"},
        {"name": "--stdout-handling", "dest": "stdout_handling", "default": "inherit",
         "choices": ["inherit", "report", "null", "file"],
         "help": "Where to send stdout (default: inherit)"},
        {"name": "--stderr-handling", "dest": "stderr_handling", "default": "inherit",
         "choices": ["inherit", "report", "null", "merge", "file"],
         "help": "Where to send stderr (default: inherit)"},
        {"name": "--log-file",  "dest": "log_file",  "default": "",
         "help": "Log file path (used with --stdout-handling=file or --stderr-handling=file)"},
    ],
    "handler": cmd_create_task,
}

COMMANDS["report"] = {
    "help": "Read stdin and post execution output to the server.",
    "arguments": [
        {"name": "task_id", "type": int, "help": "Task ID to report output for"},
        {"name": "--stream", "default": "both",
         "choices": ["stdout", "stderr", "both"],
         "help": "Which stream was captured (default: both)"},
        {"name": "--force", "action": "store_true",
         "help": "Report even if output is empty (default: skip empty reports)"},
    ],
    "handler": cmd_report,
}


main = make_main(CLIENT_CONFIG, COMMANDS)


if __name__ == "__main__":
    main()
