from fastapi import FastAPI
import os
from datetime import datetime

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE_DIR, "documents")


@app.get("/")
def home():
    return {"message": "MCP HTTP Server actif"}


@app.get("/list_documents")
def list_documents():
    if not os.path.exists(DOCS):
        return {"error": "Dossier introuvable"}

    return {"documents": os.listdir(DOCS)}


@app.get("/search_and_read")
def search_and_read(mot_cle: str):
    if not os.path.exists(DOCS):
        return {"error": "Dossier introuvable"}

    for f in os.listdir(DOCS):
        if mot_cle.lower() in f.lower():
            path = os.path.join(DOCS, f)

            with open(path, "r", encoding="utf-8") as file:
                return {"content": file.read()}

    return {"error": "Document introuvable"}


@app.get("/get_time")
def get_time():
    return {"time": datetime.now().strftime("%H:%M:%S")}
