"""
Outils pour l'intégration GitHub
"""
import os
import logging
from github import Github
from dotenv import load_dotenv
from typing import List, Dict, Optional
import re
from datetime import datetime, timedelta

load_dotenv()
logger = logging.getLogger("GitHubTools")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_ORG = os.getenv("GITHUB_ORG")

def _get_github_client():
    """Crée un client GitHub authentifié"""
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN non configuré dans .env")
    return Github(GITHUB_TOKEN)

def list_github_repos() -> dict:
    """Liste les repositories GitHub de l'organisation ou de l'utilisateur"""
    logger.info(" Outil appelé : list_github_repos")
    
    if not GITHUB_TOKEN:
        logger.warning(" GITHUB_TOKEN manquant")
        return {"error": "Token GitHub non configuré. Ajoutez GITHUB_TOKEN dans .env"}
    
    try:
        client = _get_github_client()
        
        # Détermine si c'est une org ou un user
        try:
            entity = client.get_organization(GITHUB_ORG)
            entity_type = "organization"
        except:
            entity = client.get_user(GITHUB_ORG)
            entity_type = "user"
        
        repos = []
        for repo in list(entity.get_repos())[:20]:  # Limite à 20
            repos.append({
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description or "Pas de description",
                "private": repo.private,
                "language": repo.language,
                "url": repo.html_url
            })
        
        logger.info(f"{len(repos)} repos trouvés")
        return {
            "repos": repos,
            "count": len(repos),
            "entity_type": entity_type,
            "entity_name": GITHUB_ORG
        }
    
    except Exception as e:
        logger.error(f" Erreur GitHub: {e}")
        return {"error": f"Erreur GitHub : {str(e)}"}

def list_github_files(repo_name: str, path: str = "") -> dict:
    """Liste les fichiers et dossiers d'un repository GitHub"""
    logger.info(f" Outil appelé : list_github_files repo={repo_name}, path={path}")
    
    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}
    
    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
        contents = repo.get_contents(path)
        
        if not isinstance(contents, list):
            contents = [contents]
        
        files = []
        for c in contents:
            files.append({
                "name": c.name,
                "type": c.type,  # file ou dir
                "path": c.path,
                "size": c.size if c.type == "file" else None
            })
        
        logger.info(f" {len(files)} éléments trouvés")
        return {
            "files": files,
            "count": len(files),
            "repo": repo_name,
            "path": path or "/"
        }
    
    except Exception as e:
        logger.error(f" Erreur: {e}")
        return {"error": f"Erreur : {str(e)}"}

def read_github_file(repo_name: str, file_path: str) -> dict:
    """Lit le contenu d'un fichier dans un repository GitHub"""
    logger.info(f" Outil appelé : read_github_file repo={repo_name}, file={file_path}")
    
    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}
    
    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
        content_file = repo.get_contents(file_path)
        
        # Décode le contenu
        file_content = content_file.decoded_content.decode('utf-8')
        
        logger.info(f" Fichier lu: {len(file_content)} caractères")
        return {
            "filename": content_file.name,
            "path": file_path,
            "content": file_content[:2000],  # Limite à 2000 chars
            "full_size": len(file_content),
            "truncated": len(file_content) > 2000
        }
    
    except Exception as e:
        logger.error(f" Erreur: {e}")
        return {"error": f"Erreur : {str(e)}"}

def write_github_file(repo_name: str, file_path: str, content: str, commit_message: str) -> dict:
    """Crée ou met à jour un fichier dans un repository GitHub"""

    logger.info(f" Outil appelé : write_github_file repo={repo_name}, file={file_path}")

    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}

    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")

        #  Vérifier si le fichier existe déjà
        try:
            file = repo.get_contents(file_path)
            sha = file.sha

            #  UPDATE fichier existant
            repo.update_file(
                path=file_path,
                message=commit_message,
                content=content,
                sha=sha
            )

            logger.info(" Fichier mis à jour avec succès")

            return {
                "status": "updated",
                "file": file_path,
                "repo": repo_name
            }

        except Exception:
            # 📄 CREATE fichier (il n'existe pas)
            repo.create_file(
                path=file_path,
                message=commit_message,
                content=content
            )

            logger.info("📄 Fichier créé avec succès")

            return {
                "status": "created",
                "file": file_path,
                "repo": repo_name
            }

    except Exception as e:
        logger.error(f" Erreur GitHub: {e}")
        return {"error": str(e)}
        
# ═══════════════════════════════════════════════════════════════
# NIVEAU 1 : CRUD AVANCÉ
# ═══════════════════════════════════════════════════════════════

def scan_all_repos() -> dict:
    """Scan complet de tous les repositories avec métadonnées enrichies"""
    logger.info("🔍 Scan complet des repositories")
    
    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}
    
    try:
        client = _get_github_client()
        
        try:
            entity = client.get_organization(GITHUB_ORG)
        except:
            entity = client.get_user(GITHUB_ORG)
        
        repos_data = []
        for repo in entity.get_repos():
            # Analyse de chaque repo
            has_readme = False
            has_license = False
            has_gitignore = False
            
            try:
                repo.get_contents("README.md")
                has_readme = True
            except:
                pass
            
            try:
                repo.get_contents("LICENSE")
                has_license = True
            except:
                pass
            
            try:
                repo.get_contents(".gitignore")
                has_gitignore = True
            except:
                pass
            
            repos_data.append({
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description or "",
                "language": repo.language,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "last_push": repo.pushed_at.isoformat() if repo.pushed_at else None,
                "has_readme": has_readme,
                "has_license": has_license,
                "has_gitignore": has_gitignore,
                "default_branch": repo.default_branch,
                "is_private": repo.private,
                "size_kb": repo.size
            })
        
        logger.info(f"✅ {len(repos_data)} repos scannés")
        return {
            "repos": repos_data,
            "total": len(repos_data),
            "missing_readme": sum(1 for r in repos_data if not r["has_readme"]),
            "missing_license": sum(1 for r in repos_data if not r["has_license"])
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur scan : {e}")
        return {"error": str(e)}

def deep_scan_repo(repo_name: str) -> dict:
    """Scan approfondi d'un repository : structure, fichiers, problèmes potentiels"""
    logger.info(f"🔬 Deep scan de {repo_name}")
    
    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}
    
    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
        
        # Analyse récursive de la structure
        def analyze_contents(path=""):
            items = repo.get_contents(path)
            if not isinstance(items, list):
                items = [items]
            
            files = []
            dirs = []
            
            for item in items:
                if item.type == "dir":
                    dirs.append(item.path)
                    files.extend(analyze_contents(item.path))
                else:
                    files.append({
                        "path": item.path,
                        "name": item.name,
                        "size": item.size,
                        "extension": os.path.splitext(item.name)[1]
                    })
            
            return files
        
        all_files = analyze_contents()
        
        # Détection de patterns
        extensions = {}
        for f in all_files:
            ext = f["extension"]
            extensions[ext] = extensions.get(ext, 0) + 1
        
        # Détection de problèmes
        issues = []
        
        # Pas de README
        if not any(f["name"].upper() == "README.MD" for f in all_files):
            issues.append({"type": "missing_file", "severity": "high", "message": "README.md manquant"})
        
        # Pas de .gitignore
        if not any(f["name"] == ".gitignore" for f in all_files):
            issues.append({"type": "missing_file", "severity": "medium", "message": ".gitignore manquant"})
        
        # Fichiers volumineux
        large_files = [f for f in all_files if f["size"] > 1000000]  # > 1MB
        if large_files:
            issues.append({
                "type": "large_files",
                "severity": "medium",
                "message": f"{len(large_files)} fichier(s) > 1MB détecté(s)",
                "files": [f["path"] for f in large_files]
            })
        
        return {
            "repo": repo_name,
            "total_files": len(all_files),
            "file_types": extensions,
            "structure": {
                "depth": max(f["path"].count("/") for f in all_files) if all_files else 0,
                "directories": len(set(os.path.dirname(f["path"]) for f in all_files))
            },
            "issues": issues,
            "language": repo.language,
            "size_kb": repo.size
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur deep scan : {e}")
        return {"error": str(e)}

# ═══════════════════════════════════════════════════════════════
# NIVEAU 2 : ANALYSE INTELLIGENTE
# ═══════════════════════════════════════════════════════════════

def analyze_commits(repo_name: str, days: int = 30) -> dict:
    """Analyse les commits récents et génère un rapport"""
    logger.info(f"📊 Analyse des commits de {repo_name} ({days} derniers jours)")
    
    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}
    
    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
        
        since_date = datetime.now() - timedelta(days=days)
        commits = repo.get_commits(since=since_date)
        
        commit_data = []
        authors = {}
        files_changed = {}
        
        for commit in commits:
            author = commit.commit.author.name
            authors[author] = authors.get(author, 0) + 1
            
            commit_data.append({
                "sha": commit.sha[:7],
                "author": author,
                "date": commit.commit.author.date.isoformat(),
                "message": commit.commit.message.split("\n")[0]  # Première ligne
            })
            
            # Analyser les fichiers modifiés
            for file in commit.files:
                files_changed[file.filename] = files_changed.get(file.filename, 0) + 1
        
        # Top fichiers modifiés
        top_files = sorted(files_changed.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "repo": repo_name,
            "period_days": days,
            "total_commits": len(commit_data),
            "authors": authors,
            "top_contributors": sorted(authors.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_modified_files": [{"file": f, "changes": c} for f, c in top_files],
            "recent_commits": commit_data[:20]  # 20 plus récents
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur analyse commits : {e}")
        return {"error": str(e)}

def detect_code_issues(repo_name: str) -> dict:
    """Détecte les TODO, FIXME, et autres problèmes potentiels dans le code"""
    logger.info(f"🐛 Détection de problèmes dans {repo_name}")
    
    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}
    
    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
        
        def scan_file_content(path=""):
            items = repo.get_contents(path)
            if not isinstance(items, list):
                items = [items]
            
            issues = []
            
            for item in items:
                if item.type == "dir":
                    issues.extend(scan_file_content(item.path))
                elif item.type == "file":
                    # Analyser seulement les fichiers texte de code
                    code_extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.c', '.cpp']
                    if any(item.name.endswith(ext) for ext in code_extensions):
                        try:
                            content = item.decoded_content.decode('utf-8')
                            
                            # Recherche de patterns
                            for i, line in enumerate(content.split("\n"), 1):
                                if "TODO" in line.upper():
                                    issues.append({
                                        "type": "TODO",
                                        "file": item.path,
                                        "line": i,
                                        "content": line.strip()[:100]
                                    })
                                elif "FIXME" in line.upper():
                                    issues.append({
                                        "type": "FIXME",
                                        "file": item.path,
                                        "line": i,
                                        "content": line.strip()[:100]
                                    })
                                elif "HACK" in line.upper():
                                    issues.append({
                                        "type": "HACK",
                                        "file": item.path,
                                        "line": i,
                                        "content": line.strip()[:100]
                                    })
                        except:
                            pass  # Fichier binaire ou non-UTF8
            
            return issues
        
        all_issues = scan_file_content()
        
        # Grouper par type
        by_type = {}
        for issue in all_issues:
            t = issue["type"]
            by_type[t] = by_type.get(t, [])
            by_type[t].append(issue)
        
        return {
            "repo": repo_name,
            "total_issues": len(all_issues),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "details": all_issues[:50]  # Limite à 50 pour pas surcharger
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur détection : {e}")
        return {"error": str(e)}

# ═══════════════════════════════════════════════════════════════
# NIVEAU 3 : ACTIONS AUTONOMES
# ═══════════════════════════════════════════════════════════════

def generate_readme(repo_name: str) -> dict:
    """Génère automatiquement un README.md basé sur l'analyse du repo"""
    logger.info(f"📝 Génération README pour {repo_name}")
    
    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}
    
    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
        
        # Analyser le repo pour comprendre sa structure
        deep_scan = deep_scan_repo(repo_name)
        
        # Construire le README
        readme_content = f"""# {repo_name}

## 📖 Description

{repo.description or "Description à compléter"}

## 🚀 À propos

Ce projet a été automatiquement analysé et contient :
- **{deep_scan.get('total_files', 0)}** fichiers
- Langage principal : **{repo.language or 'Non détecté'}**
- Dernière mise à jour : {repo.pushed_at.strftime('%Y-%m-%d') if repo.pushed_at else 'Inconnu'}

## 📂 Structure

Types de fichiers détectés :
"""
        
        for ext, count in deep_scan.get('file_types', {}).items():
            if ext:
                readme_content += f"- `{ext}` : {count} fichier(s)\n"
        
        readme_content += """
## 🛠️ Installation

```bash
# Cloner le repository
git clone https://github.com/{}/{}.git
cd {}

# Instructions d'installation à compléter
```

## 📝 Utilisation

Documentation à venir.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📄 Licence

À définir.

---

*README généré automatiquement le {}*
""".format(GITHUB_ORG, repo_name, repo_name, datetime.now().strftime('%Y-%m-%d'))
        
        # Créer ou mettre à jour le README
        try:
            # Vérifier si README existe
            existing = repo.get_contents("README.md")
            repo.update_file(
                "README.md",
                f"📝 README auto-généré par MCP Agent",
                readme_content,
                existing.sha
            )
            action = "updated"
        except:
            # Créer nouveau README
            repo.create_file(
                "README.md",
                f"📝 README auto-généré par MCP Agent",
                readme_content
            )
            action = "created"
        
        logger.info(f"✅ README {action}")
        return {
            "repo": repo_name,
            "action": action,
            "preview": readme_content[:500],
            "url": f"https://github.com/{GITHUB_ORG}/{repo_name}/blob/main/README.md"
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur génération README : {e}")
        return {"error": str(e)}

def auto_fix_repo(repo_name: str) -> dict:
    """Corrige automatiquement les problèmes détectés dans un repo"""
    logger.info(f"🔧 Auto-fix de {repo_name}")
    
    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}
    
    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
        
        actions_taken = []
        
        # 1. Ajouter .gitignore si manquant
        try:
            repo.get_contents(".gitignore")
        except:
            # Créer .gitignore basique
            gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/

# IDEs
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Logs
*.log
"""
            repo.create_file(
                ".gitignore",
                "🔧 Add .gitignore via MCP Agent",
                gitignore_content
            )
            actions_taken.append("Created .gitignore")
        
        # 2. Ajouter README si manquant
        try:
            repo.get_contents("README.md")
        except:
            result = generate_readme(repo_name)
            if "error" not in result:
                actions_taken.append("Generated README.md")
        
        return {
            "repo": repo_name,
            "actions_taken": actions_taken,
            "total_fixes": len(actions_taken)
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur auto-fix : {e}")
        return {"error": str(e)}

def quality_report(repo_name: str) -> dict:
    """Génère un rapport de qualité complet d'un repository"""
    logger.info(f"📊 Rapport qualité de {repo_name}")
    
    try:
        # Combiner plusieurs analyses
        deep_scan = deep_scan_repo(repo_name)
        commits = analyze_commits(repo_name, days=30)
        issues = detect_code_issues(repo_name)
        
        # Calculer un score de qualité
        score = 100
        
        # Pénalités
        if not any(i for i in deep_scan.get("issues", []) if "README" in i.get("message", "")):
            score -= 0
        else:
            score -= 20
        
        if len(deep_scan.get("issues", [])) > 5:
            score -= 10
        
        if issues.get("total_issues", 0) > 20:
            score -= 15
        
        if commits.get("total_commits", 0) == 0:
            score -= 25
        
        score = max(0, score)
        
        return {
            "repo": repo_name,
            "quality_score": score,
            "rating": "Excellent" if score >= 80 else "Good" if score >= 60 else "Needs improvement",
            "deep_scan": deep_scan,
            "commits_analysis": commits,
            "code_issues": issues,
            "recommendations": [
                "Add missing README" if not any(i for i in deep_scan.get("issues", []) if "README" not in i.get("message", "")) else None,
                "Fix TODO/FIXME comments" if issues.get("total_issues", 0) > 10 else None,
                "More regular commits needed" if commits.get("total_commits", 0) < 10 else None
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur rapport : {e}")
        return {"error": str(e)}
