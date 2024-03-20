from re import template
from uuid import uuid4
from pydantic import ValidationError
from app.drugsearch import df, drugs_dict
from app.models import app, logger, templates, RegistrationForm, SinginForm
from typing import Any, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Form, Request, HTTPException, Depends, APIRouter, Body, status, Cookie
from fastapi.responses import HTMLResponse
from app.config import get_session
from sqlalchemy import text
import pandas as pd

# sessions in-memmory database that will contain session-id and user_id of the user that is signed-in

sessions = {}


# receive post reqs from mobile app
@app.post("/api/receive")
async def receive(request: Request, session: AsyncSession = Depends(get_session)):
    try:
        data = await request.json()
        # logger.info(f"Received data: {data}")
    except Exception as e:
        logger.error(f"JSON parsing error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Bad request: JSON parsing error")

    try:
        df = pd.json_normalize(data, record_path=["HeartRates"], meta=["UserID"])
        df = df.rename(
            columns={
                "TimeStamp": "TIMESTAMP",
                "HeartRate": "HEART_RATE",
                "Steps": "STEPS",
                "UserID": "USER_ID",
            }
        )
        records = df.to_dict("records")

        # each request is from a unique phone so USER_ID is uniqte per request

        # user_id = records[0]["USER_ID"]
    except Exception as e:
        # logger.error(f"Data processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=400, detail=f"Bad request: Error processing data: {str(e)}"
        )

        # text function is to create sql queries :VARIABLE is to define paramets
        # in the execute function we should give params if they are used it the text function input
    # query_check_if_existing_user_in_users_table = text(
    #     """select USER_ID from users where USER_ID = :USER_ID"""
    # )

    query_insert_to_table = text(
        """
    INSERT IGNORE INTO MI_BAND_ACTIVITY_SAMPLE (USER_ID, TIMESTAMP, HEART_RATE, STEPS)
    VALUES (:USER_ID, :TIMESTAMP, :HEART_RATE, :STEPS);
    """
    )
    # query_insert_to_users_if_not_exist = text(
    #     """INSERT INTO users (USER_ID, PASSWORD) VALUES (:USER_ID, :USER_ID)"""
    # )

    try:
        async with session.begin():  # Begin a transaction:
            # Check if the user already exists in the users table
            # existing_user = await session.execute(
            #     query_check_if_existing_user_in_users_table, params={"USER_ID": user_id}
            # )
            # # Insert the user into the users table if it doesn't exist
            # if not existing_user:
            #     await session.execute(
            #         query_insert_to_users_if_not_exist,
            #         params={"USER_ID": user_id, "PASSWORD": user_id},
            #     )
            # Insert the records into the table
            for record in records:
                await session.execute(query_insert_to_table, params=record)
        await session.commit()  # Ensure to commit the transaction
    except Exception as e:
        # logger.error(f"Database operation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the data: {str(e)}",
        )


# define the root route, that returns the index.html
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})




########################################################## LOGIN #########################


# login page defination
@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

async def extract_bulk_user_ids(session: AsyncSession) -> list:
    query = text("select distinct USER_ID from MI_BAND_ACTIVITY_SAMPLE")
    async with session.begin():
        query_result = await session.execute(query)
        bulk_userids = [str(tuple(buid)[0]) for buid in query_result.fetchall()]
        print(bulk_userids, type(bulk_userids[0]))
    return bulk_userids

# the simple authenticaiotn just check for the avaibility of the user in the user
# table if there, compare the password, if same the user is authenticated
# if not return register page


async def AuthenticateuserinDatabase(
    form_data: dict,
    session: AsyncSession = Depends(get_session),
):
    print(form_data, type(form_data))
    username = form_data['username']
    password = form_data['password']


    buids = await extract_bulk_user_ids(session)

    query = text("SELECT ID, USER_ID, PASSWORD FROM users WHERE USER_ID = :username")
    if username in buids:
        print("userid", username)
        async with session.begin():
            query_result = await session.execute(query, params={"username": username})
            user_row = query_result.fetchone()
            print("user_roww", user_row)
            if user_row is None:
                # If user not found in users table, raise an exception
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Basic"},
                )
            user_id, user_username, user_password = user_row
            if password != user_password:
                # If password does not match, raise an exception
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                    headers={"WWW-Authenticate": "Basic"},
                )
            return{'id': user_id, 'username': user_username}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not in the band database",
            headers={"WWW-Authenticate": "Basic"}
        )



def create_session(user_id: str) -> str:
    session_id = str(uuid4())
    sessions[session_id] = user_id
    # print("session_id", session_id)
    return session_id


async def form_data(username: str = Form(...), password: str = Form(...)):
    form_data = SinginForm(username=username, password=password)
    return {"username": form_data.username, "password": form_data.password}



@app.post("/api/login_info")
async def login_info(request: Request, form_data: dict = Depends(form_data), session: AsyncSession = Depends(get_session)):
    user = await AuthenticateuserinDatabase(session=session, form_data=form_data)
    if not user:
        return templates.TemplateResponse("register.html", {"request": request})
        
    session_id = create_session(user["id"])

    return {"message": "Logged in successfully", "session_id": session_id}

@app.get("/users/me")
def getuser(session_id: str = Cookie(default=None)):
    return {"Your username ": sessions[session_id]}



# user form
@app.post("/api/register")
async def register_info(
    password: str = Form(...),
    user_id: str = Form(...),
    session: AsyncSession = Depends(get_session),
    sex: int = Form(...),
    name: str = Form(...),
    lastname: str = Form(...),
    birthdate: int = Form(...),
    height: str = Form(...),
    weight: str = Form(...),
    medication: str | None = Form(None),
    comorbitidies: str | None = Form(None),
):  # username from the login form
    query = text(
        "INSERT INTO users (USER_ID ,PASSWORD, SEX, name, lastname, BIRTHDATE, HEIGHT, WEIGHT, MEDICATIONS, COMORBIDITIES) VALUES (:USER_ID, :PASSWORD, :SEX, :name, :lastname, :BIRTHDATE, :HEIGHT, :WEIGHT, :MEDICATIONS, :COMORBITIDIES)"
    )

    # caling pydantic modal to validate the data

    try:
        form_data = RegistrationForm(
            user_id=user_id,
            password=password,
            sex=sex,
            name=name,
            lastname=lastname,
            birthdate=birthdate,
            height=height,
            weight=weight,
            medication=medication,
            comorbitidies=comorbitidies,
        )
    except ValidationError as e:
        return {"error": str(e)}

    # update the user table with the new data
    async with session.begin():
        await session.execute(
            query,
            params={
                "USER_ID": form_data.user_id,
                "PASSWORD": form_data.password,
                "SEX": form_data.sex,
                "name": form_data.name,
                "lastname": form_data.lastname,
                "BIRTHDATE": form_data.birthdate,
                "HEIGHT": form_data.height,
                "WEIGHT": form_data.weight,
                "MEDICATIONS": form_data.medication,
                "COMORBITIDIES": form_data.comorbitidies,
            },
        )
        await session.commit()
    return {"message ": "registration successful"}


# +---------------+-------------+------+-----+---------+-------+
# | Field         | Type        | Null | Key | Default | Extra |
# +---------------+-------------+------+-----+---------+-------+
# | USER_ID       | varchar(10) | NO   | MUL | NULL    |       |
# | PASSWORD      | varchar(20) | NO   |     | NULL    |       |
# | BIRTHDATE     | varchar(20) | YES  |     | NULL    |       |
# | HEIGHT        | varchar(3)  | YES  |     | NULL    |       |
# | WEIGHT        | varchar(3)  | YES  |     | NULL    |       |
# | MEDICATIONS   | json        | YES  |     | NULL    |       |
# | COMORBIDITIES | json        | YES  |     | NULL    |       |
# | name          | varchar(20) | YES  |     | NULL    |       |
# | lastname      | varchar(20) | YES  |     | NULL    |       |
# | SEX           | int         | YES  |     | NULL    |       |
# +---------------+-------------+------+-----+---------+-------+


# drug activr search
# htmx hits the /api/drug_search when each time a key is pressed and sends the search query
@app.post("/api/drug_search", response_class=HTMLResponse)
# query: str = Form(...) is the query that htmx sends Form tags in the html contains names and herer we can unpack that hashtable like data structure
async def drug_search(request: Request, query: str = Form(...)):
    filtered_df: Any = df[df["Drug Name"].str.contains(query, case=False)]
    drugs = filtered_df["Drug Name"].drop_duplicates().tolist()
    return templates.TemplateResponse(
        "search.html", {"request": request, "options": drugs}
    )


@app.post("/api/search/drugname", response_class=HTMLResponse)
async def drugname(request: Request, drugname: str = Form(...)):
    drugname_filtered_df: Any = df[df["Drug Name"] == str(drugname)]
    salts = drugname_filtered_df["Salt"].drop_duplicates().tolist()
    dosageforms = drugname_filtered_df["Dosage Form"].drop_duplicates().tolist()
    strengths = drugname_filtered_df["Strengh"].drop_duplicates().tolist()
    roas = drugname_filtered_df["Route of Admin"].drop_duplicates().tolist()
    list_data = {
        "salt": salts,
        "dosageform": dosageforms,
        "strength": strengths,
        "roa": roas,
    }
    for key, value in list_data.items():
        if str(value[0]) == "nan":
            value[0] = f"No particular {key} for this drug"
    return templates.TemplateResponse(
        "drugInfo.html",
        {
            "request": request,
            "drugname": drugname,
            "salts": salts,
            "dosageforms": dosageforms,
            "strengths": strengths,
            "roas": roas,
        },
    )


@app.post("/api/search/drugname/druginfo", response_class=HTMLResponse)
async def drugname_salt(
    request: Request,
    drugname: str = Form(...),
    salt: str = Form(...),
    dosageform: str = Form(...),
    strength: str = Form(...),
    roa: str = Form(...),
):
    last = ""
    if "No particular" not in salt:
        last += f", {salt}"
    if "No particular" not in dosageform:
        last += f", {dosageform}"
    if "No particular" not in strength:
        last += f", {strength}"
    if "No particular" not in roa:
        last += f", {roa}"
    drugs_dict[drugname] = last
    total = drugs_dict
    return templates.TemplateResponse(
        "druglist.html", {"request": request, "last": drugname + last, "total": total}
    )
