"""Pydantic schemas for Appointments."""

from datetime import datetime, date, time
from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.appointment import AppointmentStatus


class AvailabilityConfigUpdate(BaseModel):
    """Schema for updating business availability configuration."""
    working_days: Optional[list[str]] = None  # ["mon", "tue", "wed", "thu", "fri"]
    working_hours_start: Optional[str] = None  # "08:00"
    working_hours_end: Optional[str] = None  # "18:00"
    appointment_duration_minutes: Optional[int] = None  # 60
    break_start: Optional[str] = None  # "12:00"
    break_end: Optional[str] = None  # "13:00"
    timezone: Optional[str] = None  # "America/New_York"
    notifications_enabled: Optional[bool] = None


class AvailabilityConfigOut(BaseModel):
    """Schema for returning availability configuration."""
    working_days: Optional[list[str]] = None
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None
    appointment_duration_minutes: Optional[int] = None
    break_start: Optional[str] = None
    break_end: Optional[str] = None
    timezone: Optional[str] = None
    notifications_enabled: Optional[bool] = None

    class Config:
        from_attributes = True


class AppointmentCreate(BaseModel):
    """Schema for creating an appointment."""
    business_id: UUID
    customer_name: str
    customer_phone: str
    customer_email: Optional[EmailStr] = None
    service_needed: str
    appointment_date: date
    appointment_time: time
    duration_minutes: int
    notes: Optional[str] = None


class AppointmentOut(BaseModel):
    """Schema for returning appointment details."""
    id: UUID
    business_id: UUID
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    service_needed: str
    appointment_date: date
    appointment_time: time
    duration_minutes: int
    status: AppointmentStatus
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TimeSlot(BaseModel):
    """Schema for available time slots."""
    time: str  # "08:00", "08:30", etc.
    available: bool


class AvailableSlotsResponse(BaseModel):
    """Schema for available slots response."""
    date: date
    slots: list[str]  # ["08:00", "09:00", "10:00"]
