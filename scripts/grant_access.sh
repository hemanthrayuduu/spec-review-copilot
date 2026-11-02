#!/usr/bin/env bash
# Grant or remove access to the hosted review app (Phase 4).
#   scripts/grant_access.sh add <email> | remove <email> | list
# Updates ALLOWED_USERS on the app's Container App; the change rolls out as a new revision in about a minute.
# Needs the Azure CLI signed in, and AZURE_SUBSCRIPTION_ID set to the subscription that hosts the demo.
set -euo pipefail

APP="${APP_NAME:-ca-specreview-app}"
RG="${RESOURCE_GROUP:-rg-specreview-demo-gwc}"
SUB="${AZURE_SUBSCRIPTION_ID:?set AZURE_SUBSCRIPTION_ID to the subscription that hosts the demo}"
cmd="${1:-}"
email="$(printf '%s' "${2:-}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"

current="$(az containerapp show -n "$APP" -g "$RG" --subscription "$SUB" \
  --query "properties.template.containers[0].env[?name=='ALLOWED_USERS'].value | [0]" -o tsv)"
[ "$current" = "None" ] && current=""  # az prints None for a setting that is not there yet
emails="$(printf '%s' "$current" | tr ',;' '\n\n' | tr -d ' \t\r' | sed '/^$/d')"  # keep the newlines

case "$cmd" in
  list) printf '%s\n' "$emails"; exit 0 ;;
  add) [ -n "$email" ] || { echo "usage: $0 add <email>" >&2; exit 2; }
       emails="$(printf '%s\n%s\n' "$emails" "$email" | sed '/^$/d' | sort -u)" ;;
  remove) [ -n "$email" ] || { echo "usage: $0 remove <email>" >&2; exit 2; }
          emails="$(printf '%s\n' "$emails" | grep -vx "$email" | sed '/^$/d' || true)" ;;
  *) echo "usage: $0 add <email> | remove <email> | list" >&2; exit 2 ;;
esac

joined="$(printf '%s\n' "$emails" | sed '/^$/d' | paste -sd, -)"
az containerapp update -n "$APP" -g "$RG" --subscription "$SUB" --set-env-vars "ALLOWED_USERS=$joined" -o none
echo "ALLOWED_USERS is now: ${joined:-<nobody>}"
