"""
Client MCP dynamique - Découvre automatiquement les outils disponibles
"""
import json
import httpx
from groq import Groq
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")
MONITORING_URL = "http://localhost:8002"  # URL du serveur de monitoring

if not GROQ_API_KEY or not MCP_SERVER_URL:
    raise ValueError(" Variables manquantes dans .env")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MCP-Client-Dynamic")

groq_client = Groq(api_key=GROQ_API_KEY)

# ═══════════════════════════════════════════════════════════════
# DÉCOUVERTE AUTOMATIQUE DES OUTILS
# ═══════════════════════════════════════════════════════════════

def discover_tools():
    """Découvre automatiquement les outils disponibles depuis le serveur"""
    logger.info(" Découverte des outils disponibles...")
    
    try:
        response = httpx.get(f"{MONITORING_URL}/tools/llm-format", timeout=5.0)
        data = response.json()
        tools = data.get('tools', [])
        
        logger.info(f" {len(tools)} outils découverts dynamiquement")
        return tools
    
    except Exception as e:
        logger.error(f" Erreur lors de la découverte des outils : {e}")
        logger.warning(" Utilisation de la liste d'outils par défaut")
        return get_default_tools()

def get_default_tools():
    """Liste d'outils de secours si la découverte échoue"""
    return [
        {"type": "function", "function": {
            "name": "list_documents",
            "description": "Liste les documents locaux",
            "parameters": {"type": "object", "properties": {}}}},
        
        {"type": "function", "function": {
            "name": "get_time",
            "description": "Retourne l'heure actuelle",
            "parameters": {"type": "object", "properties": {}}}}
    ]

# ═══════════════════════════════════════════════════════════════
# SESSION ET APPELS MCP (identique à avant)
# ═══════════════════════════════════════════════════════════════

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5),
       retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)))
def create_session():
    logger.info(" Création session MCP")
    with httpx.Client(timeout=10.0) as client:
        response = client.post(MCP_SERVER_URL, headers={"Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "client-mcp-dynamic", "version": "2.0"}}})
        return response.headers.get("mcp-session-id")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5),
       retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)))
def call_tool(session_id, tool_name, arguments={}):
    logger.info(f" Appel outil : {tool_name}")
    with httpx.Client(timeout=10.0) as client:
        response = client.post(MCP_SERVER_URL, headers={"Content-Type": "application/json",
            "Accept": "application/json, text/event-stream", "mcp-session-id": session_id},
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments}})
        for line in response.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip()).get("result", {})
    return {}

# ═══════════════════════════════════════════════════════════════
# AGENT IA AVEC DÉCOUVERTE DYNAMIQUE
# ═══════════════════════════════════════════════════════════════

def process(user_input):
    logger.info(f" Question : '{user_input}'")
    
    # Découvrir les outils dynamiquement
    tools = discover_tools()
    
    try:
        session_id = create_session()
    except Exception as e:
        logger.error(f"Échec session : {e}")
        return "Erreur : impossible de se connecter"
    
    # Construire le prompt système dynamiquement
    tools_list = "\n".join([f"- {t['function']['name']}: {t['function']['description'][:100]}..." 
                            for t in tools])
    
    system_prompt = f"""Tu es un assistant IA connecté à des outils MCP.

🎯 OUTILS DISPONIBLES :

{tools_list}

📋 RÈGLES :
1. Lis attentivement les descriptions
2. Choisis le BON outil pour la question
3. Utilise TOUJOURS un outil quand possible
4. Si aucun outil ne convient, dis-le"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.1,
        max_tokens=2000
    )
    
    message = response.choices[0].message
    
    if message.tool_calls:
        tool_call = message.tool_calls[0]
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        logger.info(f"IA a choisi : {tool_name}")
        
        try:
            tool_result = call_tool(session_id, tool_name, arguments)
        except Exception as e:
            logger.error(f" Échec outil : {e}")
            return "Erreur : outil inaccessible"
        
        final = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Tu es un assistant IA."},
                      {"role": "user", "content": user_input}, message,
                      {"role": "tool", "content": json.dumps(tool_result),
                       "tool_call_id": tool_call.id}])
        return final.choices[0].message.content
    
    return message.content
