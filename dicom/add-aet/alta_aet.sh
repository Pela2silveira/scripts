#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Uso: $0 NUEVO_AET"
  echo "Ejemplo: $0 PACSCT01"
  exit 1
fi

NUEVO_AET="$1"

# AE Title DICOM: máximo 16 caracteres.
# Uso una validación conservadora para evitar DN raros en LDAP.
if ! echo "${NUEVO_AET}" | grep -Eq '^[A-Za-z0-9_-]{1,16}$'; then
  echo "ERROR: NUEVO_AET inválido: ${NUEVO_AET}"
  echo "Usá solo letras, números, guion o guion bajo. Máximo 16 caracteres."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

set -a
source ../docker-compose.env
set +a

: "${LDAP_ROOTPASS:?Falta LDAP_ROOTPASS. Ejecutá desde mwl-test o revisá ../docker-compose.env}"

LDAP_CONTAINER="${LDAP_CONTAINER:-ldap}"
LDAP_URL="ldap://localhost:389"
LDAP_BIND_DN="cn=admin,dc=dcm4che,dc=org"

DEVICE_NAME="PACSSSS"
BASE_DN="dc=dcm4che,dc=org"
DICOM_CONFIG_DN="cn=DICOM Configuration,${BASE_DN}"
DEVICE_DN="dicomDeviceName=${DEVICE_NAME},cn=Devices,${DICOM_CONFIG_DN}"

SOURCE_AET="PACSSSS"
SOURCE_AE_DN="dicomAETitle=${SOURCE_AET},${DEVICE_DN}"
TARGET_AE_DN="dicomAETitle=${NUEVO_AET},${DEVICE_DN}"

WORK_DIR="./generated-${NUEVO_AET}"
mkdir -p "${WORK_DIR}"

echo "Alta de AET: ${NUEVO_AET}"
echo "Device: ${DEVICE_NAME}"
echo "LDAP container: ${LDAP_CONTAINER}"
echo

echo "1) Verificando si ya existe ${NUEVO_AET}..."

EXISTS_COUNT="$(
  docker exec -i "${LDAP_CONTAINER}" ldapsearch -x -LLL -o ldif-wrap=no \
    -w "${LDAP_ROOTPASS}" \
    -D "${LDAP_BIND_DN}" \
    -H "${LDAP_URL}" \
    -b "${DEVICE_DN}" \
    "(dicomAETitle=${NUEVO_AET})" dn \
  | grep -c '^dn:' || true
)"

if [ "${EXISTS_COUNT}" != "0" ]; then
  echo "ERROR: El AET ${NUEVO_AET} ya existe en LDAP."
  exit 1
fi

echo "OK: ${NUEVO_AET} no existe todavía."
echo

echo "2) Creando LDIF del Application Entity..."

cat > "${WORK_DIR}/01-aet.ldif" <<EOF_LDIF
dn: ${TARGET_AE_DN}
changetype: add
objectClass: dicomNetworkAE
objectClass: dcmNetworkAE
objectClass: dcmArchiveNetworkAE
dicomAETitle: ${NUEVO_AET}
dicomDescription: AET ${NUEVO_AET}
dicomAssociationInitiator: TRUE
dicomAssociationAcceptor: TRUE
dicomNetworkConnectionReference: cn=dicom,${DEVICE_DN}
dicomNetworkConnectionReference: cn=dicom-tls,${DEVICE_DN}
dcmObjectStorageID: fs1
dcmQueryRetrieveViewID: hideRejected
EOF_LDIF

echo "3) Creando LDIF de WebApps REST para ${NUEVO_AET}..."

cat > "${WORK_DIR}/02-webapps.ldif" <<EOF_LDIF
dn: dcmWebAppName=${NUEVO_AET},${DEVICE_DN}
changetype: add
objectClass: dcmWebApp
dcmWebAppName: ${NUEVO_AET}
dicomAETitle: ${NUEVO_AET}
dicomDescription: REST services for ${NUEVO_AET}
dcmWebServiceClass: WADO_RS
dcmWebServiceClass: STOW_RS
dcmWebServiceClass: QIDO_RS
dcmWebServiceClass: UPS_RS
dcmWebServiceClass: MWL_RS
dcmWebServiceClass: QIDO_COUNT
dcmWebServiceClass: DCM4CHEE_ARC_AET
dcmWebServiceClass: UPS_MATCHING
dcmWebServicePath: /dcm4chee-arc/aets/${NUEVO_AET}/rs

dn: dcmWebAppName=${NUEVO_AET}-WADO,${DEVICE_DN}
changetype: add
objectClass: dcmWebApp
dcmWebAppName: ${NUEVO_AET}-WADO
dicomAETitle: ${NUEVO_AET}
dicomDescription: WADO URI service for ${NUEVO_AET}
dcmWebServiceClass: WADO_URI
dcmWebServicePath: /dcm4chee-arc/aets/${NUEVO_AET}/wado
EOF_LDIF

echo "4) Copiando Transfer Capabilities desde ${SOURCE_AET} hacia ${NUEVO_AET}..."

docker exec -i "${LDAP_CONTAINER}" ldapsearch -x -LLL -o ldif-wrap=no \
  -w "${LDAP_ROOTPASS}" \
  -D "${LDAP_BIND_DN}" \
  -H "${LDAP_URL}" \
  -b "${SOURCE_AE_DN}" \
  "(objectClass=dicomTransferCapability)" \
  dn objectClass cn dicomSOPClass dicomTransferRole dicomTransferSyntax \
| sed "s/dicomAETitle=${SOURCE_AET}/dicomAETitle=${NUEVO_AET}/g" \
| awk '
  /^dn: / {
    print
    print "changetype: add"
    next
  }
  { print }
' > "${WORK_DIR}/03-transfer-capabilities.ldif"

TC_COUNT="$(grep -c '^dn:' "${WORK_DIR}/03-transfer-capabilities.ldif" || true)"

if [ "${TC_COUNT}" = "0" ]; then
  echo "ERROR: No se generaron Transfer Capabilities desde ${SOURCE_AET}."
  echo "Revisar si ${SOURCE_AET} tiene capabilities en LDAP."
  exit 1
fi

echo "Transfer Capabilities generadas: ${TC_COUNT}"
echo

echo "5) Aplicando LDIFs en LDAP..."

docker cp "${WORK_DIR}/01-aet.ldif" "${LDAP_CONTAINER}:/tmp/01-aet-${NUEVO_AET}.ldif"
docker cp "${WORK_DIR}/02-webapps.ldif" "${LDAP_CONTAINER}:/tmp/02-webapps-${NUEVO_AET}.ldif"
docker cp "${WORK_DIR}/03-transfer-capabilities.ldif" "${LDAP_CONTAINER}:/tmp/03-transfer-capabilities-${NUEVO_AET}.ldif"

docker exec -i "${LDAP_CONTAINER}" ldapmodify -x \
  -w "${LDAP_ROOTPASS}" \
  -D "${LDAP_BIND_DN}" \
  -H "${LDAP_URL}" \
  -f "/tmp/01-aet-${NUEVO_AET}.ldif"

docker exec -i "${LDAP_CONTAINER}" ldapmodify -x \
  -w "${LDAP_ROOTPASS}" \
  -D "${LDAP_BIND_DN}" \
  -H "${LDAP_URL}" \
  -f "/tmp/02-webapps-${NUEVO_AET}.ldif"

docker exec -i "${LDAP_CONTAINER}" ldapmodify -x \
  -w "${LDAP_ROOTPASS}" \
  -D "${LDAP_BIND_DN}" \
  -H "${LDAP_URL}" \
  -f "/tmp/03-transfer-capabilities-${NUEVO_AET}.ldif"

echo
echo "6) Verificando alta en LDAP..."

docker exec -i "${LDAP_CONTAINER}" ldapsearch -x -LLL -o ldif-wrap=no \
  -w "${LDAP_ROOTPASS}" \
  -D "${LDAP_BIND_DN}" \
  -H "${LDAP_URL}" \
  -b "${TARGET_AE_DN}" \
  "(objectClass=*)" \
  dn objectClass dicomAETitle dicomAssociationAcceptor dicomAssociationInitiator dcmObjectStorageID dcmQueryRetrieveViewID \
  | sed -n '1,80p'

echo
echo "WebApps asociadas:"

docker exec -i "${LDAP_CONTAINER}" ldapsearch -x -LLL -o ldif-wrap=no \
  -w "${LDAP_ROOTPASS}" \
  -D "${LDAP_BIND_DN}" \
  -H "${LDAP_URL}" \
  -b "${DEVICE_DN}" \
  "(|(dcmWebAppName=${NUEVO_AET})(dcmWebAppName=${NUEVO_AET}-WADO))" \
  dn dcmWebAppName dicomAETitle dcmWebServiceClass dcmWebServicePath

echo
echo "Transfer Capabilities cargadas:"

docker exec -i "${LDAP_CONTAINER}" ldapsearch -x -LLL -o ldif-wrap=no \
  -w "${LDAP_ROOTPASS}" \
  -D "${LDAP_BIND_DN}" \
  -H "${LDAP_URL}" \
  -b "${TARGET_AE_DN}" \
  "(objectClass=dicomTransferCapability)" dn \
  | grep -c '^dn:' || true

echo
echo "7) Reiniciando Docker desde el nivel superior con: make restart"
echo

(
  cd ..
  make restart
)

echo
echo "Alta finalizada para AET=${NUEVO_AET}"
echo
echo "Pruebas sugeridas:"
echo
echo "echoscu -v -aec ${NUEVO_AET} -aet TESTSCU localhost 11112"
echo
echo "curl -k -i \\"
echo "  \"https://\${ARCHIVE_HOST}/dcm4chee-arc/aets/${NUEVO_AET}/rs/patients?limit=1\" \\"
echo "  --header \"Authorization: bearer \${TOKEN}\" \\"
echo "  --header \"Accept: application/dicom+json\""
