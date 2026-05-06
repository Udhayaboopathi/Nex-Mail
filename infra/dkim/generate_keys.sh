#!/bin/bash
DOMAIN=$1
if [ -z "$DOMAIN" ]; then echo "Usage: $0 <domain>"; exit 1; fi
mkdir -p infra/dkim
openssl genrsa -out infra/dkim/${DOMAIN}.private 2048
openssl rsa -in infra/dkim/${DOMAIN}.private -pubout -out infra/dkim/${DOMAIN}.public
