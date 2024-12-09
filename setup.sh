#!/bin/sh

func_def=$(cat <<EOF

function hive_cli() {
    SOCKET=\${DOCKER_SOCKET:-/var/run/docker.sock}
    if [ -S \${SOCKET} ]; then
        SOCKET_GID=\$(stat -c '%g' )
        return 1
    else
        SOCKET_GID=\${DOCKER_SOCKET_GID}
    fi
    if [ -z \${SOCKET_GID} ]; then
        echo "Could not determine docker socket location and id."
        echo "Please set the DOCKER_SOCKET and DOCKER_GID environment variable manually."
        return -1
    fi
    echo "Logging into ghcr.io ..."
    docker login ghcr.io
    docker volume create hive
    docker run -ti --rm \\
     -p 443:443 \\
     -v hive:/workspace/hive \\
     -v /var/run/docker.sock:/var/run/docker.sock \\
     -e UID=\$(id -u) \\
     -e GID=\${SOCKET_GID} \\
     ghcr.io/caretech-owl/hive-cli
    if [ -f $HOME/.hive/_restart ]; then
        echo "Restarting hive-cli ..."
        rm $HOME/.hive/_restart
        hive_cli
    fi
    echo "Shutdown. Goodbye."
}
EOF
)

if [ -f ~/.bashrc ]; then
    if [ $(grep -c "function hive_cli()" ~/.bashrc) -eq 0 ]; then
        echo "✅ Adding hive_cli function to .bashrc ..."
        echo "$func_def" >> ~/.bashrc
    else
        echo "ℹ️ hive_cli function already exists in .bashrc"
    fi
elif [ -f ~/.bash_profile ]; then
    if [ $(grep -c "function hive_cli()" ~/.bash_profile) -eq 0 ]; then
        echo "✅ Adding hive_cli function to .bash_profile ..."
        echo "$func_def" >> ~/.bash_profile
    else
        echo "ℹ️ hive_cli function already exists in .bash_profile"
    fi
fi
if [ -f ~/.zshrc ]; then
    if [ $(grep -c "function hive_cli()" ~/.zshrc) -eq 0 ]; then
        echo "✅ Adding hive_cli function to .zshrc ..."
        echo "$func_def" >> ~/.zshrc
    else
        echo "ℹ️ hive_cli function already exists in .zshrc"
    fi
fi

echo "ℹ️ Please restart your shell or run 'source ~/.bashrc', 'source ~/.zshrc' or 'source ~/.bash_profile'"
echo "ℹ️ To use the function, run 'hive_cli'"
