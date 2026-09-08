"""
P4 — Diagnóstico de calidad de datos (RFC-006 §4/§5).

SOLO LECTURA: no inserta, modifica ni elimina ningún dato.
Reporta la disponibilidad real de datos para calcular las 4 métricas
obligatorias del RFC-006 §5, sin inventar umbrales de suficiencia.

Uso:
    python scripts/validate_data_quality.py
   (o con DATABASE_URL explícita:
    DATABASE_URL="postgresql://..." python scripts/validate_data_quality.py)
"""
import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

TABLES = {
    "predictions": ["knowledge_model_version_id"],
    "operational_events": ["is_incident", "start_timestamp", "end_timestamp"],
    "operational_observations": ["observed_density", "timestamp"],
    "zone_recommendations": ["score", "ranking", "reasoning"],
    "knowledge_model_versions": ["snapshot_hash", "version_number"],
    "zone_behaviors": ["density_factor"],
}

METRIC_TABLES = ("predictions", "operational_events", "operational_observations",
                 "zone_recommendations", "knowledge_model_versions")


def count_rows(conn, table: str) -> int:
    return int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())


def count_rows_where(conn, table: str, where: str) -> int:
    return int(conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {where}")).scalar_one())


def load_counts(engine) -> dict:
    data: dict = {}
    with engine.connect() as conn:
        for table in TABLES:
            entry = {"present": True, "missing_columns": [], "count": None}
            try:
                columns = {col["name"] for col in inspect(engine).get_columns(table)}
                entry["missing_columns"] = [c for c in TABLES[table] if c not in columns]
                entry["count"] = count_rows(conn, table)
            except Exception:
                entry["present"] = False
            data[table] = entry

        if data["predictions"]["present"]:
            data["predictions"]["with_kv"] = count_rows_where(
                conn, "predictions", "knowledge_model_version_id IS NOT NULL"
            )
            data["predictions"]["without_kv"] = (
                data["predictions"]["count"] - data["predictions"]["with_kv"]
            )

        if data["operational_events"]["present"]:
            data["operational_events"]["incidents"] = count_rows_where(
                conn, "operational_events", "is_incident = true"
            )
    return data


def metric_density(data: dict) -> str:
    obs = data["operational_observations"]
    pred = data["predictions"]
    if not obs["present"]:
        return "BLOQUEADA — la tabla operational_observations no existe en la BD."
    if not pred["present"]:
        return "BLOQUEADA — la tabla predictions no existe en la BD."
    if obs["count"] == 0:
        return "BLOQUEADA — 0 observaciones reales de densidad para contrastar"
    if pred["count"] == 0:
        return "BLOQUEADA — no hay predicciones históricas de densidad para contrastar"
    return (
        f"HABILITADA — {obs['count']} observaciones de densidad reales "
        f"para contrastar contra {pred['count']} predicciones"
    )


def metric_incidents(data: dict) -> str:
    events = data["operational_events"]
    if not events["present"]:
        return "LIMITADA — la tabla operational_events no existe en la BD."
    if events["count"] == 0:
        return "LIMITADA — 0 eventos registrados sobre los que calcular la frecuencia"
    if events["incidents"] == 0:
        return f"LIMITADA — solo {events['count']} eventos, 0 incidents reales"
    return (
        f"HABILITADA — {events['count']} eventos con "
        f"{events['incidents']} incidents reales"
    )


def metric_adherence(data: dict) -> str:
    obs = data["operational_observations"]
    behaviors = data["zone_behaviors"]
    if not obs["present"]:
        return "BLOQUEADA — requiere la tabla operational_observations (ausente)."
    if not behaviors["present"]:
        return "BLOQUEADA — requiere la tabla zone_behaviors (ausente)."
    if obs["count"] == 0:
        return "BLOQUEADA — requiere operational_observations (actualmente 0 registros)."
    if behaviors["count"] == 0:
        return "BLOQUEADA — requiere reference en zone_behaviors (actualmente 0 registros)."
    return (
        f"HABILITADA — {obs['count']} observaciones para contrastar contra "
        f"{behaviors['count']} ZoneBehavior de referencia"
    )


def build_report(data: dict) -> str:
    lines = ["=== DATA QUALITY REPORT (RFC-006 §4) ===", ""]
    lines.append("[1] HISTORICAL SOURCES")

    pred = data["predictions"]
    if pred["present"]:
        lines.append(
            f"- predictions: {pred['count']} registros. "
            f"({pred['with_kv']} con versión, {pred['without_kv']} sin versión)."
        )
    else:
        lines.append("- predictions: tabla ausente.")

    events = data["operational_events"]
    if events["present"]:
        lines.append(
            f"- operational_events: {events['count']} registros. "
            f"({events['incidents']} con is_incident=true)."
        )
    else:
        lines.append("- operational_events: tabla ausente.")

    for table in ("operational_observations", "zone_recommendations", "knowledge_model_versions"):
        entry = data[table]
        if entry["present"]:
            lines.append(f"- {table}: {entry['count']} registros.")
        else:
            lines.append(f"- {table}: tabla ausente.")

    lines.append("")
    lines.append("[2] METRICS READINESS (RFC-006 §5)")
    lines.append(f"- Desviación de Densidad: {metric_density(data)}")
    lines.append(f"- Frecuencia de Incidents: {metric_incidents(data)}")
    lines.append(
        "- Latencia de Transición de Fases: BLOQUEADA — no existe actualmente "
        "una fuente de observación de transición de fase definida. "
        "No se modifica operational_events en esta fase."
    )
    lines.append(f"- Adherencia a ZoneBehavior: {metric_adherence(data)}")

    lines.append("")
    lines.append("[3] RECOMMENDATIONS")

    recommendations: list[str] = []
    if data["operational_observations"]["present"] and data["operational_observations"]["count"] == 0:
        recommendations.append(
            "Ingestar operational_observations vía API POST para habilitar "
            "Desviación de Densidad y Adherencia a ZoneBehavior."
        )
    if data["predictions"]["present"] and data["predictions"]["with_kv"] == 0:
        recommendations.append(
            "Emitir nuevas predicciones por el flujo vivo para que queden vinculadas "
            "a knowledge_model_versions (las históricas quedan sin versión, correcto)."
        )
    if data["operational_events"]["present"] and data["operational_events"]["incidents"] == 0:
        recommendations.append(
            "Registrar operational_events con is_incident=true para dar señales reales "
            "a Frecuencia de Incidents."
        )
    recommendations.append(
        "Definir en una fase futura una fuente de observación de transición de fase "
        "(p. ej. a partir de start_timestamp/end_timestamp) para desbloquear "
        "Latencia de Transición de Fases."
    )

    lines.extend(f"- {rec}" for rec in recommendations[:3])
    return "\n".join(lines)


def main() -> None:
    database_url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        data = load_counts(engine)
        for table in METRIC_TABLES:
            missing = data[table]["missing_columns"]
            if missing:
                print(
                    f"[aviso] columnas requeridas ausentes en {table}: {missing}",
                    file=sys.stderr,
                )
        print(build_report(data))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()