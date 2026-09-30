# ophix-task-client

**The piece that turns "what should run where" into a task your host can actually see.**

A central schedule is only useful if every host can reliably pull its own slice of it — authenticate, fetch, and know what changed. `ophix-task-client` is that connection: it registers the host with your [Ophix](https://ophix.io) task server, exposes a `task-client` CLI for bootstrapping and debugging, and an importable library (`get_tasks()`, `create_task()`) that [ophix-task-crontab](https://github.com/ophixproject/ophix-task-crontab) and [ophix-task-systemd](https://github.com/ophixproject/ophix-task-systemd) build on to actually apply tasks to the host's native scheduler.

---

## Installation

```bash
pip install ophix-task-client venv-cmds
```

`venv-cmds` is optional but recommended — it provides `venv-cmds list` to discover all
commands available in the venv and `venv-cmds check_updates` to check for new releases.

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
  --scheduler cron \
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
| `--scheduler` | No | Scheduler type (e.g. `cron`, `systemd`, `wts`) — must match an existing, enabled Scheduler on the server. Determines the expected `--interval` format. |
| `--name` | Yes | Task name |
| `--command` | Yes | Command to execute |
| `--description` | No | Comment written above the cron entry |
| `--interval` | No | An expression in the format the assigned `--scheduler` expects (e.g. a cron expression for `cron`) |
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

### `get_tasks(schedule=None, scheduler=None, server_url=None, api_token=None, ca_cert=None)`

Fetch the task list. Returns a list of dicts.

```python
tasks = get_tasks()                                # all linked schedules
tasks = get_tasks(schedule="server-maintenance")   # one schedule only
tasks = get_tasks(scheduler="cron")                # only tasks assigned to a given scheduler type
```

Each dict includes: `id`, `schedule`, `scheduler`, `name`, `command`, `description`, `run_at`, `interval`, `starts_at`, `ends_at`, `enabled`, `paused`, `stdout_handling`, `stderr_handling`, `log_file`.

Disabled tasks (`enabled=False`) are excluded entirely; paused tasks (`paused=True`) are included so Tier 2 clients can write them as commented-out/disabled entries. `paused` is an effective value — true if the task, its Schedule, or this client's access to that Schedule is paused.

### `create_task(schedule, name, command, ...)`

Create a task on the server. Returns `{"status": "created"|"skipped", "id": <int>}`.

```python
result = create_task(
    schedule="server-maintenance",
    scheduler="cron",
    name="nightly-backup",
    command="/opt/backup.sh",
    interval="0 2 * * *",
    stdout_handling="report",
    stderr_handling="merge",
)
```

Full signature:

```python
create_task(
    schedule,                   # Schedule name (required)
    name,                       # Task name (required)
    command,                    # Command to execute (required)
    description="",             # Comment text
    scheduler="",               # Scheduler name (e.g. "cron", "systemd") - determines expected interval format
    interval="",                # Interval expression matching the scheduler's format
    run_at=None,                # ISO datetime string for one-off tasks
    starts_at=None,             # ISO datetime string
    ends_at=None,                # ISO datetime string
    stdout_handling="inherit",  # inherit | report | null | file
    stderr_handling="inherit",  # inherit | report | null | merge | file
    log_file="",                # Log file path
    server_url=None,            # Override .task.env
    api_token=None,             # Override .task.env
    ca_cert=None,                # Override .task.env
)
```
