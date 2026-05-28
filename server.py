from mcp.server.fastmcp import FastMCP
import os
from datetime import datetime

mcp = FastMCP("MCP Tools Server")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE_DIR, "documents")


@mcp.tool()
def search_and_read(mot_cle: str) -> str:
    if not os.path.exists(DOCS):
        return f"Dossier introuvable: {DOCS}"

    for f in os.listdir(DOCS):
        if mot_cle.lower() in f.lower():
            path = os.path.join(DOCS, f)
            with open(path, "r", encoding="utf-8") as file:
                return file.read()

    return "Document introuvable"


@mcp.tool()
def list_documents() -> list:
    if not os.path.exists(DOCS):
        return []
    return os.listdir(DOCS)


@mcp.tool()
def get_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    print("MCP Server actif...")
    mcp.run()
