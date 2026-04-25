import re
from typing import Annotated

from pydantic import BaseModel, Field, EmailStr

def validate_regex(postal_code: str) -> bool:
    pattern = r'^\d{4}\s?[A-Za-z]{2}$'
    return re.match(pattern, postal_code) is not None

PostalCode = Annotated[str, validate_regex]

class UserModel(BaseModel):
    first_name: str = Field(..., title="First Name", max_length=150)
    last_name: str = Field(..., title="Last Name", max_length=150)
    email: EmailStr = Field(..., title="Email Address")
    street: str = Field(..., title="Street", max_length=150)
    house_number: str = Field(..., title="House Number", max_length=10)
    city: str = Field(..., title="City", max_length=150)
    province: str = Field(..., title="Province", max_length=150)
    postal_code: PostalCode = Field(..., title="Postal Code")
    password: str = Field(..., title="Password")
    check_password: str = Field(..., title="Confirm Password")
    