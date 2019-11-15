#!/usr/bin/env bash

VERSION=$(sentry-cli releases propose-version || exit)

docker build -t "theenbyperor/wwfypc-cls:$VERSION" . || exit
docker push "theenbyperor/wwfypc-cls:$VERSION" || exit

sentry-cli releases --org we-will-fix-your-pc new -p cls $VERSION || exit
sentry-cli releases --org we-will-fix-your-pc set-commits --auto $VERSION
