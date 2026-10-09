#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exporta todos los pacientes de la colección 'pacientes' en MongoDB
con proyección de campos: _id y documento, y los guarda en un JSON.
"""

import os
import json
from datetime import datetime

from pymongo import MongoClient


def get_mongo_client():
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    user = os.getenv("MONGO_USER")
    password = os.getenv("MONGO_PASSWORD")
    auth_db = os.getenv("MONGO_AUTH_DB", "admin")

    # URI con autenticación + mecanismo SCRAM-SHA-1
    mongo_uri = (
        f"mongodb://{user}:{password}@{host}:{port}/?authSource=andes"
    )
    return MongoClient(mongo_uri)


def export_pacientes():
    db_name: str = os.getenv("MONGO_DB_NAME", "HIS")
    collection_name: str = os.getenv("MONGO_PATIENT_COLLECTION", "pacientes")
    output_file: str | None = None
  
    if output_file is None:
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"outputs/pacientes_mongo_{fecha}.json"

    client = get_mongo_client()
    db = client[db_name]
    col = db[collection_name]

    # Proyección: solo _id y documento
    cursor = col.find({}, {"_id": 1, "documento": 1})

    pacientes = []
    for doc in cursor:
        # Serializar ObjectId como string
        pacientes.append(
            {
                "id": str(doc.get("_id")),
                "documento": doc.get("documento"),
            }
        )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(pacientes, f, indent=2, ensure_ascii=False)

    print(f"Exportados {len(pacientes)} pacientes de MongoDB a {output_file}")


if __name__ == "__main__":
    export_pacientes()
