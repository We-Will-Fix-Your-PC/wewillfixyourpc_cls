#!/usr/bin/env bash

/opt/wewillfixyourpc_cls/venv/bin/gunicorn -w 8 -b [::1]:8000 --forwarded-allow-ips "*" --access-logfile - wewillfixyourpc_cls.wsgi:application

