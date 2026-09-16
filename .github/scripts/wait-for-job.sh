#!/usr/bin/env bash
# Wait for one Container Apps Job execution to reach a terminal state.
#
# `az containerapp job start` returns as soon as the execution is queued, so a
# workflow that stops there has proved that Azure accepted the request and
# nothing else. This polls until the execution actually finishes and fails the
# step on anything other than success.
set -euo pipefail

JOB="${1:?job name}"
RESOURCE_GROUP="${2:?resource group}"
EXECUTION="${3:?execution name}"
TIMEOUT_SECONDS="${4:-900}"
INTERVAL_SECONDS=10

deadline=$(( SECONDS + TIMEOUT_SECONDS ))

while (( SECONDS < deadline )); do
  status="$(az containerapp job execution show \
    --name "$JOB" \
    --resource-group "$RESOURCE_GROUP" \
    --job-execution-name "$EXECUTION" \
    --query "properties.status" -o tsv 2>/dev/null || echo "Unknown")"

  echo "${EXECUTION}: ${status}"

  case "$status" in
    Succeeded)
      exit 0
      ;;
    Failed|Degraded|Cancelled)
      echo "::error::execution ${EXECUTION} of job ${JOB} ended as ${status}"
      exit 1
      ;;
  esac

  sleep "$INTERVAL_SECONDS"
done

echo "::error::execution ${EXECUTION} of job ${JOB} did not finish within ${TIMEOUT_SECONDS}s"
exit 1
