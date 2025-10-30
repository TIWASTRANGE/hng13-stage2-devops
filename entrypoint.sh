#!/bin/sh

# Remove default symlinks to stdout/stderr
rm -f /var/log/nginx/access.log
rm -f /var/log/nginx/error.log

# Create real log files
touch /var/log/nginx/access.log
touch /var/log/nginx/error.log

# Calculate backup pool
export BACKUP_POOL=$([ "$ACTIVE_POOL" = "blue" ] && echo "green" || echo "blue")

# Substitute environment variables
envsubst '${ACTIVE_POOL} ${BACKUP_POOL}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Start nginx
exec nginx -g 'daemon off;'

