#!/usr/bin/env bash

cd "$(cd "$(dirname "$0")" >/dev/null 2>&1; pwd -P)" || exit 9

# cd jcalapi
# uvicorn jcalapi.app:app --reload
python main.py
