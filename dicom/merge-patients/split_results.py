#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import re

INPUT_FILENAME = os.environ.get(
    "PATIENTS_INPUT",
    "outputs/pacientes_dcm4chee_api.json",
)

OUTPUT_FF = os.environ.get(
    "PATIENTS_OUTPUT_FF",
    "outputs/pacientes_andes_false_manual_false.json",
)
OUTPUT_TF = os.environ.get(
    "PATIENTS_OUTPUT_TF",
    "outputs/pacientes_andes_true_manual_false.json",
)
OUTPUT_FT = os.environ.get(
    "PATIENTS_OUTPUT_FT",
    "outputs/pacientes_andes_false_manual_true.json",
)
OUTPUT_TT = os.environ.get(
    "PATIENTS_OUTPUT_TT",
    "outputs/pacientes_andes_true_manual_true.json",
)

# Nuevo: pacientes sin otro ID alternativo
OUTPUT_NO_OTHER = os.environ.get(
    "PATIENTS_OUTPUT_NO_OTHER",
    "outputs/pacientes_andes_sin_other_id.json",
)

# Regex para validar ObjectId de Mongo (24 hex)
OBJECTID_RE = re.compile(r"^[0-9a-fA-F]{24}$")


def load_patients(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_patients(path: str, patients):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(patients, f, indent=2, ensure_ascii=False)


def is_mongo_objectid(value: str) -> bool:
    if not isinstance(value, str):
        return False
    return bool(OBJECTID_RE.match(value))


def filter_andes_mongo_id(patients):
    """
    Devuelve solo pacientes que cumplen:
      - patient_id_issuer == "ANDES"
      - patient_id con formato de ObjectId de Mongo (24 hex)
    """
    filtered = []
    for p in patients:
        issuer = p.get("patient_id_issuer")
        pid = p.get("patient_id")

        if issuer == "ANDES" and is_mongo_objectid(pid):
            filtered.append(p)

    return filtered


def add_other_patient_new(patients):
    """
    Agrega el campo other_patient_new a cada paciente:
      - trim de patient_id y últimos 15 caracteres.
    """
    for p in patients:
        pid = p.get("patient_id")
        if isinstance(pid, str):
            trimmed = pid.strip()
            p["other_patient_new"] = trimmed[-15:]
        else:
            p["other_patient_new"] = None
    return patients


def split_patients(patients):
    """
    Divide pacientes (ya filtrados y con other_patient_new) en 5 categorías:

      - no_other:     sin other_patient_ids (lista vacía o campo faltante)
      - ff:           other_patient_andes=False, other_patient_manual=False
      - tf:           other_patient_andes=True,  other_patient_manual=False
      - ft:           other_patient_andes=False, other_patient_manual=True
      - tt:           other_patient_andes=True,  other_patient_manual=True
    """

    no_other = []
    ff = []  # andes=False, manual=False
    tf = []  # andes=True,  manual=False
    ft = []  # andes=False, manual=True
    tt = []  # andes=True,  manual=True

    for p in patients:
        other_ids = p.get("other_patient_ids")

        # Si no tiene otro ID alternativo => va a la categoría especial
        if not other_ids:
            no_other.append(p)
            continue

        andes = bool(p.get("other_patient_andes"))
        manual = bool(p.get("other_patient_manual"))

        if andes and manual:
            tt.append(p)
        elif andes and not manual:
            tf.append(p)
        elif not andes and manual:
            ft.append(p)
        else:
            ff.append(p)

    return no_other, ff, tf, ft, tt


def main():
    print(f"Leyendo pacientes desde: {INPUT_FILENAME}")
    patients = load_patients(INPUT_FILENAME)
    print(f"Total pacientes en archivo: {len(patients)}")

    # Filtrar solo ANDES + ObjectId Mongo
    filtered = filter_andes_mongo_id(patients)
    print(f"Pacientes ANDES + ObjectId Mongo: {len(filtered)}")

    # Agregar other_patient_new a todos los filtrados
    add_other_patient_new(filtered)

    # Dividir en categorías
    no_other, ff, tf, ft, tt = split_patients(filtered)

    print(f"Sin other_patient_ids:          {len(no_other)}")
    print(f"FF (andes=False, manual=False): {len(ff)}")
    print(f"TF (andes=True,  manual=False): {len(tf)}")
    print(f"FT (andes=False, manual=True):  {len(ft)}")
    print(f"TT (andes=True,  manual=True):  {len(tt)}")

    save_patients(OUTPUT_NO_OTHER, no_other)
    save_patients(OUTPUT_FF, ff)
    save_patients(OUTPUT_TF, tf)
    save_patients(OUTPUT_FT, ft)
    save_patients(OUTPUT_TT, tt)

    print("Archivos generados:")
    print(f"  {OUTPUT_NO_OTHER}")
    print(f"  {OUTPUT_FF}")
    print(f"  {OUTPUT_TF}")
    print(f"  {OUTPUT_FT}")
    print(f"  {OUTPUT_TT}")


if __name__ == "__main__":
    main()
