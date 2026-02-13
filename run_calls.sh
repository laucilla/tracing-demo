#!/usr/bin/env bash
# Randomly trigger the two services for a configurable duration.
set -euo pipefail

# Use the first argument as minutes, defaulting to 10.
minutes="${1:-10}"
if ! [[ "$minutes" =~ ^[0-9]+$ ]] || [[ "$minutes" -le 0 ]]; then
  echo "Usage: $0 [minutes]" >&2
  echo "Minutes must be a positive integer." >&2
  exit 1
fi

# Convert minutes to seconds and record the start time.
duration_seconds=$((minutes * 60))
start_time=$(date +%s)

# Call the first service endpoint.
call_service1() {
  curl -X POST http://localhost:8000/proxy \
    -H 'Content-Type: application/json' \
    -d '{"name":"Alice"}'
}

# Call the second service endpoint.
call_otel_service1() {
  curl -X POST http://localhost:9000/call \
    -H 'Content-Type: application/json' \
    -d '{"name":"Tiz"}'
}

# Keep firing random calls until the duration elapses.
while true; do
  now=$(date +%s)
  if (( now - start_time >= duration_seconds )); then
    break
  fi

  # Randomly choose which call to make.
  if (( RANDOM % 2 == 0 )); then
    call_service1
  else
    call_otel_service1
  fi

  # Add a blank line between calls for readability.
  echo

  # Sleep a random 1-5 seconds between calls.
  sleep_seconds=$(( (RANDOM % 5) + 1 ))
  sleep "$sleep_seconds"
done
