# ophix-task-client

Tier 1 client for [Ophix](https://ophixproject.com) task scheduling servers.

Handles authentication, registration, and task fetching. Exposes `get_tasks()` as an importable library for Tier 2 clients (e.g. `ophix-task-crontab`).

---

## Installation

```bash
pip install ophix-task-client
```

Requires Python 3.7+.

---

## Quick start

```bash
task-client quickstart https://tasks.internal myhost-tasks
```

This sets the server URL, downloads the CA certificate, and registers the client in one step. The API token is saved automatically.

---

## Configuration

Configuration is stored in `.task.env` in the project root (or venv parent directory).

| Variable | Description |
| --- | --- |
| `TASKSERVER_URL` | Task server base URL (e.g. `https://tasks.internal`) |
| `TASKSERVER_API_TOKEN` | 64-character hex token issued on registration |
| `TASKSERVER_CA_CERT` | Path to the server's CA certificate PEM file |

---

## CLI reference

### `task-client quickstart <server_url> <client_name>`

Set server URL, download CA certificate, and register this client in one step.

```bash
task-client quickstart https://tasks.internal myhost-tasks
```

### `task-client set server <url>`

Set the task server URL.

```bash
task-client set server https://tasks.internal
```

### `task-client download ca-cert`

Download and save the server's CA certificate. Required for TLS verification.

```bash
task-client download ca-cert
```

### `task-client register <name>`

Register this client with the task server. Generates a token and saves it to `.task.env`.

```bash
task-client register myhost-tasks
```

### `task-client fetch`

Fetch the active task list and print it as JSON. Useful for inspection and debugging.

```bash
task-client fetch
```

### `task-client rotate-token`

Generate a new token, send it to the server, and update `.task.env`. Run regularly via a separate cron job to limit token exposure.

```bash
task-client rotate-token
```

### `task-client report <task_id>`

Read stdin and post the content to the server as an execution log entry for the given task. Used as part of a cron pipe expression — not normally run directly.

```bash
task-client report 42
```

Fails silently — the task already ran; reporting is best-effort and should not cause the cron job to show a failure.

### `task-client info`

Show the current configuration (server URL, token prefix, CA cert path).

```bash
task-client info
```

### `task-client doctor`

Check local configuration and server connectivity. Reports on the ENV file, permissions, token validity, CA cert path, and makes a live authenticated request to confirm the server accepts the token.

```bash
task-client doctor
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
| --- | --- | --- |
| `id` | int | Task ID on the server |
| `schedule` | str | Schedule name |
| `name` | str | Task name |
| `command` | str | Command to execute |
| `run_at` | str or null | ISO datetime for one-off tasks |
| `interval` | str | Cron expression for recurring tasks |
| `starts_at` | str or null | Active from this datetime |
| `ends_at` | str or null | Active until this datetime |

Time bounds are enforced server-side — `get_tasks()` only returns tasks currently within their active window.

---

## Token rotation

Tokens should be rotated regularly. Add a separate cron entry outside the ophix-managed block:

```text
# Weekly token rotation — not managed by ophix-task-crontab
0 3 * * 0 root /path/to/venv/bin/task-client rotate-token
```

Keep this entry separate from the ophix-managed block so it is not overwritten on sync.
