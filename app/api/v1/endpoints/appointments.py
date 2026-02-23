"""Appointment booking and availability endpoints."""

from datetime import datetime, date, time, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.database import get_db
from app.models.business import Business
from app.models.user import User
from app.models.appointment import Appointment, AppointmentStatus
from app.core.trial_limits import check_trial_limit_appointments
from app.schemas.appointment import (
    AvailabilityConfigUpdate,
    AvailabilityConfigOut,
    AppointmentCreate,
    AppointmentOut,
    AvailableSlotsResponse,
)
from app.services.email_service import email_service
import os
from twilio.rest import Client
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# AVAILABILITY CONFIG ENDPOINTS
# ============================================================================

@router.put("/business/{business_id}/availability", response_model=AvailabilityConfigOut)
async def update_availability_config(
    business_id: UUID,
    config: AvailabilityConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update availability configuration for a business."""
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Update fields
    update_data = config.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(business, key, value)
    
    business.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(business)
    
    return AvailabilityConfigOut(
        working_days=business.working_days,
        working_hours_start=business.working_hours_start,
        working_hours_end=business.working_hours_end,
        appointment_duration_minutes=business.appointment_duration_minutes,
        break_start=business.break_start,
        break_end=business.break_end,
        timezone=business.timezone,
        notifications_enabled=business.notifications_enabled,
    )


@router.get("/business/{business_id}/availability", response_model=AvailabilityConfigOut)
async def get_availability_config(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get availability configuration for a business."""
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return AvailabilityConfigOut(
        working_days=business.working_days,
        working_hours_start=business.working_hours_start,
        working_hours_end=business.working_hours_end,
        appointment_duration_minutes=business.appointment_duration_minutes,
        break_start=business.break_start,
        break_end=business.break_end,
        timezone=business.timezone,
        notifications_enabled=business.notifications_enabled,
    )


# ============================================================================
# SLOT CALCULATION
# ============================================================================

def time_to_minutes(t: str) -> int:
    """Convert HH:MM string to minutes since midnight."""
    h, m = map(int, t.split(":"))
    return h * 60 + m


def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to HH:MM string."""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


async def calculate_available_slots(
    business: Business,
    target_date: date,
    db: AsyncSession,
) -> list[str]:
    """Calculate available time slots for a given date."""
    
    # Validate configuration
    if not all([
        business.working_days,
        business.working_hours_start,
        business.working_hours_end,
        business.appointment_duration_minutes,
    ]):
        raise HTTPException(
            status_code=400,
            detail="Business availability not configured. Please set working hours first.",
        )
    
    # Check if date is a working day
    weekday_map = {
        0: "mon", 1: "tue", 2: "wed", 3: "thu",
        4: "fri", 5: "sat", 6: "sun",
    }
    weekday = weekday_map[target_date.weekday()]
    
    if weekday not in business.working_days:
        return []  # Not a working day
    
    # Parse times
    start_minutes = time_to_minutes(business.working_hours_start)
    end_minutes = time_to_minutes(business.working_hours_end)
    duration = business.appointment_duration_minutes
    
    break_start_minutes = None
    break_end_minutes = None
    if business.break_start and business.break_end:
        break_start_minutes = time_to_minutes(business.break_start)
        break_end_minutes = time_to_minutes(business.break_end)
    
    # Generate all possible slots
    slots = []
    current = start_minutes
    
    while current + duration <= end_minutes:
        slot_time = minutes_to_time(current)
        
        # Skip slots that overlap with break
        if break_start_minutes and break_end_minutes:
            slot_end = current + duration
            # Check if slot overlaps with break [break_start, break_end)
            overlaps_break = not (slot_end <= break_start_minutes or current >= break_end_minutes)
            if not overlaps_break:
                slots.append(slot_time)
        else:
            slots.append(slot_time)
        
        current += duration
    
    # Fetch existing confirmed appointments for this date
    result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.business_id == business.id,
                Appointment.appointment_date == target_date,
                Appointment.status == AppointmentStatus.CONFIRMED,
            )
        )
    )
    existing_appointments = result.scalars().all()
    
    # Remove slots that overlap with existing appointments
    available_slots = []
    for slot_str in slots:
        slot_minutes = time_to_minutes(slot_str)
        slot_end_minutes = slot_minutes + duration
        
        is_available = True
        for appt in existing_appointments:
            appt_minutes = appt.appointment_time.hour * 60 + appt.appointment_time.minute
            appt_end_minutes = appt_minutes + appt.duration_minutes
            
            # Check overlap
            overlaps = not (slot_end_minutes <= appt_minutes or slot_minutes >= appt_end_minutes)
            if overlaps:
                is_available = False
                break
        
        if is_available:
            available_slots.append(slot_str)
    
    return available_slots


@router.get("/appointments/available-slots", response_model=AvailableSlotsResponse)
async def get_available_slots(
    business_id: UUID = Query(...),
    date: date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Get available appointment slots for a specific date."""
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    slots = await calculate_available_slots(business, date, db)
    
    return AvailableSlotsResponse(date=date, slots=slots)


# ============================================================================
# APPOINTMENT BOOKING
# ============================================================================

async def send_sms_notification(to: str, message: str):
    """Send SMS via Twilio. Best-effort: logs warning if credentials missing."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    
    if not all([account_sid, auth_token, from_number]):
        logger.warning("Twilio credentials not configured. Skipping SMS notification.")
        return
    
    try:
        client = Client(account_sid, auth_token)
        client.messages.create(
            to=to,
            from_=from_number,
            body=message,
        )
        logger.info(f"SMS sent to {to}")
    except Exception as e:
        logger.error(f"Failed to send SMS to {to}: {e}")


@router.post("/appointments/book", response_model=AppointmentOut, status_code=201)
async def book_appointment(
    appointment: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Book a new appointment (with trial limit check)."""
    
    # Fetch business
    result = await db.execute(select(Business).where(Business.id == appointment.business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get the business owner (user) to check trial status
    user_result = await db.execute(
        select(User).where(User.business_id == appointment.business_id)
    )
    user = user_result.scalars().first()
    
    if user:
        # Check trial limits before creating appointment
        await check_trial_limit_appointments(db, appointment.business_id, user)
    
    # Validate that the slot is available
    available_slots = await calculate_available_slots(business, appointment.appointment_date, db)
    
    requested_time = appointment.appointment_time.strftime("%H:%M")
    if requested_time not in available_slots:
        raise HTTPException(
            status_code=409,
            detail=f"Time slot {requested_time} is not available. Available slots: {', '.join(available_slots)}",
        )
    
    # Create appointment
    new_appointment = Appointment(**appointment.model_dump())
    db.add(new_appointment)
    await db.commit()
    await db.refresh(new_appointment)
    
    # Send notifications if enabled
    if business.notifications_enabled:
        # Notify business owner
        owner_message = (
            f"New appointment: {appointment.customer_name} booked {appointment.service_needed} "
            f"on {appointment.appointment_date} at {requested_time}. "
            f"Call: {appointment.customer_phone}"
        )
        await send_sms_notification(business.owner_phone, owner_message)
        
        # Notify customer
        customer_message = (
            f"Your appointment with {business.name} is confirmed for "
            f"{appointment.appointment_date} at {requested_time}."
        )
        await send_sms_notification(appointment.customer_phone, customer_message)
        
        # Send email confirmation to customer if email provided
        if appointment.customer_email:
            try:
                await email_service.send_appointment_confirmation(
                    customer_email=appointment.customer_email,
                    customer_name=appointment.customer_name,
                    business_name=business.name,
                    appointment_date=appointment.appointment_date.strftime("%A, %B %d, %Y"),
                    appointment_time=requested_time,
                    service=appointment.service_needed,
                )
            except Exception as e:
                logger.error(f"Failed to send appointment confirmation email: {e}")
    
    return new_appointment


@router.get("/appointments/", response_model=list[AppointmentOut])
async def list_appointments(
    business_id: UUID = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List appointments for a business, optionally filtered by date range."""
    
    query = select(Appointment).where(Appointment.business_id == business_id)
    
    if start_date:
        query = query.where(Appointment.appointment_date >= start_date)
    if end_date:
        query = query.where(Appointment.appointment_date <= end_date)
    
    query = query.order_by(Appointment.appointment_date, Appointment.appointment_time)
    
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    return appointments


@router.put("/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
async def cancel_appointment(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Cancel an appointment (sets status to cancelled)."""
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Appointment already cancelled")
    
    appointment.status = AppointmentStatus.CANCELLED
    appointment.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(appointment)
    
    return appointment


@router.put("/appointments/{appointment_id}/complete", response_model=AppointmentOut)
async def complete_appointment(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark an appointment as completed."""
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Appointment already completed")
    
    appointment.status = AppointmentStatus.COMPLETED
    appointment.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(appointment)
    
    return appointment
