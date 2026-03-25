from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class VehicleType(str, Enum):
    RY1 = "รย.1"
    RY2 = "รย.2"
    RY3 = "รย.3"


class SubscribeRequest(BaseModel):
    email: EmailStr
    vehicle_type: VehicleType
    desired_number: int = Field(ge=1, le=9999)


class SubscribeResponse(BaseModel):
    message: str
    email: str
    desired_number: int
    vehicle_type: VehicleType
