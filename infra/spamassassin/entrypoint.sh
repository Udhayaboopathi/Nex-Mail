#!/bin/sh
set -e

# SpamAssassin 4.x renamed the daemon binary.
# Detect whichever binary is present and use it.
if command -v spamd > /dev/null 2>&1; then
    SPAMD_BIN="$(command -v spamd)"
elif [ -x /usr/sbin/spamd ]; then
    SPAMD_BIN="/usr/sbin/spamd"
elif [ -x /usr/bin/spamd ]; then
    SPAMD_BIN="/usr/bin/spamd"
elif command -v spamassassin > /dev/null 2>&1; then
    # SA 4.x: the spamassassin binary can run as daemon with --daemon flag
    SPAMD_BIN="$(command -v spamassassin)"
else
    echo "ERROR: cannot find spamd or spamassassin binary"
    find /usr -name "spam*" -type f 2>/dev/null
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
