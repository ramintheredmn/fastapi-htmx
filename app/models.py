from fastapi import FastAPI
from typing import Any
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
from pydantic import BaseModel, validator
import datetime
from persiantools.jdatetime import JalaliDate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# define the app, an instance of the Fastapi() class
app = FastAPI(docs_url=None, redoc_url=None)
# mount the static folder to be used by fastapi
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# define the templates dir
templates = Jinja2Templates(directory="app/templates")
# The user registrition form


# custom exception

class lessValueError(Exception):
    pass
class sameValueError(Exception):
    pass



class RegistrationForm(BaseModel):
    username: str
    password: str
    sex: int
    name: str
    lastname: str
    birthdate: Any
    height: int
    weight: int
    medication: dict | None = None
    comorbitidies: dict | None = None

    # Validator for password length
    @validator('password')
    def password_length(cls, value):
        if len(value) < 8:
            raise lessValueError('Password must be at least 8 characters')
        return value

    # Validator to check if password is equal to username
    @validator('password')
    def password_not_equal_username(cls, value, values, **kwargs):
        if 'user_id' in values and value == values['user_id']:
            raise sameValueError('Password cannot be the same as the username')
        return value
    # convert the shamsi str date to unix timestamp
    @validator('birthdate', pre=True)
    def toTimestam(cls, value):
        list_date: list = [int(i) for i in value.split('/')]
        gdate = JalaliDate(*list_date).to_gregorian()
        date = datetime.datetime(gdate.year, gdate.month, gdate.day)
        return int(date.timestamp())


# sign in validation

class SinginForm(BaseModel): 
    username: str
    password: str



