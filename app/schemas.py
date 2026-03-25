from pydantic import BaseModel, EmailStr, Field, field_validator

from app.constants import VALID_VEHICLE_TYPES


class SubscribeRequest(BaseModel):
    email: EmailStr
    vehicle_type: str
    desired_number: int = Field(ge=1, le=9999)

    @field_validator("vehicle_type")
    @classmethod
    def validate_vehicle_type(cls, v: str) -> str:
        v = v.strip()
        if v not in VALID_VEHICLE_TYPES:
            raise ValueError(
                f"ประเภทรถไม่ถูกต้อง กรุณาเลือก: {', '.join(sorted(VALID_VEHICLE_TYPES))}"
            )
        return v


class SubscribeResponse(BaseModel):
    message: str
    email: str
    desired_number: int
    vehicle_type: str
