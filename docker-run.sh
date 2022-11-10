#!/usr/bin/env bash

cd "$(cd "$(dirname "$0")" >/dev/null 2>&1; pwd -P)" || exit 9

source .envrc

docker run -it --rm -p 7042:7042 \
  -e "CONFLUENCE_URL=${CONFLUENCE_URL}" \
  -e "CONFLUENCE_USERNAME=${CONFLUENCE_USERNAME}" \
  -e "CONFLUENCE_PASSWORD=${CONFLUENCE_PASSWORD}" \
  -e "EXCHANGE_USERNAME=${EXCHANGE_USERNAME}" \
  -e "EXCHANGE_PASSWORD=${EXCHANGE_PASSWORD}" \
  pschmitt/jcalapi
