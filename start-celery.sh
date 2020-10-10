#!/usr/bin/env bash

/opt/wewillfixyourpc_cls/venv/bin/celery -A wewillfixyourpc_cls worker --loglevel=INFO -c 32

