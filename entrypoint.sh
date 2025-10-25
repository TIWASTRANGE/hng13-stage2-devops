#!/bin/sh
export BACKUP_POOL=$([ "$ACTIVE_POOL" = "blue" ] && echo "green" || echo "blue")
envsubst '${ACTIVE_POOL} ${BACKUP_POOL}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
exec nginx -g 'daemon off;