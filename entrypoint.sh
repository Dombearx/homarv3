#!/bin/bash
# entrypoint.sh

# nadaj poprawne prawa do deploy key
chmod 600 /app/deploy_key

# uruchom oryginalny CMD
exec "$@"