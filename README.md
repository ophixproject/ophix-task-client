# ophix-task-client

Tier 1 client for [Ophix](https://ophixproject.com) task scheduling servers.

Handles authentication, registration, and task fetching. Exposes `get_tasks()` as an importable library for Tier 2 clients (e.g. `ophix-task-crontab`).

---

## Installation

```
pip install ophix-task-client
```

Requires Python 3.7+.

---

## Quick start

```
task-client quickstart https://tasks.internal myhost-tasks
```

This sets the server URL, downloads the CA certificate, and registers the client in one step. The API token is saved automatically.

---

## Configuration

Configuration is stored in `.task.env` in the project root (or venv parent directory).

| Variable | Description |
|---|---|
| `TASKSERVER_URL` | Task server base URL (e.g. `https://tasks.internal`) |
| `TASKSERVER_API_TOKEN` | 64-character hex token issued on registration |
| `TASKSERVER_CA_CERT` | Path to the server's CA certificate PEM file |

---

## CLI reference

### `task-client quickstart <server_url> <client_name>`

Set server URL, download CA certificate, and register this client in one step.

```
task-client quickstart https://tasks.internal myhost-tasks
```

### `task-client set server <url>`

Set the task server URL.

```
task-client set server https://tasks.internal
```

### `task-client download ca-cert`

Download and save the server's CA certificate. Required for TLS verification.

```
task-client download ca-cert
```

### `task-client register <name>`

Register this client with the task server. Generates a token and saves it to `.task.env`.

```
task-client register myhost-tasks
```

### `task-client fetch`

Fetch the active task list and print it as JSON. Useful for inspection and debugging.

```
task-client fetch
```

### `task-client rotate-token`

Generate a new token, send it to the server, and update `.task.env`. Run regularly via a separate cron job to limit token exposure.

```
task-client rotate-token
```

### `task-client info`

Show the current configuration (server URL, token prefix, CA cert path).

```
task-client info
```

---

## Library usage

Tier 2 clients import directly from `task_client.core`:

```python
from task_client.core import get_tasks

tasks = get_tasks()
for task in tasks:
    print(task["name"], task["interval"] or task["run_at"])
```

`get_tasks()` reads `.task.env` automatically and returns the active task list as a list of dicts. Each dict contains:

| Field | Type | Description |
|---|---|---|
| `id` | int | Task ID on the server |
| `schedule` | str | Schedule name |
| `name` | str | Task name |
| `command` | str | Command to execute |
| `run_at` | str or null | ISO datetime for one-off tasks |
| `interval` | str | Cron expression for recurring tasks |
| `starts_at` | str or null | Active from this UTC datetime |
| `ends_at` | str or null | Active until this UTC datetime |

Time bounds are enforced server-side — `get_tasks()` only returns tasks currently within their active window.

---

## Token rotation

Tokens should be rotated regularly. Add a separate cron entry outside the ophix-managed block:

```
# Weekly token rotation — not managed by ophix-task-crontab
0 3 * * 0 root /path/to/venv/bin/task-client rotate-token
```

Keep this entry separate from the ophix-managed block so it is not overwritten on sync.
