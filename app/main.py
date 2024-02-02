from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Form, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import get_session
from sqlalchemy import text
import pandas as pd
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# define the app, an instance of the Fastapi() class
app = FastAPI()
# mount the static folder to be used by fastapi
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# define the templates dir
templates = Jinja2Templates(directory="app/templates")
# read the csv of medicines to access in different routs
df = pd.read_csv(r"./app/medicine.csv")
drugs_dict = {}


# define the root route, that returns the index.html
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# receive post reqs from mobile app
@app.post("/api/receive")
async def receive(request: Request, session: AsyncSession = Depends(get_session)):
    try:
        data = await request.json()
        #logger.info(f"Received data: {data}")
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
    except Exception as e:
        #logger.error(f"Data processing error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Bad request: Error processing data")

    query = text("""
    INSERT IGNORE INTO MI_BAND_ACTIVITY_SAMPLE (USER_ID, TIMESTAMP, HEART_RATE, STEPS)
    VALUES (:USER_ID, :TIMESTAMP, :HEART_RATE, :STEPS);
    """)

    try:
        async with session.begin():  # Begin a transaction:
            for record in records:
                await session.execute(query, params=record)
        await session.commit()  # Ensure to commit the transaction
    except Exception as e:
        #logger.error(f"Database operation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the data: {str(e)}",
        )


@app.post("/api/drug_search", response_class=HTMLResponse)
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
