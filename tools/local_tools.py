"""
Outils pour la gestion des documents locaux
"""
import os
import logging
from datetime import datetime

logger = logging.getLogger("LocalTools")

def get_docs_path():
    """Retourne le chemin du dossier documents"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "documents")

def list_documents() -> dict:
    """Liste tous les documents disponibles dans le dossier local"""
    logger.info("📂 Outil appelé : list_documents")
    docs_path = get_docs_path()
    
    if not os.path.exists(docs_path):
        logger.error(f"Dossier introuvable : {docs_path}")
        return {"error": "Dossier introuvable", "path": docs_path}
    
    try:
        docs = os.listdir(docs_path)
        logger.info(f"✅ {len(docs)} documents trouvés")
        return {"documents": docs, "count": len(docs)}
    except Exception as e:
        logger.error(f"❌ Erreur lors de la lecture du dossier : {e}")
        return {"error": str(e)}

def search_and_read(mot_cle: str) -> dict:
    """Cherche un document par mot clé et lit son contenu"""
    logger.info(f"🔍 Outil appelé : search_and_read avec mot_cle='{mot_cle}'")
    docs_path = get_docs_path()
    
    if not os.path.exists(docs_path):
        logger.error(f"Dossier introuvable : {docs_path}")
        return {"error": "Dossier introuvable"}
    
    try:
        for f in os.listdir(docs_path):
            if mot_cle.lower() in f.lower():
                path = os.path.join(docs_path, f)
                logger.info(f"📄 Document trouvé : {f}")
                
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()
                    logger.info(f"✅ Document lu : {len(content)} caractères")
                    return {
                        "filename": f,
                        "content": content,
                        "size": len(content)
                    }
        
        logger.warning(f"⚠️ Aucun document trouvé pour : {mot_cle}")
        return {"error": f"Aucun document trouvé contenant '{mot_cle}'"}
    
    except Exception as e:
        logger.error(f"❌ Erreur : {e}")
        return {"error": str(e)}

def get_time() -> dict:
    """Retourne l'heure actuelle du système"""
    logger.info("🕐 Outil appelé : get_time")
    
    try:
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_date = now.strftime("%Y-%m-%d")
        
        logger.info(f"✅ Heure renvoyée : {current_time}")
        return {
            "time": current_time,
            "date": current_date,
            "timestamp": now.isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Erreur : {e}")
        return {"error": str(e)}
