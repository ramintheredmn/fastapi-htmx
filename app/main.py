from uuid import uuid4
from app.drugsearch import df, drugs_dict
from app.models import app, lessValueError, logger, sameValueError, templates, RegistrationForm, SinginForm
from typing import Any, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Body, Form, Header, Request, HTTPException, Depends, status, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from app.config import get_session
from app.charts import make_chart
from sqlalchemy import text
import pandas as pd
import random
# sessions in-memmory database that will contain session-id and user_id of the user that is signed-in

sessions = {}

# in-memmory database ( python dict ) for storing user info
users = {}
                    # "SEX": validated_form_data.sex,
                    # "name": validated_form_data.name,
                    # "lastname": validated_form_data.lastname,
                    # "BIRTHDATE": validated_form_data.birthdate,
                    # "HEIGHT": validated_form_data.height,
                    # "WEIGHT": validated_form_data.weight,
                    # "MEDICATIONS": validated_form_data.medication,
                    # "COMORBITIDIES": validated_form_data.comorbitidies,


async def user_info(session: AsyncSession, username: str):
    async with session.begin():
        query = text("SELECT SEX, name, lastname, BIRTHDATE, HEIGHT, WEIGHT, MEDICATIONS, COMORBIDITIES FROM users WHERE USER_ID = :user_id")
        query_result = await session.execute(query, params={"user_id": username})
        users_list_tuple = [user for user in query_result.fetchall()]
        if users_list_tuple:
            user_info = users_list_tuple[0]
            users[username] = {'sex': user_info[0], 'name': user_info[1], 'lastname': user_info[2], 'birthdate': user_info[3], 'height': user_info[4], 'weight': user_info[5], 'medications': user_info[6], 'comorbidities': user_info[7]}
            return users[username]
        else:
            return None


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
async def read_root(request: Request, session_id: Annotated[str|None, Cookie()] = None):
    username = sessions[session_id] if session_id and session_id in sessions else None
    return templates.TemplateResponse("index.html", {"request": request, "username": username, "session_id": session_id})




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
        session_id = create_session(user["username"])
        await user_info(session=session, username=user["username"])
        # Create a response object for setting a cookie
        # response = RedirectResponse(url="/users/" + user["username"], status_code=status.HTTP_302_FOUND)
        # Set the session_id in a cookie
        response = Response(content="موقف", status_code=200)
        response.headers['HX-Redirect'] = '/users/me'
        response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=3 * 3600)
        response.set_cookie(key="username", value=user["username"], httponly=True, max_age=3 * 3600)
        
        return response
    except HTTPException as e:
        return f'''<p>{e}<p>'''

# route to user dashboard
@app.get("/users/me", response_class=HTMLResponse)
def getuser(request: Request, username: Annotated[str | None, Cookie()] = None, session_id: Annotated[str | None, Cookie()] = None):
    if not session_id  or session_id not in sessions:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    user = users[username]
    return templates.TemplateResponse("Dashboard.html", {"request": request, "username": username, "name": user["name"]})
# logout route
@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request,response: Response, session_id: Annotated[str | None, Cookie()]):
    # Delete the session server-side as before
    if not session_id:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)    
    
    if session_id and session_id in sessions:
        del sessions[session_id]
    # Clear the session cookie client-side
    response.delete_cookie(key="session_id")
    response.delete_cookie(key="username")
    response_to = Response(content="موقف", status_code=200)
    response_to.headers['HX-Redirect'] = '/login'
    response_to.delete_cookie(key="session_id")
    response_to.delete_cookie(key="username")

    # return HTML content to swap an elemnt usi
    
    return response_to
# user not found
@app.get("/notfound/{username}", response_class=HTMLResponse)
def notfound(username: str, request: Request):
    return templates.TemplateResponse("Notfound.html", {"request": request, "uesername": username})





# register the user that has user_id in the btable
@app.get("/register/{user}", response_class=HTMLResponse)
async def register(request: Request, user: str):
    randomnumber = random.randint(0, 10000000)
    return templates.TemplateResponse("register.html", {"request": request, "user": user, "randomnumber": randomnumber})


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
@app.post("/api/register/{randomnumber}", response_class=HTMLResponse)
async def register_info(
    request: Request,
    randomnumber: int,
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
    return f'''<p>درخواست شماره {randomnumber} موفق</p>
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
@app.post("/api/{randomnumber}/drug_search", response_class=HTMLResponse)
# query: str = Form(...) is the query that htmx sends Form tags in the html contains names and herer we can unpack that hashtable like data structure
async def drug_search(randomnumber: int, request: Request, query: str = Form(...)):
    filtered_df: Any = df[df["Drug Name"].str.contains(query, case=False)]
    drugs = filtered_df["Drug Name"].drop_duplicates().tolist()
    return templates.TemplateResponse(
        "drugpartial/search.html", {"request": request, "randomnumber": randomnumber ,"options": drugs}
    )


@app.post("/api/{randomnumber}/search/drugname", response_class=HTMLResponse)
async def drugname(request: Request, randomnumber: int,drugname: str = Form(...)):
    if request:
        print(drugname, "type :", type(drugname))
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
            value[0] = None
    print(list_data)

    return templates.TemplateResponse(
        "drugpartial/drugspec.html", {"request": request, "randomnumber": randomnumber,"list_data": list_data, "drugname": drugname}
    )

temp_drugs_per_user = {}
async def totaldrugperuser(randnum:int, druglist: list) -> dict:
    if randnum not in temp_drugs_per_user:
        temp_drugs_per_user[randnum] = []
    temp_drugs_per_user[randnum].append(" ".join(list(filter(lambda x: x is not None, druglist))))
    print(temp_drugs_per_user[randnum][0], "type: ", type(temp_drugs_per_user[randnum][0]))
    

    return temp_drugs_per_user[randnum]
@app.post("/api/{randomnumber}/search/{drugname}", response_class=HTMLResponse)
async def drugname_salt(
    request: Request,
    randomnumber: int,
    drugname: str,
    salt: Annotated[str|None, Form()] = None,
    dosageform: Annotated[str|None, Form()] = None,
    strength: Annotated[str|None, Form()] = None,
    roa: Annotated[str|None, Form()] = None,
):
    drugspec = [drugname, salt, dosageform, strength, roa]
    totaldrugslist = await totaldrugperuser(randomnumber, drugspec)
    print("returning druglist html? ", "\n drugs so far: ", totaldrugslist)
    return templates.TemplateResponse(
        "drugpartial/druglist.html", {"request": request, "randomnumber": randomnumber, "totaldrugslist": totaldrugslist}
    )



####################### CHARTS ####################

@app.get("/api/heartrate", response_class=HTMLResponse)
async def get_chart(hx_request: Annotated[str|None, Header()] ,response: Response, beg: str | None = None, end: str | None = None, session: AsyncSession = Depends(get_session),session_id: Annotated[str | None, Cookie()] = None):


    if not session_id or session_id not in sessions and hx_request:
        response = Response(content="موقف", status_code=200)
        response.headers['HX-Redirect'] = '/login'
        return response
    if not session_id or session_id not in sessions and not hx_request:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    if session_id and session_id in sessions:
        username = sessions[session_id]
        query = text('''
        SELECT DISTINCT TIMESTAMP, HEART_RATE, STEPS
        FROM MI_BAND_ACTIVITY_SAMPLE 
        WHERE USER_ID = :user_id
        AND TIMESTAMP BETWEEN (1706873340 - 86400) and 1706873340;
        ''')
        async with session.begin():
            query_result = await session.execute(query, params={"user_id": username})
            res_table = [res for res in query_result.fetchall()]
            #print(res_table)

        
    #return {"msg": "success"}

        y_data = [x[1] for x in res_table]
        x_data = [int(y[0]) * 1000 for y in res_table]

        # x_data = [x  for x in range(100)]
        # y_data = [randint(1, 50)  for y in range(100)]

        
        return make_chart(x_data=x_data, y_data=y_data)

