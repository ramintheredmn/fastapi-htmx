from app.drugsearch import df, drugs_dict
from app.appstuff import app, logger, templates
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Form, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from app.config import get_session
from sqlalchemy import except_, text
import pandas as pd


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

        user_id = records[0]["USER_ID"]
    except Exception as e:
        # logger.error(f"Data processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=400, detail=f"Bad request: Error processing data: {str(e)}"
        )

        # text function is to create sql queries :VARIABLE is to define paramets
        # in the execute function we should give params if they are used it the text function input
    query_check_if_existing_user_in_users_table = text(
        """select USER_ID from users where USER_ID = :USER_ID"""
    )

    query_insert_to_table = text(
        """
    INSERT IGNORE INTO MI_BAND_ACTIVITY_SAMPLE (USER_ID, TIMESTAMP, HEART_RATE, STEPS)
    VALUES (:USER_ID, :TIMESTAMP, :HEART_RATE, :STEPS);
    """
    )
    query_insert_to_users_if_not_exist = text(
        """INSERT INTO users (USER_ID, PASSWORD) VALUES (:USER_ID, :USER_ID)"""
    )

    try:
        async with session.begin():  # Begin a transaction:
            # Check if the user already exists in the users table
            existing_user = await session.execute(
                query_check_if_existing_user_in_users_table, params={"USER_ID": user_id}
            )
            # Insert the user into the users table if it doesn't exist
            if not existing_user:
                await session.execute(
                    query_insert_to_users_if_not_exist,
                    params={"USER_ID": user_id, "PASSWORD": user_id},
                )
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


# login page defination
@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# the simple authenticaiotn just check for the avaibility of the user in the user
# table if there, compare the password, if same the user is authenticated
# if not return register page
async def userinDatabase(
    username: str, password: str, session: AsyncSession
) -> tuple[bool, bool, int | bool]:
    query = text("select USER_ID, PASSWORD from users")
    async with session.begin():
        query_result = await session.execute(query)
        users_rows = query_result.fetchall()
        users_tuple = [tuple(row) for row in users_rows]
        users_dict = {username: password for username, password in users_tuple}

        # begin the check for user vaibility and user pass equality

        try:
            if username in users_dict and username == users_dict[username]:
                # this means that the user visits the website for the first time
                return True, True, 0
            elif (
                username in users_dict
                and username != users_dict[username]
                and password == users_dict[username]
            ):
                # this means that the user is in the database and has setten a passerd
                return True, True, True
            else:
                return False, False, False
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"یوزد آیدی در دیتابیس وجود ندارد: {str(e)}",
            )


@app.post("/api/login_info")
async def login_info(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    user = await userinDatabase(username, password, session)

    if user == (True, True, True):
        return {"message ": "login successful"}
    if user == (True, True, 0):
        return templates.TemplateResponse(
            "register.html", {"request": request, "username": username}
        )
    if user == (False, False, False):
        return {"message ": "login failed"}


# user form
@app.post("/api/register")
async def register_info(
    password: str = Form(...),
    username: str = Form(...),
    session: AsyncSession = Depends(get_session),
    sex: str = Form(...),
    name: str = Form(...),
    lastname: str = Form(...),
    phone: str = Form(...),
    birthdate: str = Form(...),
    height: str = Form(...),
    weight: str = Form(...),
    medication: str | None = Form(None),
    comorbitidies: str | None = Form(None),
):  # username from the login form
    query = text(
        "UPDATE users (PASSWORD, SEX, name, lastname, PHONE, BIRTHDATE, HEIGHT, WEIGHT, MEDICATIONS, COMORBITIDIES) VALUES (:USER_ID, :PASSWORD, :SEX, :name, :lastname, :PHONE, :BIRTHDATE, :HEIGHT, :WEIGHT, :MEDICATIONS, :COMORBITIDIES) WHERE USER_ID= :USER_ID"
    )
    # update the user table with the new data
    async with session.begin():
        await session.execute(
            query,
            params={
                "USER_ID": username,
                "PASSWORD": password,
                "SEX": sex,
                "name": name,
                "lastname": lastname,
                "PHONE": phone,
                "BIRTHDATE": birthdate,
                "HEIGHT": height,
                "WEIGHT": weight,
                "MEDICATIONS": medication,
                "COMORBITIDIES": comorbitidies,
            },
        )
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
