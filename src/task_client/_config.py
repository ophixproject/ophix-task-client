"""task_client._config — domain ClientConfig instance."""

from client_core.config import ClientConfig
from task_client._version import __version__, __package_name__

CLIENT_CONFIG = ClientConfig(
    prog="task-client",
    description="Ophix task client — fetch scheduled tasks from a task server.",
    env_file=".task.env",
    server_url_key="TASKSERVER_URL",
    api_token_key="TASKSERVER_API_TOKEN",
    ca_cert_key="TASKSERVER_CA_CERT",
    client_name="task",
    version=__version__,
    package_name=__package_name__,
)
