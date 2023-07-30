## Developing with Visual Studio Code + devcontainer

This approach will create a preconfigured development environment with all the tools you need.

The devcontainer has a Home Assistant core instance with the integration available ready to be added. The instance can be configured in the `./devcontainer/config/configuration.yaml` file.

**Prerequisites**

- Docker
  -  For Linux, macOS, or Windows 10 Pro/Enterprise/Education use the [current release version of Docker](https://docs.docker.com/install/)
  -   Windows 10 Home requires [WSL 2](https://docs.microsoft.com/windows/wsl/wsl2-install) and the current Edge version of Docker Desktop (see instructions [here](https://docs.docker.com/docker-for-windows/wsl-tech-preview/)). This can also be used for Windows Pro/Enterprise/Education.
- [Visual Studio code](https://code.visualstudio.com/)
- [Remote - Containers (VSC Extension)][extension-link]

[More info about requirements and devcontainer in general](https://code.visualstudio.com/docs/remote/containers#_getting-started)

[extension-link]: https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers

**Getting started:**

- Open the repository root folder using Visual Studio code.

Visual Studio code will ask "Reopen in Container", this will start the build of the container.

_If you don't see this notification, open the command palette and select `Remote-Containers: Reopen Folder in Container`._

### Start devcontainer

Open the command palette and select `Tasks: Run Task` then select `Run Home Assistant on port 8123` this will start the Home Assistant instance.

The devcontainer can be restarted by opening the command palette and selecting `Tasks: Restart Running Task`, then select the task `Run Home Assistant on port 8123`.

When the devcontainer is running, open a browser and navigate to `http://localhost:8123` and finish configuration of the instance.

### Step by Step debugging

Modify the `configuration.yaml` file in `.devcontainer/config` folder.

With the devcontainer running you can debug your code in vscode with step by step debugging.

Enable Step by Step debugging by uncommenting the line:

```yaml
# debugpy:
```

Then launch the task `Run Home Assistant on port 8123`, and launch the debugger
with the existing debugging configuration `Python: Attach Local`.

For more information, look at [the Remote Python Debugger integration documentation](https://www.home-assistant.io/integrations/debugpy/).

### Set log level

Modify the `configuration.yaml` file in `.devcontainer/config` folder.

Enable debug logging by uncommenting the line:

```yaml
  # logs:
    # custom_components.ferroamp: debug
```

### Running tests
Test cases are automatically detected by vscode and can be triggered under `Testing` section in vscode.

### Reset Home Assistant instance
Home Assistant instance data is kept in `.devcontainer/config` directory. When the container is started for the first time an empty Home Assistant instance will be initialized in this directory.

To reset the instance revert/delete any the data in this folder and rebuild devcontainer by invoking the `Dev Containers: Rebuild Container` command from vscode command palette.
