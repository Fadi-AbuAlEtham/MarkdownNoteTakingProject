from datetime import date, datetime
from typing import Optional, Annotated
from pydantic import (
    BaseModel,
    Field,
    EmailStr,
    field_validator,
    StringConstraints as StrConst,
)
from pydantic.config import ConfigDict

"""User schemas

Write:
- CreateUser: accepts a plain `password`; the API/service layer must hash it to `password_hash`.

Update:
- UpdateUser: all fields optional; if `password` provided, rehash and persist.

Read:
- UserResponse: exposes public fields (including `created_at`) and excludes `password_hash`.

Notes:
- Emails validated with EmailStr; usernames may use constrained strings.
- Use `model_config = ConfigDict(from_attributes=True)` to enable ORM model conversion.
"""


# General constraints on username, phone, and password
Username = Annotated[str, StrConst(min_length=3, max_length=32)]
Phone = Annotated[str, StrConst(min_length=6, max_length=25)]
Password = Annotated[
    str,
    StrConst(
        min_length=8,
        pattern=r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$",
    ),
]


class UserBase(BaseModel):
    """
    UserBase class acts as the parent class which contain the essential general attributes.
    """

    model_config = ConfigDict(extra="forbid")

    username: Annotated[Username, Field(description="This is the username.")]
    email: Annotated[EmailStr, Field(description="This is the user email.")]
    dob: Annotated[date, Field(description="This is the date of birth.")]
    phone_number: Optional[
        Annotated[Phone, Field(description="This is the phone number")]
    ] = None

    @field_validator("dob")
    def dob_not_in_future(current_date: date) -> date:
        """Validate that `dob` is not in the future.

        This Pydantic field validator runs for the `dob` field and ensures the date
        is today or earlier.

        Args:
            cls: The model class (provided by Pydantic; unused).
            current_date: The candidate date value for `dob`.

        Returns:
            The validated date.

        Raises:
            ValueError: If `v` is later than today's date.

        Notes:
            - Uses the system local date via `datetime.date.today()`.
            - Today's date is considered valid.
        """

        if current_date > date.today():
            raise ValueError("dob cannot be in the future")
        return current_date


class CreateUser(UserBase):
    """
    CreateUser class inherits the UserBase class and added extra attribute which is the
    password which will be hashed later in the insert to DB operation. the purpose of this
    class is to create new user with password which doesn't exist in the other classes.
    """

    password: Annotated[Password, Field(description="Plain password, will be hashed.")]


class UserResponse(UserBase):
    """
    UserResponse class inherits the UserBase class and added two attributes to display which are the
    user id and the creation date & time in addition to the fields of the UserBase class. The
    purpose of this class is to return the needed data in the response of the request made.
    """

    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class UpdateUser(BaseModel):
    """
    UpdateUser class contains the attributes that can be modified by the user. It's main purpose
    is to enforce updating certain attributes not all of them.
    """

    model_config = ConfigDict(extra="forbid")

    username: Optional[Username] = None
    email: Optional[EmailStr] = None
    password: Optional[Password] = None
    dob: Optional[date] = None
    phone_number: Optional[Phone] = None
