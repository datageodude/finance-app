import uuid

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str

    model_config = {"from_attributes": True}
