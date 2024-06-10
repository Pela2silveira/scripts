#!/bin/bash

ok=OK-$(date +"%h-%m-%s")
fail=FAIL-$(date +"%h-%m-%s")
total=800
limit=100
KEYCLOAK_HOST=pacshcm.test.com
PACS_HOST=pacshcm.test.com
PORT=11112
CLIENT_ID=app
CLIENT_SECRET=xxxxxxxxxxx
AET=PACS

TOKEN=$(curl -s -k --data "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}" https://${KEYCLOAK_HOST}/auth/realms/dcm4che/protocol/openid-connect/token | jq '.access_token' | tr -d '"' )

echo "before"
for num in {0..8500..100}
do
  echo $num
  curl --location --request GET "https://${PACS_HOST}/dcm4chee-arc/aets/${AET}/rs/patients?offset=$num&limit=$limit" --header "Authorization: bearer ${TOKEN}" --header "Accept: application/json" > patient_$num.json
  cat patient_$num.json  | jq '.[] | { "00080005" , "00100020" }' | jq -c '.' | grep "ISO_IR 192" | jq -c '."00080005"."Value" + ."00100020"."Value" ' | tr -d '"[]' > patient__$num.json 
done


cat patient__* > patients_total.json

rm patient_*
