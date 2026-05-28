import json
import httpx
from groq import Groq
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import os
from dotenv import load_dotenv

# ─── CHARGEMENT DES VARIABLES D'ENVIRONNEMENT ────────────────
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MCP_URL = os.getenv("MCP_SERVER_URL")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY manquante dans le fichier .env")
if not MCP_URL:
    raise ValueError("MCP_SERVER_URL manquante dans le fichier .env")

# ─── CONFIGURATION DES LOGS ───────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MCP-Client")

groq_client = Groq(api_key=GROQ_API_KEY)

# ─── SESSION MCP AVEC RETRIES ─────────────────────────────────
@retry(
    stop=stop_after_attempt(3),  # Maximum 3 essais
    wait=wait_exponential(multiplier=1, min=1, max=5),  # Attend 1s, 2s, 4s entre les essais
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException))
)
def create_session():
    logger.info(" Création d'une session MCP...")
    
    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            MCP_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            },
            json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "client-mcp", "version": "1.0"}
                }
            }
        )
        session_id = response.headers.get("mcp-session-id")
        logger.info(f" Session créée : {session_id}")
        return session_id

# ─── APPEL OUTIL MCP AVEC RETRIES ─────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException))
)
def call_tool(session_id, tool_name, arguments={}):
    logger.info(f"Appel de l'outil : {tool_name} avec args={arguments}")
    
    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            MCP_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "mcp-session-id": session_id
            },
            json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments}
            }
        )
        
        for line in response.text.splitlines():
            if line.startswith("data:"):
                data = json.loads(line[5:].strip())
                result = data.get("result", {})
                logger.info(f"Résultat reçu de {tool_name}")
                return result
    return {}

# ─── AGENT IA ─────────────────────────────────────────────────
def process(user_input):
    logger.info(f"💬 Question reçue : '{user_input}'")
    
    try:
        session_id = create_session()
    except Exception as e:
        logger.error(f" Échec création session après 3 tentatives : {e}")
        return "Erreur : impossible de se connecter au serveur MCP"
    
    messages = [
        {
            "role": "system",
            "content": """Tu es un assistant IA connecté à des outils MCP.
RÈGLES :
- Tu DOIS utiliser les tools si nécessaire
- Tu ne dois PAS inventer
- Tu dois être précis
TOOLS : search_and_read, list_documents, get_time"""
        },
        {"role": "user", "content": user_input}
    ]
    
    tools = [
        {"type": "function", "function": {
            "name": "search_and_read",
            "description": "Cherche et lit un document par mot clé",
            "parameters": {"type": "object",
                "properties": {"mot_cle": {"type": "string"}},
                "required": ["mot_cle"]}
        }},
        {"type": "function", "function": {
            "name": "list_documents",
            "description": "Liste les documents disponibles",
            "parameters": {"type": "object", "properties": {}}
        }},
        {"type": "function", "function": {
            "name": "get_time",
            "description": "Retourne l'heure actuelle",
            "parameters": {"type": "object", "properties": {}}
        }},
        
         # Outils GitHub
        {"type": "function", "function": {
            "name": "list_github_repos",
            "description": "Liste les repositories GitHub de l'organisation  ou de l'utilisateur",
            "parameters": {"type": "object", "properties": {}}}},
        
        {"type": "function", "function": {
            "name": "list_github_files",
            "description": "Liste les fichiers d'un repository GitHub",
            "parameters": {"type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Nom du repository"},
                    "path": {"type": "string", "description": "Chemin dans le repo (optionnel, vide pour la racine)"}
                },
                "required": ["repo_name"]}}},
        
        {"type": "function", "function": {
            "name": "read_github_file",
            "description": "Lit le contenu d'un fichier dans un repository GitHub",
            "parameters": {"type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Nom du repository"},
                    "file_path": {"type": "string", "description": "Chemin complet du fichier"}
                },
                "required": ["repo_name", "file_path"]}}}
    ]
    
    logger.info(" Envoi de la question à l'IA (Groq)...")
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    
    message = response.choices[0].message
    
    if message.tool_calls:
        tool_call = message.tool_calls[0]
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        logger.info(f"🤖 L'IA a décidé d'appeler : {tool_name}")
        
        try:
            tool_result = call_tool(session_id, tool_name, arguments)
        except Exception as e:
            logger.error(f" Échec appel outil après 3 tentatives : {e}")
            return "Erreur : l'outil n'a pas pu être appelé"
        
        messages.append(message)
        messages.append({
            "role": "tool",
            "content": json.dumps(tool_result),
            "tool_call_id": tool_call.id
        })
        
        logger.info(" Formulation de la réponse finale...")
        final = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages
        )
        
        final_response = final.choices[0].message.content
        logger.info(f"✅ Réponse finale générée")
        return final_response
    
    logger.info("✅ Réponse directe sans outil")
    return message.content
