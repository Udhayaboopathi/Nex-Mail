#!/bin/sh
set -e

# spamd (Debian package) installs to /usr/sbin/spamd
SPAMD_BIN="/usr/sbin/spamd"

if [ ! -x "$SPAMD_BIN" ]; then
    echo "ERROR: $SPAMD_BIN not found. Installed binaries:"
    find /usr -name "spam*" -o -name "spamd" 2>/dev/null
    exit 1
fi

echo "Starting SpamAssassin daemon: $SPAMD_BIN"

exec "$SPAMD_BIN" \
    --listen=0.0.0.0 \
    --port=783 \
    --nouser-config \
    --username=spamd \
    --helper-home-dir=/var/lib/spamassassin \
    --pidfile=/var/run/spamd/spamd.pid \
    --syslog=stderr \
    -D
