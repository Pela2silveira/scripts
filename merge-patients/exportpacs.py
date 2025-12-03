#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exporta todos los pacientes de dcm4chee usando la API REST + Keycloak.

- Se autentica contra Keycloak usando client_credentials.
- Llama a /dcm4chee-arc/aets/{AET}/rs/patients (en formato DICOM JSON).
- Paginación usando offset/limit.
- Convierte tags DICOM básicos a campos legibles:
    - 00100020 -> patient_id
    - 00100010 -> patient_name
    - 00100030 -> birth_date
    - 00100040 -> sex
- Guarda el resultado en un JSON.
"""

import os
import json
import logging
from datetime import datetime

import requests

logger = logging.getLogger("export_dcm4chee_patients")

# === Variables de entorno ===
# Keycloak
AUTH_HOST = os.environ.get("DCM4CHEE_AUTH_HOST", "https://keycloak.example.com")
AUTH_REALM = os.environ.get("DCM4CHEE_AUTH_REALM", "dcm4che")
AUTH_CLIENT = os.environ.get("AUTH_CLIENT", "client")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "xxxxx")  # client_secret

# dcm4chee
DCM4CHEE_HOST = os.environ.get("DCM4CHEE_HOST", "https://pacs.example.com")
DCM4CHEE_AET = os.environ.get("DCM4CHEE_AET", "DCM4CHEE")

# Export
OUTPUT_FILENAME = os.environ.get(
    "DCM4CHEE_PATIENTS_OUTPUT",
    "outputs/pacientes_dcm4chee_api.json",
)

# Paginación
PAGE_SIZE = int(os.environ.get("DCM4CHEE_PAGE_SIZE", "500"))

def setup_logging():
    logger.setLevel(logging.DEBUG)

    # Consola
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(fmt)
    logger.addHandler(ch)


def authenticate_with_keycloak():
    """
    Obtiene un access_token de Keycloak usando client_credentials.
    """
    token_url = (
        f"{AUTH_HOST}/auth/realms/{AUTH_REALM}/protocol/openid-connect/token"
    )

    payload = (
        f"grant_type=client_credentials"
        f"&client_id={AUTH_CLIENT}"
        f"&client_secret={AUTH_TOKEN}"  
    )
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(token_url, data=payload, headers=headers)
        response.raise_for_status()
        access_token = response.json().get("access_token")
        if not access_token:
            logger.error("No se obtuvo access_token desde Keycloak")
            return None
        return access_token
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de autenticación en Keycloak: {e}")
        return None


def get_patients_page(token, offset=0, limit=100):
    """
    Trae una página de pacientes desde dcm4chee.

    Devuelve:
        - lista de objetos DICOM JSON
        - True/False si hay más resultados
    """
    url = (
        f"{DCM4CHEE_HOST}/dcm4chee-arc/aets/{DCM4CHEE_AET}/rs/patients"
        f"?offset={offset}&limit={limit}"
        f"&includefield=all"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/dicom+json",
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            logger.warning("Respuesta de pacientes no es una lista")
            return [], False

        has_more = len(data) == limit
        return data, has_more
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener pacientes de dcm4chee: {e}")
        return [], False


def dicom_pat_to_simple(patient_obj):
    """
    Convierte un objeto DICOM JSON de paciente a un dict simple.
    """

    def get_tag_value(tag):
        val = patient_obj.get(tag, {}).get("Value")
        if isinstance(val, list) and len(val) > 0:
            return val[0]
        return None

    def get_patient_name():
        val = patient_obj.get("00100010", {}).get("Value")
        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
            return val[0].get("Alphabetic")
        return None

    def get_other_patient_ids_sequence():
        # Other Patient IDs Sequence (0010,1002) -> "00101002"
        seq_field = patient_obj.get("00101002")
        if seq_field is None:
            return []

        seq = seq_field.get("Value")
        if not isinstance(seq, list):
            return []

        other_ids = []
        for item in seq:
            if not isinstance(item, dict):
                continue
            val = item.get("00100020", {}).get("Value")
            if isinstance(val, list) and len(val) > 0:
                other_ids.append(val[0])

        return other_ids

    return {
        "patient_id": get_tag_value("00100020"),
        "patient_id_issuer": get_tag_value("00100021"),
        "patient_name": get_patient_name(),
        "birth_date": get_tag_value("00100030"),
        "sex": get_tag_value("00100040"),
        "other_patient_ids": get_other_patient_ids_sequence(),
    }

def annotate_other_patients_flags(patients):
    """
    Para cada paciente con other_patient_ids, agrega:
      - other_patient_andes: True si existe otro paciente con patient_id_issuer == "ANDES"
                             y patient_id == other_patient_id
      - other_patient_manual: True si existe otro paciente con patient_id == other_patient_id
                              y patient_id_issuer vacío o nulo

    Asume que other_patient_ids es una lista y sólo usa el primer elemento.
    """

    # Índice por patient_id -> lista de pacientes con ese ID
    index_by_id = {}
    for p in patients:
        pid = p.get("patient_id")
        if not pid:
            continue
        index_by_id.setdefault(pid, []).append(p)

    for p in patients:
        other_ids = p.get("other_patient_ids") or []
        if not other_ids:
            # No tiene other_patient_ids
            p["other_patient_andes"] = False
            p["other_patient_manual"] = False
            continue

        other_id = other_ids[0]  # asumimos siempre un único elemento

        candidates = index_by_id.get(other_id, [])

        has_andes = False
        has_manual = False

        for q in candidates:
            # "otro" paciente distinto (por si patient_id coincide consigo mismo)
            if q is p:
                continue

            issuer = q.get("patient_id_issuer")

            # ANDES
            if issuer == "ANDES":
                has_andes = True

            # vacío / nulo / solo espacios
            if issuer is None or str(issuer).strip() == "":
                has_manual = True

        p["other_patient_andes"] = has_andes
        p["other_patient_manual"] = has_manual

    return patients

def deduplicate_patients(patients):
    """
    Elimina entradas duplicadas tomando (patient_id, patient_id_issuer)
    como clave. Se queda con la primera ocurrencia encontrada y descarta el resto.
    """
    seen_keys = set()
    unique_patients = []
    duplicates = 0

    for patient in patients:
        patient_id = patient.get("patient_id")
        patient_issuer = patient.get("patient_id_issuer")
        key = (patient_id, patient_issuer)

        # Si no hay patient_id no tiene sentido deduplicar: se conserva.
        if patient_id:
            if key in seen_keys:
                duplicates += 1
                continue
            seen_keys.add(key)

        unique_patients.append(patient)

    return unique_patients, duplicates

def export_all_patients():
    """
    Orquesta:
        - auth
        - paginado
        - conversión
        - guardado a archivo
    """
    token = authenticate_with_keycloak()
    if not token:
        logger.error("No se pudo autenticar en Keycloak. Abortando.")
        return

    all_patients = []
    offset = 0
    limit = PAGE_SIZE

    logger.info("Comenzando exportación de pacientes dcm4chee vía API...")
    while True:
        logger.info(f"Obteniendo página de pacientes: offset={offset}, limit={limit}")
        page, has_more = get_patients_page(token, offset=offset, limit=limit)
        if not page:
            logger.info("No se recibieron más pacientes (o hubo error).")
            break

        for p in page:
            simple = dicom_pat_to_simple(p)
            all_patients.append(simple)

        if not has_more:
            logger.info("No hay más páginas de pacientes.")
            break

        offset += len(page)

    logger.info(f"Total de pacientes obtenidos: {len(all_patients)}")

    # Deduplicar por (patient_id, issuer) para evitar combinaciones repetidas
    deduped_patients, duplicates_removed = deduplicate_patients(all_patients)
    if duplicates_removed:
        logger.info(
            f"Pacientes con patient_id/issuer duplicados descartados: {duplicates_removed}"
        )
        logger.info(f"Total tras deduplicar: {len(deduped_patients)}")
    else:
        logger.info("No se detectaron patient_id/issuer duplicados.")

    # Post-proceso: marcar other_patient_andes / other_patient_manual
    annotate_other_patients_flags(deduped_patients)

    # Asegurar carpeta
    os.makedirs(os.path.dirname(OUTPUT_FILENAME), exist_ok=True)

    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        json.dump(deduped_patients, f, indent=2, ensure_ascii=False)

def main():
    setup_logging()
    export_all_patients()


if __name__ == "__main__":
    main()
