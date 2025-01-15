#!/bin/sh

func_def=$(cat <<EOF

function hive_cli() {
    DOCKER_SOCKET=\${DOCKER_SOCKET:-/var/run/docker.sock}
    DOCKER_AUTH=\${DOCKER_AUTH:-\$HOME/.docker/config.json}
    HIVE_PORT=\${HIVE_PORT:-12121}
    if [ ! -f \${DOCKER_AUTH} ]; then
        echo "❌ Could not find docker auth file at \${DOCKER_AUTH}."
        echo "Please set the DOCKER_AUTH environment variable manually."
        return 1
    fi
    if [ -S \${DOCKER_SOCKET} ]; then
        DOCKER_SOCKET_GID=\$(stat -c '%g' \${DOCKER_SOCKET})
        if [ \$(grep -c "podman.sock" <<< "\${DOCKER_SOCKET}") -eq 1 ]; then
            OPT_SEC_ID=('--userns=keep-id'\\
                '--security-opt'\\
                'label:type:container_runtime_t'\\
            )
        fi
    fi
    if [ -z \${DOCKER_SOCKET_GID} ]; then
        echo "❌ Could not determine docker socket location and id."
        echo "Please set the DOCKER_SOCKET and DOCKER_SOCKET_GID environment variable manually."
        return 1
    fi
    if [ -d "\${HIVE_INPUT}" ]; then
        OPT_INPUT_DIR=('-v'\\
            \${HIVE_INPUT}:/workspace/input\\
        )
    fi
    docker login ghcr.io
    if [ -n "\${CLI_VERSION}" ]; then
        echo "Pulling hive-cli version 'CLI_VERSION' ..."
        docker pull ghcr.io/caretech-owl/hive-cli:\${CLI_VERSION}
    fi
    docker volume create hive > /dev/null
    docker run -ti --rm \\
     -p \${HIVE_PORT}:\${HIVE_PORT} \\
     -v hive:/workspace/hive \\
     -v \${DOCKER_SOCKET}:/var/run/docker.sock \\
     -v \${DOCKER_AUTH}:/docker_config.json \\
     -e UID=\$(id -u) \\
     -e GID=\${DOCKER_SOCKET_GID} \\
     -e HIVE_PORT=\${HIVE_PORT} \\
     \${OPT_SEC_ID[@]} \\
     \${OPT_INPUT_DIR[@]} \\
     ghcr.io/caretech-owl/hive-cli:\${CLI_VERSION:-latest}
    res_code=\$?
    echo "Exited with code \${res_code}"
    if [ \${res_code} -eq 3 ]; then
        echo "Restarting hive-cli ..."
        hive_cli
    else
        echo "Goodbye."
    fi
}
EOF
)

hook_def=$(cat <<EOF
. \$HOME/.hive/cli.sh
EOF
)

echo "Create or override $HOME/.hive/cli.sh"
mkdir -p $HOME/.hive
echo "$func_def" > $HOME/.hive/cli.sh


if [ -f ~/.bashrc ]; then
    if [ $(grep -c ".hive/cli.sh" ~/.bashrc) -eq 0 ]; then
        echo "✅ Adding hive_cli hook to .bashrc ..."
        echo "$hook_def" >> ~/.bashrc
    else
        echo "ℹ️ hive_cli hook already exists in .bashrc"
    fi
elif [ -f ~/.bash_profile ]; then
    if [ $(grep -c ".hive/cli.sh" ~/.bash_profile) -eq 0 ]; then
        echo "✅ Adding hive_cli hook to .bash_profile ..."
        echo "$hook_def" >> ~/.bash_profile
    else
        echo "ℹ️ hive_cli hook already exists in .bash_profile"
    fi
fi
if [ -f ~/.zshrc ]; then
    if [ $(grep -c ".hive/cli.sh" ~/.zshrc) -eq 0 ]; then
        echo "✅ Adding hive_cli hook to .zshrc ..."
         echo "$hook_def" >> ~/.zshrc
    else
        echo "ℹ️ hive_cli hook already exists in .zshrc"
    fi
fi

echo "ℹ️ Please restart your shell or run 'source ~/.bashrc', 'source ~/.zshrc' or 'source ~/.bash_profile'"
echo "ℹ️ To use the function, run 'hive_cli'"
