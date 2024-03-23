from uuid import uuid4
from pydantic import ValidationError
from app.drugsearch import df, drugs_dict
from app.models import app, lessValueError, logger, sameValueError, templates, RegistrationForm, SinginForm
from typing import Any, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Form, Request, HTTPException, Depends, APIRouter, Body, status, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
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


    query_insert_to_table = text(
        """
    INSERT IGNORE INTO MI_BAND_ACTIVITY_SAMPLE (USER_ID, TIMESTAMP, HEART_RATE, STEPS)
    VALUES (:USER_ID, :TIMESTAMP, :HEART_RATE, :STEPS);
    """
    )

    try:
        async with session.begin():  # Begin a transaction:
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
    username = form_data['username']
    password = form_data['password']
    buids = await extract_bulk_user_ids(session)
    query = text("SELECT ID, USER_ID, PASSWORD FROM users WHERE USER_ID = :username")
    if username in buids:
        async with session.begin():
            query_result = await session.execute(query, params={"username": username})
            user_row = query_result.fetchone()
            if user_row is None:
                # If user not found in users table, raise an exception
                return {"id": None, "username": username}
            user_id, user_username, user_password = user_row
            if password != user_password:
                # If password does not match, raise an exception
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="رمز عبور برای این نام کاربری صحیح نیست",
                    headers={"WWW-Authenticate": "Basic"},
                )
            return{'id': user_id, 'username': user_username}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=''' 
  هنوز وارد اپلیکیشن نشده اید ، لطفا بعد از نصب اپلیکیشن و وارد کردن یوزد آیدی از اتصال انیترنت و بولتوث بند و گوشی خود
  اطمینان حاصل کرده وارد شوید تا به صفحه ثبت نام هدایت شوید
            ''',
            headers={"WWW-Authenticate": "Basic"}
        )
# create session id with uuid
def create_session(user_id: str) -> str:
    session_id = str(uuid4())
    sessions[session_id] = user_id
    return session_id

# helper function for login form data 
async def form_data(username: str = Form(...), password: str = Form(...)):
    form_data = SinginForm(username=username, password=password)
    return {"username": form_data.username, "password": form_data.password}

# post route for recevieng post reqs to login and further routing
@app.post("/api/login_info", response_class=HTMLResponse)
async def login_info(response: Response, form_data: dict = Depends(form_data), session: AsyncSession = Depends(get_session)):
    try:
        user = await AuthenticateuserinDatabase(session=session, form_data=form_data)
        print(user)
        if not user["id"]:
            # user[id] = None is the case when the user_id is in the buid, but not in the users table
            # to have a redircet response client-side with htmx 'Hx-Redirect' should be in the header of the response from
            # the server, otherwise the client will behave with as a normal htmx respnse and swap an element with the 
            # coming response
            response = Response(content="موفق", status_code=200)
            response.headers['HX-Redirect'] = f'/register/{user["username"]}'
            return response
            # return RedirectResponse(url="/register/"+ user["username"], status_code=status.HTTP_302_FOUND)
        session_id = create_session(user["id"])
        # Create a response object for setting a cookie
        # response = RedirectResponse(url="/users/" + user["username"], status_code=status.HTTP_302_FOUND)
        # Set the session_id in a cookie
        response = Response(content="موقف", status_code=200)
        response.headers['HX-Redirect'] = f'/users/{user["username"]}'
        response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=3 * 3600)  # httponly=True is recommended for security
        return response
    except HTTPException as e:
        return f'''<p>{e}<p>'''

# route to user dashboard
@app.get("/users/{username}", response_class=HTMLResponse)
def getuser(request: Request, username: str ,session_id: Annotated[str | None, Cookie()]):
    return templates.TemplateResponse("Dashboard.html", {"request": request, "user": {"username": username, "usersession": session_id}})
# logout route
@app.get("/logout", response_class=HTMLResponse)
async def logout(response: Response, session_id: Annotated[str | None, Cookie()]):
    # Delete the session server-side as before
    if session_id and session_id in sessions:
        del sessions[session_id]
    # Clear the session cookie client-side
    response.delete_cookie(key="session_id")
    # return HTML content to swap and elemnt using htmx
    return """<div>با موفقیت خارج شدید. <a href="/login">دوباره وارد شوید</a></div>"""

# user not found
@app.get("/notfound/{username}", response_class=HTMLResponse)
def notfound(username: str, request: Request):
    return templates.TemplateResponse("Notfound.html", {"request": request, "uesername": username})





# register the user that has user_id in the btable
@app.get("/register/{username}", response_class=HTMLResponse)
async def register(request: Request, username: str):
    return templates.TemplateResponse("register.html", {"request": request, "username": username})


# register helper function
async def register_form(password: Annotated[str, Form()],
    username: Annotated[str, Form()],
    sex: Annotated[str, Form()],
    name: Annotated[str, Form()],
    lastname: Annotated[str, Form()],
    birthdate: Annotated[Any, Form()],
    height: Annotated[str, Form()],
    weight: Annotated[str, Form()],
    medication: Annotated[str | None, Form()] = None,
    comorbitidies: Annotated[str | None, Form()] = None,
                        ):
    return {"username": username, "password": password, "sex":sex, "name": name, "lastname": lastname, "birthdate": birthdate, "height": height, "weight": weight, "medication": medication, "comorbitidies": comorbitidies}

# user form
@app.post("/api/register", response_class=HTMLResponse)
async def register_info(
    request: Request,
    session: AsyncSession = Depends(get_session),
    form_data = Depends(register_form)

):  # username from the login form
    query = text(
        "INSERT INTO users (USER_ID ,PASSWORD, SEX, name, lastname, BIRTHDATE, HEIGHT, WEIGHT, MEDICATIONS, COMORBIDITIES) VALUES (:USERNAME, :PASSWORD, :SEX, :name, :lastname, :BIRTHDATE, :HEIGHT, :WEIGHT, :MEDICATIONS, :COMORBITIDIES)"
    )

    # caling pydantic modal to validate the data
    if request:
        print(request)
    try:
        validated_form_data = RegistrationForm(**form_data)
        
    except lessValueError as e:
        return f'''<p>رمز عبور باید حداقل ۸ کاراکتر باشد</p>'''
    except sameValueError as e:
        return f'''<p>رمز عبور نمی‌تواند با نام کاربری برابر باشد</p>'''

    try:
    # update the user table with the new data
        async with session.begin():
            await session.execute(
                query,
                params={
                    "USERNAME": validated_form_data.username,
                    "PASSWORD": validated_form_data.password,
                    "SEX": validated_form_data.sex,
                    "name": validated_form_data.name,
                    "lastname": validated_form_data.lastname,
                    "BIRTHDATE": validated_form_data.birthdate,
                    "HEIGHT": validated_form_data.height,
                    "WEIGHT": validated_form_data.weight,
                    "MEDICATIONS": validated_form_data.medication,
                    "COMORBITIDIES": validated_form_data.comorbitidies,
                },
            )
            await session.commit()
    except Exception as e:
        print("error in db", str(e))
        await session.rollback()
        return f'''<p>{e}</p>'''
    return '''<p>ثبت نام با موقفیت انجام شد</p>
    <a href="/login">لطفا وارد شوید</a>
    '''


# the MySql table

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
