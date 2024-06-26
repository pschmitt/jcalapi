#!/usr/bin/env bash

cd "$(cd "$(dirname "$0")" >/dev/null 2>&1; pwd -P)" || exit 9

source .envrc

docker run -it --rm -p 7042:7042 \
  -e "CONFLUENCE_URL=${CONFLUENCE_URL}" \
  -e "CONFLUENCE_USERNAME=${CONFLUENCE_USERNAME}" \
  -e "CONFLUENCE_PASSWORD=${CONFLUENCE_PASSWORD}" \
  -e "CONFLUENCE_CONVERT_EMAIL=${CONFLUENCE_CONVERT_EMAIL}" \
  -e "EXCHANGE_USERNAME=${EXCHANGE_USERNAME}" \
  -e "EXCHANGE_PASSWORD=${EXCHANGE_PASSWORD}" \
  -e "EXCHANGE_EMAIL=${EXCHANGE_EMAIL}" \
  -e "EXCHANGE_AUTODISCOVERY=${EXCHANGE_AUTODISCOVERY:-true}" \
  -e "EXCHANGE_SERVICE_ENDPOINT=${EXCHANGE_SERVICE_ENDPOINT}" \
  -e "EXCHANGE_AUTH_TYPE=${EXCHANGE_AUTH_TYPE:-NTLM}" \
  -e "EXCHANGE_SHARED_INBOXES=${EXCHANGE_SHARED_INBOXES}" \
  -e "GOOGLE_CREDENTIALS=${GOOGLE_CREDENTIALS}" \
  -e "GOOGLE_CALENDAR_REGEX=${GOOGLE_CALENDAR_REGEX}" \
  pschmitt/jcalapi
