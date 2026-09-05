#!/usr/bin/env bash
set -euo pipefail

for db in ai_newsroom ai_newsroom_test; do
  if psql -lqt | cut -d'|' -f1 | grep -qw "$db"; then
    echo "$db already exists"
  else
    createdb "$db"
    echo "created $db"
  fi
done