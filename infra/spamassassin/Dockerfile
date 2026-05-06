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
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create runtime user and working directory
RUN useradd -r -s /bin/false spamd && \
    mkdir -p /var/lib/spamassassin /var/run/spamd && \
    chown -R spamd:spamd /var/lib/spamassassin /var/run/spamd

# Update SA rules (best-effort)
RUN sa-update --no-gpg || true

EXPOSE 783

ENTRYPOINT ["/entrypoint.sh"]
