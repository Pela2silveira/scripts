"""
Herramienta read-only para consultar pacs-config y generar JSON de alta.
No escribe en MongoDB: solo lectura + generación de documento para pegar en Compass/mongosh.
"""

from __future__ import annotations

import os
import re
from typing import Any, Optional

from bson import ObjectId
from bson.json_util import dumps, RELAXED_JSON_OPTIONS
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

load_dotenv()

CONNECT_TIMEOUT_MS = int(os.environ.get("HIS_MONGO_CONNECT_TIMEOUT_MS", "5000"))
QUERY_TIMEOUT_MS = int(os.environ.get("HIS_MONGO_QUERY_TIMEOUT_MS", "3000"))
MONGO_URI = os.environ.get("HIS_MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.environ.get("HIS_MONGO_DATABASE", "andes")
ORG_COLLECTION = os.environ.get("HIS_MONGO_ORG_COLLECTION", "organizacion")
PACS_COLLECTION = os.environ.get("HIS_MONGO_PACS_COLLECTION", "pacs-config")
PRESTACIONES_COLLECTION = os.environ.get(
    "HIS_MONGO_PRESTACIONES_COLLECTION", "conceptoTurneable"
)
PACS_CLIENT = os.environ.get("PACS_CLIENT", "andes")
PACS_SECRET = os.environ.get("PACS_SECRET", "")
UI_OID_PREFIX = os.environ.get(
    "HIS_UI_OID_PREFIX", "2.16.840.1.1.2.1."
)

app = FastAPI(title="Alta prestaciones PACS", docs_url="/docs")
app.mount("/static", StaticFiles(directory="static"), name="static")

_client: Optional[MongoClient] = None


def ui_suffix(ui: Optional[str]) -> Optional[int]:
    """Extrae el número final del OID (…35.1.201 → 201)."""
    if not ui:
        return None
    ui = ui.strip()
    if ui.startswith(UI_OID_PREFIX):
        tail = ui[len(UI_OID_PREFIX) :]
        if tail.isdigit():
            return int(tail)
    m = re.search(r"\.(\d+)$", ui)
    return int(m.group(1)) if m else None


def make_ui(suffix: int) -> str:
    return f"{UI_OID_PREFIX}{suffix}"


def org_id_str(org_ref: Any) -> str:
    if org_ref is None:
        return ""
    if isinstance(org_ref, ObjectId):
        return str(org_ref)
    if isinstance(org_ref, dict):
        raw = org_ref.get("$oid") or org_ref.get("id") or org_ref.get("_id")
        return org_id_str(raw)
    return str(org_ref)


def build_ui_registry() -> dict[str, Any]:
    """
    Inventario de sufijos UI por organización.
    Un sufijo debería mapear a una sola org; varias configs de la misma org
    pueden compartir el mismo sufijo.
    """
    cursor = coll(PACS_COLLECTION).find(
        {},
        {"ui": 1, "organizacion": 1, "aet": 1, "modalidad": 1},
    ).max_time_ms(QUERY_TIMEOUT_MS)

    # suffix -> { orgId -> {nombre, configs:[{aet,modalidad,_id}]} }
    by_suffix: dict[int, dict[str, dict]] = {}
    no_ui: list[dict] = []

    for doc in cursor:
        suf = ui_suffix(doc.get("ui"))
        org = doc.get("organizacion") or {}
        oid = org_id_str(org.get("id"))
        nombre = org.get("nombre") or "?"
        entry = {
            "_id": doc.get("_id"),
            "aet": doc.get("aet"),
            "modalidad": doc.get("modalidad"),
            "ui": doc.get("ui"),
        }
        if suf is None:
            no_ui.append({**entry, "organizacion": {"id": oid, "nombre": nombre}})
            continue
        orgs = by_suffix.setdefault(suf, {})
        slot = orgs.setdefault(
            oid, {"id": oid, "nombre": nombre, "configs": []}
        )
        slot["configs"].append(entry)
        if nombre and slot["nombre"] == "?":
            slot["nombre"] = nombre

    assignments = []
    duplicates = []
    used = sorted(by_suffix.keys())
    for suf in used:
        orgs = list(by_suffix[suf].values())
        row = {
            "suffix": suf,
            "ui": make_ui(suf),
            "organizaciones": [
                {
                    "id": o["id"],
                    "nombre": o["nombre"],
                    "configs": len(o["configs"]),
                }
                for o in sorted(orgs, key=lambda x: x["nombre"])
            ],
            "orgCount": len(orgs),
            "configCount": sum(len(o["configs"]) for o in orgs),
        }
        assignments.append(row)
        if len(orgs) > 1:
            duplicates.append(row)

    # por org: qué sufijos tiene
    by_org: dict[str, dict] = {}
    for suf, orgs in by_suffix.items():
        for oid, o in orgs.items():
            slot = by_org.setdefault(
                oid,
                {"id": oid, "nombre": o["nombre"], "suffixes": []},
            )
            slot["suffixes"].append(suf)
    for slot in by_org.values():
        slot["suffixes"] = sorted(set(slot["suffixes"]))

    next_suffix = (max(used) + 1) if used else 200
    gaps = []
    if used:
        for n in range(min(used), max(used) + 1):
            if n not in by_suffix:
                gaps.append(n)

    return {
        "prefix": UI_OID_PREFIX,
        "assignments": assignments,
        "duplicates": duplicates,
        "byOrg": list(by_org.values()),
        "noUi": serialize(no_ui),
        "nextSuffix": next_suffix,
        "nextUi": make_ui(next_suffix),
        "gaps": gaps,
        "minSuffix": min(used) if used else None,
        "maxSuffix": max(used) if used else None,
        "usedCount": len(used),
    }


def get_db() -> Database:
    global _client
    if _client is None:
        _client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=CONNECT_TIMEOUT_MS,
            connectTimeoutMS=CONNECT_TIMEOUT_MS,
        )
        _client.admin.command("ping")
    return _client[DATABASE_NAME]


def coll(name: str) -> Collection:
    return get_db()[name]


def serialize(docs: Any) -> list | dict:
    """Serialize BSON → plain Python via Extended JSON round-trip."""
    import json

    return json.loads(dumps(docs, json_options=RELAXED_JSON_OPTIONS))


def escape_regex(text: str) -> str:
    return re.escape(text.strip())


@app.on_event("shutdown")
def shutdown() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/api/health")
def health() -> dict:
    try:
        get_db().client.admin.command("ping")
        return {"ok": True, "database": DATABASE_NAME, "mode": "read-only"}
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"MongoDB no disponible: {e}") from e


@app.get("/api/pacs-config")
def list_pacs_config(
    q: Optional[str] = Query(None, description="Texto libre: org, aet, host"),
    modalidad: Optional[str] = Query(None),
    aet: Optional[str] = Query(None),
    org: Optional[str] = Query(None, description="Nombre de organización"),
    ui: Optional[str] = Query(
        None, description="Sufijo OID (201) o OID completo"
    ),
    limit: int = Query(100, ge=1, le=500),
) -> Response:
    query: dict[str, Any] = {}
    and_clauses: list[dict] = []

    if modalidad:
        and_clauses.append({"modalidad": modalidad.strip().upper()})
    if aet:
        and_clauses.append({"aet": {"$regex": escape_regex(aet), "$options": "i"}})
    if org:
        and_clauses.append(
            {"organizacion.nombre": {"$regex": escape_regex(org), "$options": "i"}}
        )
    if ui:
        ui_val = ui.strip()
        if ui_val.isdigit():
            and_clauses.append({"ui": make_ui(int(ui_val))})
        else:
            and_clauses.append({"ui": ui_val})
    if q:
        rx = {"$regex": escape_regex(q), "$options": "i"}
        and_clauses.append(
            {
                "$or": [
                    {"aet": rx},
                    {"host": rx},
                    {"modalidad": rx},
                    {"organizacion.nombre": rx},
                    {"ui": rx},
                ]
            }
        )

    if and_clauses:
        query["$and"] = and_clauses

    try:
        cursor = (
            coll(PACS_COLLECTION)
            .find(query)
            .sort([("organizacion.nombre", 1), ("modalidad", 1)])
            .limit(limit)
            .max_time_ms(QUERY_TIMEOUT_MS)
        )
        items = list(cursor)
        for item in items:
            item["uiSuffix"] = ui_suffix(item.get("ui"))
        payload = {
            "count": len(items),
            "items": serialize(items),
            "filters": {
                "q": q,
                "modalidad": modalidad,
                "aet": aet,
                "org": org,
                "ui": ui,
                "limit": limit,
            },
        }
        return Response(
            content=dumps(payload, json_options=RELAXED_JSON_OPTIONS, indent=2),
            media_type="application/json",
        )
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/ui-oids")
def list_ui_oids(
    orgId: Optional[str] = Query(None, description="Sugerir UI para esta org"),
) -> Response:
    """Inventario de sufijos UI (únicos por organización) + próximo libre."""
    try:
        registry = build_ui_registry()
        suggestion: dict[str, Any] = {
            "suffix": registry["nextSuffix"],
            "ui": registry["nextUi"],
            "reason": "next_consecutive",
        }
        warnings: list[str] = []

        if orgId:
            org_match = next(
                (o for o in registry["byOrg"] if o["id"] == orgId), None
            )
            if org_match and org_match["suffixes"]:
                # Reusar el primero (idealmente uno solo) ya asignado a la org
                existing = org_match["suffixes"][0]
                suggestion = {
                    "suffix": existing,
                    "ui": make_ui(existing),
                    "reason": "reuse_org",
                    "orgSuffixes": org_match["suffixes"],
                }
                if len(org_match["suffixes"]) > 1:
                    warnings.append(
                        f"La org ya tiene varios sufijos UI: {org_match['suffixes']}. "
                        f"Se sugiere reusar {existing}."
                    )

        registry["suggestion"] = suggestion
        registry["warnings"] = warnings
        return Response(
            content=dumps(registry, json_options=RELAXED_JSON_OPTIONS, indent=2),
            media_type="application/json",
        )
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/ui-oids/check")
def check_ui_oid(
    suffix: Optional[int] = Query(None),
    ui: Optional[str] = Query(None),
    orgId: Optional[str] = Query(None),
) -> dict:
    """Valida si un sufijo/OID está libre o ya usado por otra org."""
    if suffix is None and ui:
        suffix = ui_suffix(ui)
    if suffix is None:
        raise HTTPException(status_code=400, detail="Indicá suffix o ui")

    registry = build_ui_registry()
    row = next((a for a in registry["assignments"] if a["suffix"] == suffix), None)
    if not row:
        return {
            "suffix": suffix,
            "ui": make_ui(suffix),
            "status": "free",
            "ok": True,
            "message": "Libre",
        }

    org_ids = {o["id"] for o in row["organizaciones"]}
    if orgId and orgId in org_ids and len(org_ids) == 1:
        return {
            "suffix": suffix,
            "ui": make_ui(suffix),
            "status": "owned",
            "ok": True,
            "message": "Ya pertenece a esta organización (ok reusar)",
            "organizaciones": row["organizaciones"],
        }
    if orgId and orgId in org_ids and len(org_ids) > 1:
        return {
            "suffix": suffix,
            "ui": make_ui(suffix),
            "status": "duplicate",
            "ok": False,
            "message": "Sufijo compartido por varias orgs (dato inconsistente)",
            "organizaciones": row["organizaciones"],
        }
    if orgId and orgId not in org_ids:
        return {
            "suffix": suffix,
            "ui": make_ui(suffix),
            "status": "taken",
            "ok": False,
            "message": "Ya usado por otra organización",
            "organizaciones": row["organizaciones"],
        }
    return {
        "suffix": suffix,
        "ui": make_ui(suffix),
        "status": "taken" if len(org_ids) == 1 else "duplicate",
        "ok": False,
        "message": "En uso",
        "organizaciones": row["organizaciones"],
    }


@app.get("/api/pacs-config/modalidades")
def list_modalidades() -> dict:
    try:
        values = coll(PACS_COLLECTION).distinct("modalidad")
        return {"items": sorted(v for v in values if v)}
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/organizaciones")
def search_organizaciones(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=50),
) -> Response:
    rx = {"$regex": escape_regex(q), "$options": "i"}
    query = {"$or": [{"nombre": rx}, {"nombreCompleto": rx}]}
    projection = {"nombre": 1, "nombreCompleto": 1, "codigo": 1}
    try:
        items = list(
            coll(ORG_COLLECTION)
            .find(query, projection)
            .sort("nombre", 1)
            .limit(limit)
            .max_time_ms(QUERY_TIMEOUT_MS)
        )
        return Response(
            content=dumps(
                {"count": len(items), "items": items},
                json_options=RELAXED_JSON_OPTIONS,
                indent=2,
            ),
            media_type="application/json",
        )
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/conceptos")
def search_conceptos(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=50),
) -> Response:
    rx = {"$regex": escape_regex(q), "$options": "i"}
    query = {"$or": [{"term": rx}, {"fsn": rx}, {"conceptId": rx}]}
    projection = {
        "term": 1,
        "fsn": 1,
        "semanticTag": 1,
        "conceptId": 1,
        "ambito": 1,
    }
    try:
        items = list(
            coll(PRESTACIONES_COLLECTION)
            .find(query, projection)
            .sort("term", 1)
            .limit(limit)
            .max_time_ms(QUERY_TIMEOUT_MS)
        )
        return Response(
            content=dumps(
                {"count": len(items), "items": items},
                json_options=RELAXED_JSON_OPTIONS,
                indent=2,
            ),
            media_type="application/json",
        )
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/defaults")
def defaults() -> dict:
    """Valores por defecto útiles al armar un alta (clientId/secret desde env)."""
    return {
        "auth": {
            "clientId": PACS_CLIENT,
            "clientSecret": PACS_SECRET or "",
        },
        "featureFlags": {"usoIdDNI": True},
        "uiOidPrefix": UI_OID_PREFIX,
    }


def suggest_hosts(host: str) -> dict[str, str]:
    """
    De https://pacshcm.andes.gob.ar sugiere:
      visualizador_host = https://visor-pacshcm.andes.gob.ar
      auth.host         = https://keycloak-pacshcm.andes.gob.ar
    """
    host = host.rstrip("/")
    m = re.match(r"^(https?://)(.+)$", host)
    if not m:
        return {"visualizador_host": "", "auth_host": ""}
    scheme, name = m.group(1), m.group(2)
    return {
        "visualizador_host": f"{scheme}visor-{name}",
        "auth_host": f"{scheme}keycloak-{name}",
    }


@app.get("/api/suggest-hosts")
def api_suggest_hosts(host: str = Query(...)) -> dict:
    return suggest_hosts(host)


@app.post("/api/generate")
def generate_pacs_config(body: dict[str, Any]) -> Response:
    """
    Arma el documento pacs-config listo para pegar en Compass.
    No inserta nada en la BD.
    """
    org_id = body.get("organizacionId")
    concepto_id = body.get("conceptoId")
    modalidad = (body.get("modalidad") or "").strip().upper()
    host = (body.get("host") or "").strip().rstrip("/")
    aet = (body.get("aet") or "").strip()
    ui = (body.get("ui") or "").strip()
    ui_suffix_in = body.get("uiSuffix")
    visualizador_host = (body.get("visualizador_host") or "").strip().rstrip("/")
    auth_host = (body.get("auth_host") or "").strip().rstrip("/")
    client_id = (body.get("clientId") or PACS_CLIENT).strip()
    client_secret = (body.get("clientSecret") or PACS_SECRET).strip()
    uso_id_dni = body.get("usoIdDNI", True)
    allow_ui_conflict = bool(body.get("allowUiConflict", False))

    missing = [
        name
        for name, val in [
            ("organizacionId", org_id),
            ("conceptoId", concepto_id),
            ("modalidad", modalidad),
            ("host", host),
            ("aet", aet),
        ]
        if not val
    ]
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Faltan campos: {', '.join(missing)}"
        )

    try:
        org = coll(ORG_COLLECTION).find_one({"_id": ObjectId(org_id)})
        concepto = coll(PRESTACIONES_COLLECTION).find_one(
            {"_id": ObjectId(concepto_id)}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"IDs inválidos: {e}") from e

    if not org:
        raise HTTPException(status_code=404, detail="Organización no encontrada")
    if not concepto:
        raise HTTPException(status_code=404, detail="Concepto turneable no encontrado")

    if not visualizador_host or not auth_host:
        suggested = suggest_hosts(host)
        visualizador_host = visualizador_host or suggested["visualizador_host"]
        auth_host = auth_host or suggested["auth_host"]

    # Resolver UI: sufijo explícito → ui completo → sugerencia por org / siguiente
    registry = build_ui_registry()
    ui_warnings: list[str] = []
    ui_reason = "provided"

    if ui_suffix_in is not None and str(ui_suffix_in).strip() != "":
        suffix = int(ui_suffix_in)
        ui = make_ui(suffix)
        ui_reason = "suffix"
    elif ui:
        suffix = ui_suffix(ui)
        if suffix is None:
            raise HTTPException(status_code=400, detail=f"UI OID inválido: {ui}")
        ui_reason = "ui"
    else:
        org_match = next((o for o in registry["byOrg"] if o["id"] == str(org_id)), None)
        if org_match and org_match["suffixes"]:
            suffix = org_match["suffixes"][0]
            ui = make_ui(suffix)
            ui_reason = "reuse_org"
            if len(org_match["suffixes"]) > 1:
                ui_warnings.append(
                    f"Org con varios sufijos {org_match['suffixes']}; se usa {suffix}."
                )
        else:
            suffix = registry["nextSuffix"]
            ui = make_ui(suffix)
            ui_reason = "next_consecutive"

    # Validar unicidad por organización
    taken = next((a for a in registry["assignments"] if a["suffix"] == suffix), None)
    if taken:
        other_orgs = [o for o in taken["organizaciones"] if o["id"] != str(org_id)]
        if other_orgs and not allow_ui_conflict:
            names = ", ".join(o["nombre"] for o in other_orgs)
            raise HTTPException(
                status_code=409,
                detail=(
                    f"UI {suffix} ya usado por otra org: {names}. "
                    f"Próximo libre: {registry['nextSuffix']}."
                ),
            )
        if other_orgs and allow_ui_conflict:
            ui_warnings.append(
                f"CONFLICTO: UI {suffix} también usado por: "
                + ", ".join(o["nombre"] for o in other_orgs)
            )

    tipo_prestacion = {
        "_id": concepto["_id"],
        "fsn": concepto.get("fsn"),
        "semanticTag": concepto.get("semanticTag"),
        "conceptId": concepto.get("conceptId"),
        "term": concepto.get("term"),
        "nombre": concepto.get("term"),
    }

    doc: dict[str, Any] = {
        "organizacion": {
            "id": org["_id"],
            "nombre": org.get("nombre"),
        },
        "ui": ui,
        "tipoPrestacion": [tipo_prestacion],
        "modalidad": modalidad,
        "host": host,
        "aet": aet,
        "visualizador_host": visualizador_host,
        "auth": {
            "clientId": client_id,
            "clientSecret": client_secret,
            "host": auth_host,
        },
        "featureFlags": {
            "usoIdDNI": bool(uso_id_dni),
        },
    }

    mongosh = _to_mongosh(doc)

    payload = {
        "document": doc,
        "mongosh": mongosh,
        "ui": {
            "suffix": suffix,
            "oid": ui,
            "reason": ui_reason,
            "nextFree": registry["nextSuffix"],
        },
        "warnings": ui_warnings,
        "hint": "Read-only: copiá 'document' (Extended JSON / Compass) o 'mongosh' e insertá manualmente.",
    }
    return Response(
        content=dumps(payload, json_options=RELAXED_JSON_OPTIONS, indent=2),
        media_type="application/json",
    )


def _to_mongosh(doc: dict) -> str:
    """Representación aproximada estilo mongosh para pegar en el shell."""
    import json

    def walk(value: Any, indent: int = 0) -> str:
        pad = "  " * indent
        pad1 = "  " * (indent + 1)
        if isinstance(value, ObjectId):
            return f'ObjectId("{value}")'
        if isinstance(value, dict):
            if not value:
                return "{}"
            lines = ["{"]
            items = list(value.items())
            for i, (k, v) in enumerate(items):
                comma = "," if i < len(items) - 1 else ""
                lines.append(f'{pad1}"{k}" : {walk(v, indent + 1)}{comma}')
            lines.append(f"{pad}}}")
            return "\n".join(lines)
        if isinstance(value, list):
            if not value:
                return "[]"
            lines = ["["]
            for i, item in enumerate(value):
                comma = "," if i < len(value) - 1 else ""
                lines.append(f"{pad1}{walk(item, indent + 1)}{comma}")
            lines.append(f"{pad}]")
            return "\n".join(lines)
        return json.dumps(value, ensure_ascii=False)

    return walk(doc)
