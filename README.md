# ophix-task-client

Tier 1 task scheduling client for [Ophix Project](https://ophixproject.com) servers.

Handles authentication, provides an importable library for Tier 2 clients (`get_tasks()`, `create_task()`), and exposes the `task-client` CLI for bootstrapping and diagnostics.

---

## Installation

```bash
pip install ophix-task-client
```

---

## Quickstart

```bash
task-client quickstart https://tasks.example.com myhost-tasks
```

This single command sets the server URL, downloads the CA certificate, and registers the client. The token is saved to `.task.env` automatically.

---

## Configuration file: `.task.env`

| Variable | Description |
| --- | --- |
| `TASKSERVER_URL` | Task server base URL |
| `TASKSERVER_API_TOKEN` | 64-character hex client token |
| `TASKSERVER_CA_CERT` | Path to CA certificate PEM (optional) |

---

## CLI Reference

### `quickstart <server_url> <client_name>`

Bootstrap in one step: set server URL, download CA cert, register.

### `register <name>`

Register this client with the task server. Use after `set server` and `download ca-cert` if bootstrapping step by step.

### `set server <value>`

Write the server URL to `.task.env`.

### `download ca-cert`

Download and save the server CA certificate.

### `rotate-token`

Generate a new token, send it to the server, update `.task.env` on success.

### `fetch`

Fetch and print the active task list as JSON. Useful for debugging.

### `create-task`

Create a task on the server.

```bash
task-client create-task \
  --schedule server-maintenance \
  --name nightly-backup \
  --command "/opt/backup.sh" \
  --description "Nightly backup" \
  --interval "0 2 * * *" \
  --stdout-handling report \
  --stderr-handling merge
```

| Argument | Required | Description |
| --- | --- | --- |
| `--schedule` | Yes | Schedule name |
| `--name` | Yes | Task name |
| `--command` | Yes | Command to execute |
| `--description` | No | Comment written above the cron entry |
| `--interval` | No | Cron expression for recurring tasks |
| `--run-at` | No | ISO datetime for a one-off task |
| `--stdout-handling` | No | `inherit` (default), `report`, `null`, `file` |
| `--stderr-handling` | No | `inherit` (default), `report`, `null`, `merge`, `file` |
| `--log-file` | No | Append path (used with `file` handling) |

### `report <task_id>`

Read stdin and post it to the server as execution output. Normally invoked via a pipe in the generated cron line — not called directly.

### `info`

Show current configuration summary.

### `doctor`

Diagnose local configuration and server connectivity.

---

## Library API

```python
from task_client.core import get_tasks, create_task
```

### `get_tasks(schedule=None, server_url=None, api_token=None, ca_cert=None)`

Fetch the task list. Returns a list of dicts.

```python
tasks = get_tasks()                                # all linked schedules
tasks = get_tasks(schedule="server-maintenance")   # one schedule only
```

Each dict includes: `id`, `schedule`, `name`, `command`, `description`, `run_at`, `interval`, `starts_at`, `ends_at`, `enabled`, `stdout_handling`, `stderr_handling`, `log_file`.

Disabled tasks (`enabled=False`) are included — Tier 2 clients write them as commented-out entries.

### `create_task(schedule, name, command, ...)`

Create a task on the server. Returns `{"status": "created"|"skipped", "id": <int>}`.

```python
result = create_task(
    schedule="server-maintenance",
    name="nightly-backup",
    command="/opt/backup.sh",
    interval="0 2 * * *",
    stdout_handling="report",
    stderr_handling="merge",
)
```
