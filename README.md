# Serveur MCP Entreprise

Serveur MCP (Model Context Protocol) modulaire et évolutif pour connecter des LLMs à des outils métier.

##  Caractéristiques

- ✅ **Modulaire** : Ajoutez des outils sans modifier le code du serveur
- ✅ **Configuration YAML** : Activez/désactivez des outils via fichier de config
- ✅ **Logs structurés** : Traçabilité complète de toutes les opérations
- ✅ **Retry automatique** : Résilience face aux erreurs réseau
- ✅ **Health checks** : Endpoints de monitoring pour supervision
- ✅ **Service systemd** : Démarrage automatique et persistance
- ✅ **Sécurité** : Secrets dans variables d'environnement

## 📦 Outils disponibles

### Documents locaux
- `list_documents` : Liste les documents sur le serveur
- `search_and_read` : Cherche et lit un document par mot-clé
- `get_time` : Retourne l'heure système

### GitHub (lecture seule)
- `list_github_repos` : Liste les repositories
- `list_github_files` : Liste les fichiers d'un repo
- `read_github_file` : Lit le contenu d'un fichier

##  Démarrage rapide

### 1. Configuration

Copiez `.env.example` vers `.env` et remplissez :

```bash
GROQ_API_KEY=votre_clé_groq
MCP_SERVER_URL=http://localhost:8001/mcp
GITHUB_TOKEN=votre_token_github_optionnel
GITHUB_ORG=votre_organisation_ou_username
```

### 2. Lancer le serveur

```bash
sudo systemctl start mcp
sudo systemctl status mcp
```

### 3. Vérifier le fonctionnement

```bash
curl http://localhost:8001/health
curl http://localhost:8001/tools
```

### 4. Lancer l'interface

```bash
source venv/bin/activate
streamlit run app.py
```

## 🔧 Ajouter un nouvel outil

### Étape 1 : Créer le fichier Python

Créez `tools/mon_outil.py` :

```python
import logging
logger = logging.getLogger("MonOutil")

def ma_fonction(param1: str) -> dict:
    """Description de ce que fait la fonction"""
    logger.info(f"Fonction appelée avec param1={param1}")
    
    # Votre logique ici
    result = f"Traitement de {param1}"
    
    return {"result": result}
```

### Étape 2 : Ajouter dans la config

Modifiez `config/tools_config.yaml` :

```yaml
tools:
  # ... outils existants ...
  
  mon_outil:
    enabled: true
    module: tools.mon_outil
    description: "Description de mon outil"
    functions:
      - ma_fonction
```

### Étape 3 : Redémarrer le serveur

```bash
sudo systemctl restart mcp
```

### Étape 4 : Mettre à jour le client

Ajoutez la description de l'outil dans `client2.py` section `tools = [...]`.

## Monitoring

### Health Check

```bash
curl http://localhost:8001/health
```

Retourne : statut, uptime, nombre d'outils chargés

### Liste des outils

```bash
curl http://localhost:8001/tools
```

Retourne : tous les outils actifs avec leurs descriptions

### Configuration active

```bash
curl http://localhost:8001/config
```

Retourne : la configuration YAML active

## Logs

Les logs sont dans `/home/ahmed/mcp-project/mcp_server.log` et via systemd :

```bash
# Logs en temps réel
sudo journalctl -u mcp -f

# 50 dernières lignes
sudo journalctl -u mcp -n 50
```

## Sécurité

- Tous les secrets dans `.env` (jamais dans le code)
- `.gitignore` configuré pour éviter les fuites
- Service tourne en utilisateur non-root
- Permissions minimales sur les tokens

## Architecture
Interface (Streamlit)
↓
Client IA (Groq/LLaMA)
↓
Serveur MCP (vous êtes ici)
↓
Outils (documents, GitHub, etc.)

##  Support
Pour toute question, consultez les logs ou contactez l'équipe
