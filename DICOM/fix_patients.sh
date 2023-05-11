#!/bin/bash
AET=PACS
KEYCLOAK_HOST=pacshcm.test.com
PACS_HOST=pacshcm.test.com
PORT=11112
CLIENT_ID=app
CLIENT_SECRET=xxxxxxxxxxx
log=log-$(date +"%y-%m-%d-%H-%M")
fail=FAIL-$(date +"%y-%m-%d-%H-%M")
file=patients_total.json

IFS=$'\n'
for next in `cat $file`; do
    IFS=','
    arr=($next)
    #echo ${arr[1]}
    id=${arr[1]}
    echo "new patient:  "
    mkdir out/$id
    echo $id
    echo $id >> $log
    echo "Replace query file with patient id" >> $log
    sed "s/PatientID/$id/g" query_template  > query.txt
    echo "convert query.txt to dicom file" >> $log
    dump2dcm query.txt query.dcm
    echo "get all studies of this patient and store them in out folder" >> $log
    getscu -v -S -od out/$id -aec $AET $PACS_HOST $PORT query.dcm >> $log
    TOKEN=$(curl -s -k --data "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}" https://${KEYCLOAK_HOST}/auth/realms/dcm4che/protocol/openid-connect/token | jq '.access_token' | tr -d '"' )
    output=$(curl --request POST -s --header "Authorization: bearer ${TOKEN}" https://${PACS_HOST}/dcm4chee-arc/aets/${AET}/rs/studies/reject/113039^DCM?PatientID=${id})
    sleep 180
    echo $output >> $log
    echo "delete rejected studies" >> $log
    TOKEN=$(curl -s -k --data "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}" https://${KEYCLOAK_HOST}/auth/realms/dcm4che/protocol/openid-connect/token | jq '.access_token' | tr -d '"' )
    output=$(curl --request DELETE --header "Authorization: bearer ${TOKEN}" https://${PACS_HOST}/dcm4chee-arc/reject/113039^DCM?keepRejectionNote=false)
    echo $output >> $log
    sleep 180
    echo "delete patient $id" >> $log
    TOKEN=$(curl -s -k --data "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}" https://${KEYCLOAK_HOST}/auth/realms/dcm4che/protocol/openid-connect/token | jq '.access_token' | tr -d '"' )
    output=$(curl --request DELETE --header "Authorization: bearer ${TOKEN}" https://${PACS_HOST}/dcm4chee-arc/aets/${AET}/rs/patients/${id})
    echo $output >> $log
    echo "store every study in out folder. This action create the patient again\n" >>$log
    storescu -v +sd -aec $AET $HOST $PORT ./out/$id >> $log

    echo "change charset of patient" >> $log
    if [ -z "$(ls -A out/$id)" ]; then
	echo "Patient without studies will stay deleted"
        echo "Patient without studies will stay deleted" > $log
    else
        TOKEN=$(curl -s -k --data "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}" https://${KEYCLOAK_HOST}/auth/realms/dcm4che/protocol/openid-connect/token | jq '.access_token' | tr -d '"' )
        output=$(curl -s --header "Authorization: bearer ${TOKEN}" https://${PACS_HOST}/dcm4chee-arc/aets/${AET}/rs/patients?includefield=all\&PatientID=${id}  | sed -s 's/ISO_IR 192/ISO_IR 100/' | curl -s --header "Authorization: bearer ${TOKEN}" -HContent-Type:application/dicom+json -T - https://${PACS_HOST}/dcm4chee-arc/aets/PACSHCM/rs/${AET}/${id}^^^ANDES)
        echo $output
        echo $output >> $log
    fi
    echo "delete content of out folder" >> $log
    rm -rf out/*
done
