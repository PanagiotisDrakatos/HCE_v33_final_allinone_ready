#!/usr/bin/env bash
export PATH="$PWD/.venv/bin:$PATH"
AUTO_INSTALL_ACT=1 RUN_ACT=1 RUN_ACT_BEFORE_PUSH=1 RUN_BACKTESTS=1 \
ACT_PLATFORM="ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-24.04" \
bash ./quick_pr.sh
