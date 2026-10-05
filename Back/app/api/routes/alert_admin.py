"""Admin endpoints for TransportAlert and OperatorMessage (RFC-ALERTS-MESSAGES-V1).

Autorización (Fase 4 del RBAC)
-----------------------------
Las **escrituras** (crear / actualizar / desactivar / eliminar alertas y mensajes)
exigen ``require_permission("alerts:write")``. Antes solo pedían ``verify_token``,
que significa "cualquier usuario autenticado": el permiso ``alerts:write`` ya
existía en ``core/permissions.py`` y ya se otorgaba a los roles, pero ninguna
ruta lo pedía, así que publicar o borrar un aviso de seguridad al público era
una operación abierta a cualquier cuenta con token válido.

Las **lecturas** (``list_by_event`` y ``get``) siguen con ``verify_token``:
operadores y analistas tienen que poder ver el estado del panel, y no existe un
permiso ``alerts:read`` que las restringa. aggregate_and_scopeNo es que la
información sea pública: es que sigue Requiere token, no permiso.

Ownership por evento (anti-IDOR)
--------------------------------
El path es ``/api/admin/events/{event_id}/alerts/{alert_id}``, así que el
``event_id`` de la URL tiene que|matchar| al recurso. Antes solo lo chequeaba
``get_alert_endpoint``; ``update``, ``deactivate``, ``delete``, ``publish``,
``cancel`` y el ``delete`` de mensajes tomaban el ``alert_id`` del path y
actuaban sobre la fila sin mirar el evento, con lo que un token válido para un
evento alcanzaba para modificar o borrar los avisos de otro. Ahora todas pasan
por ``_scoped_alert`` / ``_scoped_message``, que devuelven 404 si el recurso no
pertenece al evento de la URL.

El 404 (y no el 403) es deliberado: no confirma la existencia del recurso ajeno.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission, verify_token
from app.crud.operator_message import (
    cancel as cancel_message,
    create as create_message,
    delete as delete_message,
    get as get_message,
    list_by_event as list_messages,
    publish as publish_message,
    update as update_message,
)
from app.crud.transport_alert import (
    create as create_alert,
    deactivate as deactivate_alert,
    delete as delete_alert,
    get as get_alert,
    list_by_event as list_alerts,
    update as update_alert,
)
from app.db.session import get_async_db
from app.models.operator_message import OperatorMessage
from app.models.transport_alert import TransportAlert
from app.schemas.operator_message import (
    OperatorMessageCreate,
    OperatorMessageResponse,
    OperatorMessageUpdate,
)
from app.schemas.transport_alert import (
    TransportAlertCreate,
    TransportAlertResponse,
    TransportAlertUpdate,
)

router = APIRouter(prefix="/api/admin/events/{event_id}", tags=["Alerts & Messages Admin"])


def _raise_value(e: ValueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(e),
    )


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


async def _scoped_alert(
    db: AsyncSession, event_id: str, alert_id: UUID,
) -> TransportAlert:
    """Devuelve la alerta solo si pertenece al evento de la URL; si no, 404.

    El 404 no distingue "no existe" de "existe pero es de otro evento": responder
    403 confirmaría la existencia del recurso ajeno.
    """
    db_obj = await get_alert(db, alert_id)
    if not db_obj or db_obj.event_id != event_id:
        raise _not_found("TransportAlert not found")
    return db_obj


async def _scoped_message(
    db: AsyncSession, event_id: str, message_id: UUID,
) -> OperatorMessage:
    """Ídem que ``_scoped_alert``, para mensajes de operador."""
    db_obj = await get_message(db, message_id)
    if not db_obj or db_obj.event_id != event_id:
        raise _not_found("OperatorMessage not found")
    return db_obj


@router.get("/alerts", response_model=list[TransportAlertResponse])
async def list_alerts_endpoint(
    event_id: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await list_alerts(db, event_id)


@router.post("/alerts", response_model=TransportAlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_endpoint(
    event_id: str,
    obj_in: TransportAlertCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_permission("alerts:write")),
):
    if obj_in.event_id != event_id:
        raise _raise_value(ValueError("event_id in body must match URL path"))
    try:
        return await create_alert(db, obj_in)
    except ValueError as e:
        raise _raise_value(e)


@router.get("/alerts/{alert_id}", response_model=TransportAlertResponse)
async def get_alert_endpoint(
    event_id: str,
    alert_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await _scoped_alert(db, event_id, alert_id)


@router.put("/alerts/{alert_id}", response_model=TransportAlertResponse)
async def update_alert_endpoint(
    event_id: str,
    alert_id: UUID,
    obj_in: TransportAlertUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_permission("alerts:write")),
):
    await _scoped_alert(db, event_id, alert_id)
    try:
        return await update_alert(db, alert_id, obj_in)
    except ValueError as e:
        raise _raise_value(e)


@router.patch("/alerts/{alert_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_alert_endpoint(
    event_id: str,
    alert_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_permission("alerts:write")),
):
    await _scoped_alert(db, event_id, alert_id)
    await deactivate_alert(db, alert_id)


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_endpoint(
    event_id: str,
    alert_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_permission("alerts:write")),
):
    await _scoped_alert(db, event_id, alert_id)
    await delete_alert(db, alert_id)


@router.get("/messages", response_model=list[OperatorMessageResponse])
async def list_messages_endpoint(
    event_id: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await list_messages(db, event_id)


@router.post("/messages", response_model=OperatorMessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message_endpoint(
    event_id: str,
    obj_in: OperatorMessageCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_permission("alerts:write")),
):
    if obj_in.event_id != event_id:
        raise _raise_value(ValueError("event_id in body must match URL path"))
    try:
        return await create_message(db, obj_in)
    except ValueError as e:
        raise _raise_value(e)


@router.get("/messages/{message_id}", response_model=OperatorMessageResponse)
async def get_message_endpoint(
    event_id: str,
    message_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await _scoped_message(db, event_id, message_id)


@router.put("/messages/{message_id}", response_model=OperatorMessageResponse)
async def update_message_endpoint(
    event_id: str,
    message_id: UUID,
    obj_in: OperatorMessageUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_permission("alerts:write")),
):
    await _scoped_message(db, event_id, message_id)
    try:
        return await update_message(db, message_id, obj_in)
    except ValueError as e:
        raise _raise_value(e)


@router.patch("/messages/{message_id}/publish", response_model=OperatorMessageResponse)
async def publish_message_endpoint(
    event_id: str,
    message_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_permission("alerts:write")),
):
    await _scoped_message(db, event_id, message_id)
    return await publish_message(db, message_id)


@router.patch("/messages/{message_id}/cancel", response_model=OperatorMessageResponse)
async def cancel_message_endpoint(
    event_id: str,
    message_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_permission("alerts:write")),
):
    await _scoped_message(db, event_id, message_id)
    return await cancel_message(db, message_id)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message_endpoint(
    event_id: str,
    message_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(require_permission("alerts:write")),
):
    await _scoped_message(db, event_id, message_id)
    await delete_message(db, message_id)