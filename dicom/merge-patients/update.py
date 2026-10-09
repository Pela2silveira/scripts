#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script batch para múltiples pacientes.

Nuevo Patient ID = primer elemento de other_patient_ids.
Other Patient IDs Sequence se carga con other_patient_new.
"""

import os
import json
import logging
from pathlib import Path
from urllib.parse import quote

import requests

logger = logging.getLogger("fix_patients_changeid_batch")

# === Variables de entorno ===
PATIENTS_INPUT = os.environ.get(
    "PATIENTS_INPUT",
    "outputs/pacientes_andes_false_manual_false.json",
)

# Keycloak
AUTH_HOST = os.environ.get("DCM4CHEE_AUTH_HOST", "https://keycloak.example.com")
AUTH_REALM = os.environ.get("DCM4CHEE_AUTH_REALM", "dcm4che")
AUTH_CLIENT = os.environ.get("AUTH_CLIENT", "client")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "xxxxx")  # client_secret

# dcm4chee
DCM4CHEE_HOST = os.environ.get("DCM4CHEE_HOST", "https://pacs.example.com")
DCM4CHEE_AET = os.environ.get("DCM4CHEE_AET", "DCM4CHEE")


def setup_logging():
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(fmt)
    logger.addHandler(ch)


def authenticate_with_keycloak():
    token_url = (
        f"{AUTH_HOST}/auth/realms/{AUTH_REALM}/protocol/openid-connect/token"
    )

    payload = (
        f"grant_type=client_credentials"
        f"&client_id={AUTH_CLIENT}"
        f"&client_secret={AUTH_TOKEN}"
    )
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    logger.info("Autenticando contra Keycloak...")
    response = requests.post(token_url, data=payload, headers=headers)
    response.raise_for_status()

    access_token = response.json().get("access_token")
    if not access_token:
        raise RuntimeError("No se obtuvo access_token desde Keycloak")

    logger.info("Autenticación OK.")
    return access_token


def call_with_token(token: str, func, *args, **kwargs) -> str:
    """
    Ejecuta la función func usando el token actual.
    Si responde 401 se reautentica y se reintenta una vez más.
    Devuelve el token válido (puede ser uno nuevo).
    """

    for attempt in (1, 2):
        try:
            func(token, *args, **kwargs)
            return token
        except requests.HTTPError as exc:
            status_code = getattr(
                getattr(exc, "response", None), "status_code", None
            )
            if status_code == 401 and attempt == 1:
                logger.warning(
                    "Token expirado o inválido (401). Reautenticando y reintentando"
                )
                token = authenticate_with_keycloak()
                continue
            raise

    return token


def load_patients(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_patients(path: str, patients: list[dict]):
    """Persist remaining patients atomically to avoid corrupting the file."""
    tmp_path = Path(f"{path}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(patients, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def remove_processed_patient(patient: dict, remaining: list[dict], path: str):
    try:
        remaining.remove(patient)
    except ValueError:
        logger.warning(
            "No se encontró el paciente procesado en el archivo de entrada; "
            "no se realizó ninguna eliminación"
        )
        return

    save_patients(path, remaining)
    logger.info("Paciente procesado eliminado de %s", path)


def post_changeid(token: str, prior_patient_id: str, new_patient_id: str, issuer: str):
    prior_full = f"{prior_patient_id}^^^{issuer}"
    new_full = f"{new_patient_id}^^^{issuer}"

    prior_encoded = quote(prior_full, safe="")
    new_encoded = quote(new_full, safe="")

    url = (
        f"{DCM4CHEE_HOST}/dcm4chee-arc/aets/{DCM4CHEE_AET}"
        f"/rs/patients/{prior_encoded}/changeid/{new_encoded}"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    logger.info(f"[changeid] prior={prior_full} -> new={new_full}")
    resp = requests.post(url, headers=headers)
    logger.info(f"[changeid] Status: {resp.status_code}")
    if resp.text:
        logger.debug(f"[changeid] Response: {resp.text}")
    resp.raise_for_status()


def post_update_other_ids(
    token: str,
    patient_id: str,
    issuer: str,
    new_other_id: str,
    character_set: str | None,
    patient_name: str | None,
    birth_date: str | None,
    sex: str | None,
):
    dicom_pid = f"{patient_id}^^^{issuer}"
    encoded_pid = quote(dicom_pid, safe="")

    url = (
        f"{DCM4CHEE_HOST}/dcm4chee-arc/aets/{DCM4CHEE_AET}"
        f"/rs/patients/{encoded_pid}"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/dicom+json",
    }

    ds: dict[str, object] = {}

    if character_set:
        ds["00080005"] = {"vr": "CS", "Value": [character_set]}

    ds["00100020"] = {"vr": "LO", "Value": [patient_id]}
    ds["00100021"] = {"vr": "LO", "Value": [issuer]}

    if patient_name:
        ds["00100010"] = {
            "vr": "PN",
            "Value": [{"Alphabetic": patient_name}],
        }

    if birth_date:
        ds["00100030"] = {"vr": "DA", "Value": [birth_date]}

    if sex:
        ds["00100040"] = {"vr": "CS", "Value": [sex]}

    # 0010,1002 Other Patient IDs Sequence -> solo new_other_id
    ds["00101002"] = {
        "vr": "SQ",
        "Value": [
            {
                "00100020": {
                    "vr": "LO",
                    "Value": [new_other_id],
                }
            }
        ],
    }

    body = [ds]

    logger.info(f"[updateOtherIDs] {dicom_pid} new_other_id={new_other_id}")
    resp = requests.put(url, headers=headers, data=json.dumps(body))
    logger.info(f"[updateOtherIDs] Status: {resp.status_code}")
    if resp.text:
        logger.debug(f"[updateOtherIDs] Response: {resp.text}")
    resp.raise_for_status()


def main():
    setup_logging()

    logger.info(f"Leyendo pacientes desde: {PATIENTS_INPUT}")
    patients = load_patients(PATIENTS_INPUT)
    logger.info(f"Total pacientes en archivo: {len(patients)}")
    remaining_patients = list(patients)

    filtered = []
    for p in patients:
        issuer = p.get("patient_id_issuer")
        prior_id = p.get("patient_id")
        other_ids = p.get("other_patient_ids") or []
        other_new = p.get("other_patient_new")

        new_id = other_ids[0] if other_ids else None

        if issuer != "ANDES":
            logger.warning(
                f"Skip: patient_id={prior_id} issuer={issuer} (no ANDES)"
            )
            continue
        if not prior_id or not new_id or not other_new:
            logger.warning(
                "Skip: faltan campos obligatorios en paciente: "
                f"patient_id={prior_id}, new_id={new_id}, "
                f"other_patient_new={other_new}, other_patient_ids={other_ids}"
            )
            continue

        filtered.append(p)

    if not filtered:
        logger.error("No hay pacientes válidos para procesar.")
        raise SystemExit(1)

    logger.info(f"Pacientes válidos para procesar: {len(filtered)}")

    print("\n*** MODO DE EJECUCIÓN ***")
    print(f"Pacientes válidos a procesar: {len(filtered)}")
    print("Elige modo:")
    print("  i = iterativo, uno por uno con confirmación")
    print("  a = todos sin confirmación")
    print("  otro = cancelar")
    mode = input("Modo [i/a/otro]: ").strip().lower()

    if mode not in ("i", "a"):
        print("Ejecución cancelada por el usuario.")
        raise SystemExit(0)

    token = authenticate_with_keycloak()
    character_set_default = "ISO_IR 100"

    for idx, p in enumerate(filtered, start=1):
        prior_id = p.get("patient_id")
        issuer = p.get("patient_id_issuer")
        other_new = p.get("other_patient_new")
        other_ids = p.get("other_patient_ids") or []
        new_id = other_ids[0] if other_ids else None
        patient_name = p.get("patient_name")
        birth_date = p.get("birth_date")
        sex = p.get("sex")

        if not new_id:
            logger.error(
                "El paciente %s no tiene new_patient_id válido al momento de "
                "procesarlo; abortando.",
                prior_id,
            )
            raise SystemExit(1)

        logger.info(
            f"\n=== Paciente {idx}/{len(filtered)}: "
            f"{prior_id} -> {new_id} (issuer={issuer}) ==="
        )

        if mode == "i":
            print(
                f"\nPaciente {idx}/{len(filtered)}:"
                f"\n  prior_patient_id  = {prior_id}"
                f"\n  new_patient_id    = {new_id}  (primer elemento de other_patient_ids)"
                f"\n  other_patient_ids = {other_ids}"
                f"\n  issuer            = {issuer}"
                f"\n  other_patient_new = {other_new}"
            )
            choice = input("¿Procesar este paciente? [y/N]: ").strip().lower()
            if choice != "y":
                print("Saltando este paciente.")
                continue

        try:
            token = call_with_token(
                token,
                post_changeid,
                prior_patient_id=prior_id,
                new_patient_id=new_id,
                issuer=issuer,
            )

            token = call_with_token(
                token,
                post_update_other_ids,
                patient_id=new_id,
                issuer=issuer,
                new_other_id=other_new,
                character_set=character_set_default,
                patient_name=patient_name,
                birth_date=birth_date,
                sex=sex,
            )

            logger.info(f"OK paciente {prior_id} -> {new_id}")
            remove_processed_patient(p, remaining_patients, PATIENTS_INPUT)

        except requests.RequestException as e:
            logger.error(
                f"Error procesando paciente {prior_id} -> {new_id}: {e}"
            )
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            if status_code == 500:
                logger.error(
                    "Error 500 del servidor remoto; eliminando paciente del "
                    "%s y continuando",
                    PATIENTS_INPUT,
                )
                remove_processed_patient(p, remaining_patients, PATIENTS_INPUT)
                continue
            # abortar al primer error
            raise SystemExit(1)

    logger.info("Batch completo sin errores.")


if __name__ == "__main__":
    main()
