from pydantic import BaseModel, Field, EmailStr


class UserModel(BaseModel):
    first_name: str = Field(..., title="First Name", max_length=150)
    last_name: str = Field(..., title="Last Name", max_length=150)
    email: EmailStr = Field(..., title="Email Address")
    username: str = Field(..., title="Username", max_length=150)
    password: str = Field(..., title="Password")
    check_password: str = Field(..., title="Confirm Password")
    