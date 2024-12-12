# hive-cli

Controls the CareTech OWL [hive](https://github.com/caretech-owl/hive).

## Quickstart

### Preparations: Login into GHCR

Login into GitHub with a [personal access token (ck)](https://github.com/settings/tokens) that only requires `write:packages` permissions.
Find more info [here](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#authenticating-to-the-container-registry).

```shell
echo "<github_token>" | docker login ghcr.io -u USERNAME --password-stdin
```

### Setup hive-cli

Review [setup.sh](https://raw.githubusercontent.com/caretech-owl/hive-cli/refs/heads/main/setup.sh), download it and execute it or copy/paste the block below.

```shell
curl --proto '=https' --tlsv1.2 -LsSf https://raw.githubusercontent.com/caretech-owl/hive-cli/refs/heads/main/setup.sh | sh
```

### Output

```shell
DOCKER_GID=991
Creating group _docker with GID 991
   Built hive-cli @ file:///workspace/hive-cli
Uninstalled 1 package in 0.58ms
Installed 1 package in 1ms
Poe => prod
DEBUG:hive_cli.repo:Fetching origin from https://github.com/caretech-owl/hive.git
DEBUG:hive_cli.docker:Running command: docker-compose -f compose/gerd.yml ps --format json
INFO:hive_cli.server:Starting server.
INFO:     Started server process [28]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on https://0.0.0.0:443 (Press CTRL+C to quit)
```

`hive-cli` should now be available at https://0.0.0.0:12121 or https://localhost:12121 or https://127.0.0.1:12121 with a self-signed certificate.

## Concept

![](concepts/overview.png)