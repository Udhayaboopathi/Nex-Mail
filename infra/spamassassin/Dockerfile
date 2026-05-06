FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        spamassassin \
        spamc \
        perl \
        libnet-dns-perl \
        libmail-spamassassin-perl \
        sa-compile \
    && rm -rf /var/lib/apt/lists/*

# Copy local config
COPY local.cf /etc/spamassassin/local.cf

# Create runtime user
RUN useradd -r -s /bin/false spamd && \
    mkdir -p /var/lib/spamassassin && \
    chown spamd:spamd /var/lib/spamassassin

# Update SA rules on first run
RUN sa-update --no-gpg || true

EXPOSE 783

CMD ["spamd", "--listen=0.0.0.0", "--port=783", "--nouser-config", \
     "--username=spamd", "--helper-home-dir=/var/lib/spamassassin", \
     "--syslog=stderr", "-D"]
