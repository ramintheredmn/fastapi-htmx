from fastapi import FastAPI
from typing import Optional
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import logging
from pydantic import BaseModel, validator


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# define the app, an instance of the Fastapi() class
app = FastAPI()
# mount the static folder to be used by fastapi
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# define the templates dir
templates = Jinja2Templates(directory="app/templates")
# define the hashing algorithm
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# def authenticate_user(username: str, password: str):
#     user = {"username": username, "password": pwd_context.hash("secret")}
#     if pwd_context.verify(password, user["password"]):
#         return user
#     return None
# for now just simple athentication withiot hashing



# HERE the pydantic schemas for validation begins
# The user registrition form

class RegistrationForm(BaseModel):
    user_id: str
    password: str
    sex: int
    name: str
    lastname: str
    birthdate: int
    height: str
    weight: str
    medication: Optional[str] = None
    comorbitidies: Optional[str] = None

    # Validator for password length
    @validator('password')
    def password_length(cls, value):
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters')
        return value

    # Validator to check if password is equal to username
    @validator('password')
    def password_not_equal_username(cls, value, values, **kwargs):
        if 'user_id' in values and value == values['user_id']:
            raise ValueError('Password cannot be the same as the username')
        return value


# sign in validation

class SinginForm(BaseModel): 
    user_id: str
    password: str



