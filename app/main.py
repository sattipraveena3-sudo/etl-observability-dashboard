from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.core import Store,simulate
store=Store(); app=FastAPI(title="ETL Observability Dashboard"); static=Path(__file__).parent/"static"; app.mount("/static",StaticFiles(directory=static),name="static")
@app.get("/")
def home(): return FileResponse(static/"index.html")
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/simulate")
def seed(count:int=24): simulate(store,count); return {"created":count}
@app.get("/runs")
def runs(): return store.rows("runs")
@app.get("/alerts")
def alerts(): return store.rows("alerts")
