#!/usr/bin/env bash
if timedatectl show -p NTPSynchronized --value | grep -q "\(true\|yes\)"; then
  echo "✓ System clock synchronized"
  exit 0
else
  echo "✗ System clock NOT synchronized"
  timedatectl status
  exit 1
fi
