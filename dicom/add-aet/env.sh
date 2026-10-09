#!/usr/bin/env bash
set -euo pipefail

: "${KEYCLOAK_HOST:=pacs.ar}"
: "${ARCHIVE_HOST:=pacs.ar}"
: "${CLIENT_ID:=andes}"
: "${ANDES_SECRET:?Falta SECRET}"
: "${AET:=PACS}"

TOKEN="$(curl -s -k \
  --data "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${ANDES_SECRET}" \
  "https://${KEYCLOAK_HOST}/auth/realms/dcm4che/protocol/openid-connect/token" \
  | jq -r '.access_token')"

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "No se pudo obtener TOKEN"
  exit 1
fi

export TOKEN
