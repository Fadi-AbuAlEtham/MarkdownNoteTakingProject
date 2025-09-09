import re
from datetime import date, datetime
from typing import Optional, Annotated
from pydantic import (
    BaseModel,
    Field,
    EmailStr,
    field_validator,
    StringConstraints as StrConst,
    model_validator,
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
Password = Annotated[str, StrConst(min_length=8)]


class UserBase(BaseModel):
    """
    UserBase class acts as the parent class which contain the essential general attributes.
    """

    model_config = ConfigDict(extra="forbid")

    username: Annotated[Username, Field(description="This is the username.")]
    email: Annotated[EmailStr, Field(description="This is the user email.")]
    dob: Optional[Annotated[date, Field(description="Date of birth")]] = None
    phone_number: Optional[Annotated[Phone, Field(description="Phone number")]] = None

    @field_validator("username", mode="before")
    def norm_username(v: Optional[str]) -> Optional[str]:
        """
        Normalize `username` **before** validation.

        - Trims leading/trailing whitespace.
        - Passes through `None` or non-str values unchanged.

        Args:
            v: Raw username value.

        Returns:
            The normalized username, or `None`.
        """
        return v.strip() if isinstance(v, str) else v

    @field_validator("email", mode="before")
    def norm_email(v: Optional[EmailStr]) -> Optional[str]:
        """
        Normalize `email` **before** validation.

        - Converts to `str`, trims whitespace.
        - Passes through `None` unchanged.

        Args:
            v: Raw email value.

        Returns:
            The normalized email string, or `None`.
        """
        return str(v).strip().lower() if v is not None else v

    @field_validator("dob")
    def dob_not_in_future(current_date: date) -> date:
        """Validate that `dob` is not in the future.

        This Pydantic field validator runs for the `dob` field and ensures the date
        is today or earlier.

        Args:
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
    password that will be hashed later in the insert to DB operation. the purpose of this
    class is to create a new user with a password which doesn't exist in the other classes.
    """

    password: Annotated[Password, Field(description="Plain password, will be hashed.")]

    @field_validator("password")
    def strong_password(cls, v: str) -> str:
        pattern = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$")
        if not pattern.fullmatch(v):
            raise ValueError("Password must be ≥8 chars, include a letter, a digit, and a special (@$!%*?&)")
        return v

class UserResponse(UserBase):
    """
    UserResponse class inherits the UserBase class and added two attributes to display which are the
    user id and the creation date & time in addition to the fields of the UserBase class. The
    purpose of this class is to return the needed data in the response of the request made.
    """

    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool


class UpdateUser(BaseModel):
    """
    UpdateUser class contains the attributes that can be modified by the user. It's main purpose
    is to enforce updating certain attributes, not all of them.
    """

    model_config = ConfigDict(extra="forbid")

    username: Optional[Username] = None
    email: Optional[EmailStr] = None
    password: Optional[Password] = None
    dob: Optional[date] = None
    phone_number: Optional[Phone] = None

    @field_validator("username", mode="before")
    def norm_username(v: Optional[str]) -> Optional[str]:
        """
        Normalize `username` **before** validation.

        - Trims leading/trailing whitespace.
        - Passes through `None` or non-str values unchanged.

        Args:
            v: Raw username value.

        Returns:
            The normalized username, or `None`.
        """
        return v.strip() if isinstance(v, str) else v

    @field_validator("email", mode="before")
    def norm_email(v: Optional[EmailStr]) -> Optional[str]:
        """
        Normalize `email` **before** validation.

        - Converts to `str`, trims whitespace.
        - Passes through `None` unchanged.

        Args:
            v: Raw email value.

        Returns:
            The normalized email string, or `None`.
        """
        return str(v).strip().lower() if v is not None else v

    @field_validator("dob")
    def dob_not_in_future(v: Optional[date]) -> Optional[date]:
        """
        Ensure `dob` is not a future date.

        Accepts `None`. If a date is provided, and it is later than today,
        raises a `ValueError`.

        Args:
            v: Candidate date of birth.

        Returns:
            The same date value, if valid (or `None`).

        Raises:
            ValueError: If `v` is later than today's date.
        """
        if v is not None and v > date.today():
            raise ValueError("dob cannot be in the future")
        return v

    @model_validator(mode="after")
    def at_least_one_field(self):
        """
        Enforce that at least one updatable field is provided.

        Checks `username`, `email`, `password`, `dob`, and `phone_number`.
        If all are `None`, raises a `ValueError`.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If no updatable fields are provided.
        """
        if not any(
            getattr(self, f) is not None
            for f in ("username", "email", "password", "dob", "phone_number")
        ):
            raise ValueError("At least one field must be provided for update")
        return self

    @field_validator("password")
    def strong_password(cls, v: str) -> str:
        pattern = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$")
        if not pattern.fullmatch(v):
            raise ValueError("Password must be ≥8 chars, include a letter, a digit, and a special (@$!%*?&)")
        return v