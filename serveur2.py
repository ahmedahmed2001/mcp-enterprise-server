"""
Serveur MCP Entreprise - Version modulaire plug-and-play
Permet le chargement dynamique d'outils via configuration YAML
"""
from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import logging
import yaml
import importlib
from pathlib import Path
from datetime import datetime
import sys
import inspect



# ═══════════════════════════════════════════════════════════════
# CONFIGURATION DES LOGS
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ahmed/mcp-project/mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MCP-Server")

# ═══════════════════════════════════════════════════════════════
# SERVEUR MCP
# ═══════════════════════════════════════════════════════════════

mcp = FastMCP("serveur-mcp-entreprise")

# Variables globales
TOOLS_LOADED = []
TOOLS_CONFIG = {}
SERVER_START_TIME = datetime.now()

# ═══════════════════════════════════════════════════════════════
# CHARGEMENT DE LA CONFIGURATION
# ═══════════════════════════════════════════════════════════════

def load_config():
    """Charge la configuration des outils depuis YAML"""
    config_path = Path(__file__).parent / "config" / "tools_config.yaml"
    
    if not config_path.exists():
        logger.error(f"Fichier de configuration introuvable : {config_path}")
        sys.exit(1)
    
    logger.info(f" Chargement de la configuration : {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('tools', {})
    except Exception as e:
        logger.error(f" Erreur lors du chargement de la config : {e}")
        sys.exit(1)

def validate_tool_config(tool_name, config):
    """Valide qu'une configuration d'outil est correcte"""
    required_fields = ['module', 'functions']
    
    for field in required_fields:
        if field not in config:
            logger.error(f" Outil '{tool_name}' : champ '{field}' manquant")
            return False
    
    if not isinstance(config['functions'], list):
        logger.error(f" Outil '{tool_name}' : 'functions' doit être une liste")
        return False
    
    return True

# ═══════════════════════════════════════════════════════════════
# CHARGEMENT DYNAMIQUE DES OUTILS
# ═══════════════════════════════════════════════════════════════

def register_tools():
    """Enregistre tous les outils actifs depuis la configuration"""
    global TOOLS_LOADED, TOOLS_CONFIG
    
    TOOLS_CONFIG = load_config()
    total_registered = 0
    errors = []
    
    logger.info("="*60)
    logger.info(" CHARGEMENT DES OUTILS MCP")
    logger.info("="*60)
    
    for tool_name, config in TOOLS_CONFIG.items():
        # Vérifier si l'outil est activé
        if not config.get('enabled', False):
            logger.info(f"  Outil '{tool_name}' : DÉSACTIVÉ (enabled=false)")
            continue
        
        # Valider la configuration
        if not validate_tool_config(tool_name, config):
            errors.append(f"Configuration invalide pour '{tool_name}'")
            continue
        
        module_name = config.get('module')
        functions = config.get('functions', [])
        description = config.get('description', 'Pas de description')
        
        logger.info(f"\n Outil : {tool_name}")
        logger.info(f"   Module : {module_name}")
        logger.info(f"   Description : {description}")
        logger.info(f"   Fonctions : {len(functions)}")
        
        try:
            # Import dynamique du module
            module = importlib.import_module(module_name)
            
            # Enregistrement de chaque fonction comme outil MCP
            for func_name in functions:
                if hasattr(module, func_name):
                    func = getattr(module, func_name)
                    mcp.tool()(func)
                    total_registered += 1
                    
                    TOOLS_LOADED.append({
                        'tool_name': tool_name,
                        'function_name': func_name,
                        'module': module_name,
                        'description': func.__doc__ or "Pas de description"
                    })
                    
                    logger.info(f"    {func_name}")
                else:
                    error_msg = f"Fonction '{func_name}' introuvable dans {module_name}"
                    logger.warning(f"   ⚠️ {error_msg}")
                    errors.append(error_msg)
        
        except Exception as e:
            error_msg = f"Erreur lors du chargement de '{module_name}': {e}"
            logger.error(f"    {error_msg}")
            errors.append(error_msg)
    
    logger.info("="*60)
    logger.info(f" Total d'outils enregistrés : {total_registered}")
    
    if errors:
        logger.warning(f"  {len(errors)} erreur(s) rencontrée(s) :")
        for error in errors:
            logger.warning(f"   - {error}")
    
    logger.info("="*60)
    
    return total_registered, errors

# ═══════════════════════════════════════════════════════════════
# ENDPOINTS ENTREPRISE
# ═══════════════════════════════════════════════════════════════

# Créer une app FastAPI pour les endpoints de monitoring
app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint pour monitoring"""
    uptime = (datetime.now() - SERVER_START_TIME).total_seconds()
    
    return JSONResponse({
        "status": "healthy",
        "server": "MCP Enterprise Server",
        "uptime_seconds": uptime,
        "tools_loaded": len(TOOLS_LOADED),
        "timestamp": datetime.now().isoformat()
    })

@app.get("/tools")
async def list_tools():
    """Liste tous les outils disponibles"""
    tools_by_category = {}
    
    for tool in TOOLS_LOADED:
        category = tool['tool_name']
        if category not in tools_by_category:
            tools_by_category[category] = {
                'module': tool['module'],
                'functions': []
            }
        
        tools_by_category[category]['functions'].append({
            'name': tool['function_name'],
            'description': tool['description']
        })
    
    return JSONResponse({
        "total_tools": len(TOOLS_LOADED),
        "categories": len(tools_by_category),
        "tools": tools_by_category,
        "timestamp": datetime.now().isoformat()
    })

@app.get("/config")
async def get_config():
    """Retourne la configuration actuelle"""
    active_tools = {k: v for k, v in TOOLS_CONFIG.items() if v.get('enabled')}
    
    return JSONResponse({
        "active_tools": len(active_tools),
        "config": active_tools,
        "timestamp": datetime.now().isoformat()
    })

@app.get("/")
async def root():
    """Page d'accueil du serveur"""
    return JSONResponse({
        "message": "Serveur MCP Entreprise",
        "version": "2.0",
        "endpoints": {
            "health": "/health",
            "tools": "/tools",
            "config": "/config",
            "mcp": "/mcp (protocole MCP)"
        }
    })
@app.get("/tools/llm-format")
async def get_tools_for_llm():
    """Retourne les outils au format attendu par les LLMs (OpenAI/Groq)"""
    tools_for_llm = []
    
    for tool in TOOLS_LOADED:
        # Récupérer la fonction pour extraire sa signature
        try:
            module = importlib.import_module(tool['module'])
            func = getattr(module, tool['function_name'])
            
            # Extraire les paramètres de la fonction
            import inspect
            sig = inspect.signature(func)
            params = {}
            required_params = []
            
            for param_name, param in sig.parameters.items():
                if param_name == 'return':
                    continue
                
                # Déterminer le type
                param_type = "string"  # Par défaut
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == float:
                        param_type = "number"
                    elif param.annotation == bool:
                        param_type = "boolean"
                
                params[param_name] = {
                    "type": param_type,
                    "description": f"Paramètre {param_name}"
                }
                
                # Si pas de valeur par défaut, c'est requis
                if param.default == inspect.Parameter.empty:
                    required_params.append(param_name)
            
            tool_definition = {
                "type": "function",
                "function": {
                    "name": tool['function_name'],
                    "description": tool['description'].strip(),
                    "parameters": {
                        "type": "object",
                        "properties": params,
                        "required": required_params
                    }
                }
            }
            
            tools_for_llm.append(tool_definition)
        
        except Exception as e:
            logger.error(f" Erreur lors de la génération du schéma pour {tool['function_name']}: {e}")
            continue
    
    return JSONResponse({
        "tools": tools_for_llm,
        "count": len(tools_for_llm),
        "timestamp": datetime.now().isoformat()
    })
    
@app.post("/github-webhook")
async def github_webhook(payload: dict):
    """
    Endpoint appelé par GitHub Actions
    Analyse un repo et retourne des recommandations
    """
    logger.info("🎣 Webhook GitHub reçu")
    
    repo_name = payload.get("repository")
    action = payload.get("action", "analyze")
    
    if not repo_name:
        return JSONResponse({
            "error": "repository name required",
            "example": {"repository": "mon-repo", "action": "analyze"}
        }, status_code=400)
    
    logger.info(f"📊 Analyse demandée pour : {repo_name}")
    
    try:
        # Importer la fonction depuis github_advanced_tools
        from tools.github_tools import deep_scan_repo, generate_readme
        
        # Faire l'analyse
        scan_result = deep_scan_repo(repo_name)
        
        # Vérifier si README manque
        issues = scan_result.get("issues", [])
        readme_missing = any("README" in issue.get("message", "") for issue in issues)
        
        response_data = {
            "repository": repo_name,
            "scan_result": scan_result,
            "readme_missing": readme_missing,
            "actions_recommended": []
        }
        
        if readme_missing:
            response_data["actions_recommended"].append({
                "action": "generate_readme",
                "reason": "README.md is missing",
                "severity": "high"
            })
        
        logger.info(f"✅ Analyse terminée : {len(response_data['actions_recommended'])} actions recommandées")
        
        return JSONResponse(response_data)
    
    except Exception as e:
        logger.error(f"❌ Erreur webhook : {e}")
        return JSONResponse({
            "error": str(e),
            "repository": repo_name
        }, status_code=500)
    
# ═══════════════════════════════════════════════════════════════
# DÉMARRAGE DU SERVEUR
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🚀 DÉMARRAGE DU SERVEUR MCP ENTREPRISE")
    logger.info("="*60)
    logger.info(f"📅 Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🐍 Python : {sys.version.split()[0]}")
    logger.info("="*60)
    
    
    # Charger et enregistrer tous les outils
    tools_count, errors = register_tools()
    
    if tools_count == 0:
        logger.error("Aucun outil chargé ! Vérifiez votre configuration.")
        sys.exit(1)
    
    logger.info("\n🌐 Serveurs actifs :")
    logger.info("   - http://0.0.0.0:8001        (Protocole MCP)")
    logger.info("   - http://0.0.0.0:8002/health (Health check)")
    logger.info("   - http://0.0.0.0:8002/tools  (Liste des outils)")
    logger.info("   - http://0.0.0.0:8002/config (Configuration)")
    logger.info("="*60)
    
    # Démarrer le serveur de monitoring en arrière-plan
    import threading
    def run_monitoring():
        uvicorn.run(app, host="0.0.0.0", port=8002, log_level="warning")
    
    monitoring_thread = threading.Thread(target=run_monitoring, daemon=True)
    monitoring_thread.start()
    
    # Démarrer le serveur MCP principal
    uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=8001, log_level="warning")
    

