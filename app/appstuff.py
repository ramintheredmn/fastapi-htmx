from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# define the app, an instance of the Fastapi() class
app = FastAPI()
# mount the static folder to be used by fastapi
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# define the templates dir
templates = Jinja2Templates(directory="app/templates")
# define the hashing algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def authenticate_user(username: str, password: str):
    user = {"username": username, "password": pwd_context.hash("secret")}
    if pwd_context.verify(password, user["password"]):
        return user
    return None
