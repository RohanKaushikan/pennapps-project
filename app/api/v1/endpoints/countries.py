from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import get_session
from app.models.country import Country
from app.models.alert import Alert
from app.schemas.country import CountryCreate, CountryResponse, CountryUpdate, CountryWithStats
from app.schemas.common import MessageResponse

router = APIRouter()


@router.get("/", response_model=List[CountryResponse])
async def get_countries(
    skip: int = 0,
    limit: int = 100,
    region: str = None,
    db: AsyncSession = Depends(get_session)
):
    """
    Get all countries with pagination and optional region filtering.
    """
    query = select(Country)

    if region:
        query = query.where(Country.region.ilike(f"%{region}%"))

    result = await db.execute(
        query.offset(skip).limit(limit).order_by(Country.name)
    )
    countries = result.scalars().all()
    return countries


@router.post("/", response_model=CountryResponse, status_code=status.HTTP_201_CREATED)
async def create_country(
    country: CountryCreate,
    db: AsyncSession = Depends(get_session)
):
    """
    Create a new country.
    """
    # Check if country code already exists
    result = await db.execute(
        select(Country).where(Country.code == country.code.upper())
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Country with this code already exists"
        )

    # Create new country
    db_country = Country(
        code=country.code.upper(),
        name=country.name,
        region=country.region
    )
    db.add(db_country)
    await db.commit()
    await db.refresh(db_country)
    return db_country


@router.get("/{country_id}", response_model=CountryResponse)
async def get_country(
    country_id: int,
    db: AsyncSession = Depends(get_session)
):
    """
    Get a specific country by ID.
    """
    result = await db.execute(
        select(Country).where(Country.id == country_id)
    )
    country = result.scalar_one_or_none()

    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found"
        )

    return country


@router.get("/code/{country_code}", response_model=CountryResponse)
async def get_country_by_code(
    country_code: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get a specific country by code.
    """
    result = await db.execute(
        select(Country).where(Country.code == country_code.upper())
    )
    country = result.scalar_one_or_none()

    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found"
        )

    return country


@router.get("/{country_id}/stats", response_model=CountryWithStats)
async def get_country_with_stats(
    country_id: int,
    db: AsyncSession = Depends(get_session)
):
    """
    Get a country with alert statistics.
    """
    # Get country
    result = await db.execute(
        select(Country).where(Country.id == country_id)
    )
    country = result.scalar_one_or_none()

    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found"
        )

    # Get alert statistics
    total_alerts_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.country_id == country_id)
    )
    total_alerts = total_alerts_result.scalar() or 0

    active_alerts_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.country_id == country_id,
            Alert.expires_at > func.now() or Alert.expires_at.is_(None)
        )
    )
    active_alerts = active_alerts_result.scalar() or 0

    high_risk_alerts_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.country_id == country_id,
            Alert.risk_level >= 4,
            Alert.expires_at > func.now() or Alert.expires_at.is_(None)
        )
    )
    high_risk_alerts = high_risk_alerts_result.scalar() or 0

    # Get last alert date
    last_alert_result = await db.execute(
        select(Alert.created_at)
        .where(Alert.country_id == country_id)
        .order_by(Alert.created_at.desc())
        .limit(1)
    )
    last_alert_date = last_alert_result.scalar_one_or_none()

    # Create response with stats
    country_dict = {
        "id": country.id,
        "code": country.code,
        "name": country.name,
        "region": country.region,
        "created_at": country.created_at,
        "updated_at": country.updated_at,
        "total_alerts": total_alerts,
        "active_alerts": active_alerts,
        "high_risk_alerts": high_risk_alerts,
        "last_alert_date": last_alert_date
    }

    return country_dict


@router.put("/{country_id}", response_model=CountryResponse)
async def update_country(
    country_id: int,
    country_update: CountryUpdate,
    db: AsyncSession = Depends(get_session)
):
    """
    Update a specific country.
    """
    result = await db.execute(
        select(Country).where(Country.id == country_id)
    )
    country = result.scalar_one_or_none()

    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found"
        )

    # Update fields
    update_data = country_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "code" and value:
            value = value.upper()
        setattr(country, field, value)

    await db.commit()
    await db.refresh(country)
    return country


@router.delete("/{country_id}", response_model=MessageResponse)
async def delete_country(
    country_id: int,
    db: AsyncSession = Depends(get_session)
):
    """
    Delete a specific country.
    """
    result = await db.execute(
        select(Country).where(Country.id == country_id)
    )
    country = result.scalar_one_or_none()

    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found"
        )

    await db.delete(country)
    await db.commit()

    return MessageResponse(message="Country deleted successfully")