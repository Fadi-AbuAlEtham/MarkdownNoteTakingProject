from datetime import date, datetime
from typing import Optional, Annotated
from pydantic import BaseModel, Field, EmailStr, field_validator, StringConstraints as S
from pydantic.config import ConfigDict

Username = Annotated[str, S(min_length=3, max_length=32)]
Phone = Annotated[str, S(min_length=6, max_length=25)]
Password = Annotated[
    str,
    S(
        min_length=8,
        pattern=r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$",
    ),
]


class UserBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Annotated[Username, Field(description="This is the username.")]
    email: Annotated[EmailStr, Field(description="This is the user email.")]
    dob: Annotated[date, Field(description="This is the date of birth.")]
    phone_number: Optional[
        Annotated[Phone, Field(description="This is the phone number")]
    ] = None

    @field_validator("dob")
    def dob_not_in_future(cls, v: date) -> date:
        from datetime import date as d

        if v > d.today():
            raise ValueError("dob cannot be in the future")
        return v


class CreateUser(UserBase):
    password: Annotated[Password, Field(description="Plain password, will be hashed.")]


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Optional[Username] = None
    email: Optional[EmailStr] = None
    password: Optional[Password] = None
    dob: Optional[date] = None
    phone_number: Optional[Phone] = None
