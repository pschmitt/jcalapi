#!/usr/bin/env bash

cd "$(cd "$(dirname "$0")" >/dev/null 2>&1; pwd -P)" || exit 9

export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)/src"

python -m jcalapi "$@"
