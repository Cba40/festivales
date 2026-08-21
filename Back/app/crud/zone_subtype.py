from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.zone_subtype import ZoneSubtype


class ZoneSubtypeCRUD:
    def get(self, db: Session, id: str) -> Optional[ZoneSubtype]:
        return db.get(ZoneSubtype, id)

    def get_by_slug(
        self, db: Session, zone_type_id: str, slug: str
    ) -> Optional[ZoneSubtype]:
        stmt = select(ZoneSubtype).where(
            ZoneSubtype.zone_type_id == zone_type_id,
            ZoneSubtype.slug == slug,
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_multi(
        self,
        db: Session,
        *,
        zone_type_id: Optional[str] = None,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 1000,
    ) -> list[ZoneSubtype]:
        stmt = select(ZoneSubtype)
        if zone_type_id is not None:
            stmt = stmt.where(ZoneSubtype.zone_type_id == zone_type_id)
        if only_active:
            stmt = stmt.where(ZoneSubtype.is_active.is_(True))
        stmt = (
            stmt.order_by(ZoneSubtype.sort_order.asc(), ZoneSubtype.name.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())


zone_subtype = ZoneSubtypeCRUD()
