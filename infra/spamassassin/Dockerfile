FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        spamassassin \
        spamc \
        perl \
        libnet-dns-perl \
        libmail-spamassassin-perl \
    && rm -rf /var/lib/apt/lists/*

# Copy local config
COPY local.cf /etc/spamassassin/local.cf

# Create runtime user and working directory
RUN useradd -r -s /bin/false spamd && \
    mkdir -p /var/lib/spamassassin /var/run/spamd && \
    chown -R spamd:spamd /var/lib/spamassassin /var/run/spamd

# Update SA rules (best-effort — no GPG needed for basic rules)
RUN sa-update --no-gpg || true

EXPOSE 783

# Use full path to avoid $PATH issues in containers
CMD ["/usr/sbin/spamd", \
     "--listen=0.0.0.0", \
     "--port=783", \
     "--nouser-config", \
     "--username=spamd", \
     "--helper-home-dir=/var/lib/spamassassin", \
     "--pidfile=/var/run/spamd/spamd.pid", \
     "--syslog=stderr", \
     "-D"]
