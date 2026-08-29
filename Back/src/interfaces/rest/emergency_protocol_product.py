"""Adapter puro de protocolos de emergencia (Emergencia V2 - S2).

Funciones determinísticas y testeadas sin dependencia de I/O: filtran y ordenan
la lista de ``EmergencyProtocol`` cargada por el endpoint. La resolución de
recursos (``target_type`` → ``emergencies``) NO está implementada (Fase S3).
"""
from __future__ import annotations

from app.models.emergency_protocol import EmergencyProtocol, EmergencyProtocolContext


def filter_protocols(
    protocols: list[EmergencyProtocol],
    context: EmergencyProtocolContext,
    active_only: bool = True,
) -> list[EmergencyProtocol]:
    """Filtra protocolos por contexto y estado activo."""
    result = [p for p in protocols if p.context == context]
    if active_only:
        result = [p for p in result if p.active]
    return result


def sort_protocols(protocols: list[EmergencyProtocol]) -> list[EmergencyProtocol]:
    """Orden determinístico: priority ASC, order ASC, id ASC."""
    return sorted(protocols, key=lambda p: (p.priority, p.order, p.id))