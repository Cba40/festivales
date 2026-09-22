"""Admin endpoints for TransportAlert and OperatorMessage (RFC-ALERTS-MESSAGES-V1)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
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
    _=Depends(verify_token),
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
    db_obj = await get_alert(db, alert_id)
    if not db_obj or db_obj.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TransportAlert not found",
        )
    return db_obj


@router.put("/alerts/{alert_id}", response_model=TransportAlertResponse)
async def update_alert_endpoint(
    event_id: str,
    alert_id: UUID,
    obj_in: TransportAlertUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    try:
        return await update_alert(db, alert_id, obj_in)
    except ValueError as e:
        raise _raise_value(e)


@router.patch("/alerts/{alert_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_alert_endpoint(
    event_id: str,
    alert_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    await deactivate_alert(db, alert_id)


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_endpoint(
    event_id: str,
    alert_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
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
    _=Depends(verify_token),
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
    db_obj = await get_message(db, message_id)
    if not db_obj or db_obj.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperatorMessage not found",
        )
    return db_obj


@router.put("/messages/{message_id}", response_model=OperatorMessageResponse)
async def update_message_endpoint(
    event_id: str,
    message_id: UUID,
    obj_in: OperatorMessageUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    try:
        return await update_message(db, message_id, obj_in)
    except ValueError as e:
        raise _raise_value(e)


@router.patch("/messages/{message_id}/publish", response_model=OperatorMessageResponse)
async def publish_message_endpoint(
    event_id: str,
    message_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await publish_message(db, message_id)


@router.patch("/messages/{message_id}/cancel", response_model=OperatorMessageResponse)
async def cancel_message_endpoint(
    event_id: str,
    message_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await cancel_message(db, message_id)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message_endpoint(
    event_id: str,
    message_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    await delete_message(db, message_id)