#!/usr/bin/env bash
set -euo pipefail

set -a
source ../docker-compose.env
set +a

source ./env.sh

AET="${AET:-PACSHTM}"
PATIENT_ID="MWLTEST001"
PATIENT_NAME="TEST^MWL^DX"
ACCESSION_NUMBER="ACC-MWL-DX-002"
STUDY_UID="1.2.826.0.1.3680043.11.543.202606110001"
SPS_ID="SPS-DX-001"

echo "ARCHIVE_HOST=${ARCHIVE_HOST}"
echo "AET=${AET}"
echo "PATIENT_ID=${PATIENT_ID}"

cat > patient_mwltest001.json <<EOFJSON
{
  "00100010": {
    "vr": "PN",
    "Value": [
      {
        "Alphabetic": "${PATIENT_NAME}"
      }
    ]
  },
  "00100020": {
    "vr": "LO",
    "Value": [ "${PATIENT_ID}" ]
  },
  "00100030": {
    "vr": "DA",
    "Value": [ "19800101" ]
  },
  "00100040": {
    "vr": "CS",
    "Value": [ "O" ]
  }
}
EOFJSON

cat > mwl_dx_001.json <<EOFJSON
{
  "00080005": {
    "vr": "CS",
    "Value": [ "ISO_IR 100" ]
  },
  "00080050": {
    "vr": "SH",
    "Value": [ "${ACCESSION_NUMBER}" ]
  },
  "00080090": {
    "vr": "PN",
    "Value": [
      {
        "Alphabetic": "REFERENTE^MEDICO"
      }
    ]
  },
  "00100010": {
    "vr": "PN",
    "Value": [
      {
        "Alphabetic": "${PATIENT_NAME}"
      }
    ]
  },
  "00100020": {
    "vr": "LO",
    "Value": [ "${PATIENT_ID}" ]
  },
  "00100030": {
    "vr": "DA",
    "Value": [ "19800101" ]
  },
  "00100040": {
    "vr": "CS",
    "Value": [ "O" ]
  },
  "0020000D": {
    "vr": "UI",
    "Value": [ "${STUDY_UID}" ]
  },
  "00321060": {
    "vr": "LO",
    "Value": [ "Radiografia DX de prueba" ]
  },
  "00401001": {
    "vr": "SH",
    "Value": [ "RP-DX-002" ]
  },
  "00401002": {
    "vr": "LO",
    "Value": [ "Carga de prueba MWL" ]
  },
  "00400100": {
    "vr": "SQ",
    "Value": [
      {
        "00080060": {
          "vr": "CS",
          "Value": [ "CR" ]
        },
        "00400002": {
          "vr": "DA",
          "Value": [ "20260703" ]
        },
        "00400003": {
          "vr": "TM",
          "Value": [ "100000" ]
        },
        "00400006": {
          "vr": "PN",
          "Value": [
            {
              "Alphabetic": "OPERADOR^DX"
            }
          ]
        },
        "00400007": {
          "vr": "LO",
          "Value": [ "Radiografia DX de prueba" ]
        },
        "00400009": {
          "vr": "SH",
          "Value": [ "${SPS_ID}" ]
        },
        "00400010": {
          "vr": "SH",
          "Value": [ "SALA-DX-01" ]
        },
        "00400020": {
          "vr": "CS",
          "Value": [ "SCHEDULED" ]
        }
      }
    ]
  }
}
EOFJSON

echo
echo "1) Consultando paciente..."

PATIENT_HTTP_CODE="$(curl -k -s -o patient_lookup_response.json -w "%{http_code}" \
  --location \
  --request GET "https://${ARCHIVE_HOST}/dcm4chee-arc/aets/${AET}/rs/patients?PatientID=${PATIENT_ID}" \
  --header "Authorization: bearer ${TOKEN}" \
  --header "Accept: application/dicom+json")"

echo "GET patient HTTP=${PATIENT_HTTP_CODE}"

PATIENT_EXISTS="false"

if [ "${PATIENT_HTTP_CODE}" = "200" ]; then
  if jq -e 'type == "array" and length > 0' patient_lookup_response.json >/dev/null 2>&1; then
    PATIENT_EXISTS="true"
  fi
fi

if [ "${PATIENT_EXISTS}" = "true" ]; then
  echo "Paciente ya existe."
else
  echo "Paciente no existe. Creando con PUT /patients/${PATIENT_ID}..."

  CREATE_PATIENT_HTTP_CODE="$(curl -k -s -o create_patient_response.json -w "%{http_code}" \
    --location \
    --request PUT "https://${ARCHIVE_HOST}/dcm4chee-arc/aets/${AET}/rs/patients/${PATIENT_ID}" \
    --header "Authorization: bearer ${TOKEN}" \
    --header "Content-Type: application/dicom+json" \
    --header "Accept: application/json" \
    --data-binary @patient_mwltest001.json)"

  echo "PUT patient HTTP=${CREATE_PATIENT_HTTP_CODE}"
  cat create_patient_response.json || true
  echo

  if [ "${CREATE_PATIENT_HTTP_CODE}" != "200" ] && \
     [ "${CREATE_PATIENT_HTTP_CODE}" != "201" ] && \
     [ "${CREATE_PATIENT_HTTP_CODE}" != "204" ]; then
    echo "Falló la creación del paciente."
    exit 1
  fi
fi

echo
echo "2) Reconsultando paciente..."

curl -k -s \
  --location \
  --request GET "https://${ARCHIVE_HOST}/dcm4chee-arc/aets/${AET}/rs/patients?PatientID=${PATIENT_ID}" \
  --header "Authorization: bearer ${TOKEN}" \
  --header "Accept: application/dicom+json" \
  | tee patient_after_create.json \
  | jq .

echo
echo "3) Cargando MWL item DX sin Scheduled Station AE Title..."

CREATE_MWL_HTTP_CODE="$(curl -k -s -o create_mwl_response.json -w "%{http_code}" \
  --location \
  --request POST "https://${ARCHIVE_HOST}/dcm4chee-arc/aets/${AET}/rs/mwlitems" \
  --header "Authorization: bearer ${TOKEN}" \
  --header "Content-Type: application/dicom+json" \
  --header "Accept: application/json" \
  --data-binary @mwl_dx_001.json)"

echo "POST MWL HTTP=${CREATE_MWL_HTTP_CODE}"
cat create_mwl_response.json || true
echo

if [ "${CREATE_MWL_HTTP_CODE}" != "200" ] && \
   [ "${CREATE_MWL_HTTP_CODE}" != "201" ] && \
   [ "${CREATE_MWL_HTTP_CODE}" != "204" ]; then
  echo "Falló la creación del MWL item."
  exit 1
fi

echo
echo "4) Consultando MWL item cargado..."

curl -k -s \
  --location \
  --request GET "https://${ARCHIVE_HOST}/dcm4chee-arc/aets/${AET}/rs/mwlitems?PatientID=${PATIENT_ID}" \
  --header "Authorization: bearer ${TOKEN}" \
  --header "Accept: application/dicom+json" \
  | tee mwl_lookup_response.json \
  | jq .
