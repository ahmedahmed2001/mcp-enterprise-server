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
def list_pull_requests(repo_name: str, state: str = "open") -> dict:
    logger.info(f"📥 list_pull_requests repo={repo_name}")

    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}

    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")

        pulls = repo.get_pulls(state=state)

        result = []
        for pr in pulls:
            result.append({
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "author": pr.user.login,
                "created_at": pr.created_at.isoformat(),
                "url": pr.html_url
            })

        return {
            "repo": repo_name,
            "count": len(result),
            "pull_requests": result
        }

    except Exception as e:
        return {"error": str(e)}

def get_pull_request(repo_name: str, pr_number: int) -> dict:
    client = _get_github_client()
    repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
    pr = repo.get_pull(pr_number)

    return {
        "number": pr.number,
        "title": pr.title,
        "body": pr.body,
        "author": pr.user.login,
        "state": pr.state,
        "additions": pr.additions,
        "deletions": pr.deletions,
        "changed_files": pr.changed_files
    }
    

def get_pr_diff(repo_name: str, pr_number: int) -> dict:
    client = _get_github_client()
    repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
    pr = repo.get_pull(pr_number)

    diff = pr.diff_url

    import requests
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(diff, headers=headers)

    return {
        "pr": pr_number,
        "diff": r.text[:10000]  # limite
    }

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
# ═══════════════════════════════════════════════════════════════
# ANALYSE DES PULL REQUESTS
# ═══════════════════════════════════════════════════════════════

def analyze_pull_request(repo_name: str, pr_number: int) -> dict:
    """
    Analyse une Pull Request et vérifie sa conformité avec le template
    Retourne un score et des recommandations détaillées
    """
    logger.info(f"🔍 Analyse PR #{pr_number} dans {repo_name}")
    
    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}
    
    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
        pr = repo.get_pull(pr_number)
        
        # ── Récupérer toutes les infos de la PR ──────────────────
        pr_data = {
            "number": pr.number,
            "title": pr.title,
            "body": pr.body or "",
            "author": pr.user.login,
            "base_branch": pr.base.ref,
            "head_branch": pr.head.ref,
            "files_changed": pr.changed_files,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "commits": pr.commits,
            "labels": [l.name for l in pr.labels],
            "draft": pr.draft
        }
        
        # ── Analyse du titre ─────────────────────────────────────
        title_analysis = _analyze_pr_title(pr.title)
        
        # ── Analyse de la description ────────────────────────────
        body_analysis = _analyze_pr_body(pr.body or "")
        
        # ── Analyse des fichiers modifiés ────────────────────────
        files_analysis = _analyze_pr_files(pr)
        
        # ── Calcul du score global ───────────────────────────────
        score = _calculate_pr_score(title_analysis, body_analysis, files_analysis, pr_data)
        
        # ── Déterminer la sévérité ───────────────────────────────
        if score >= 80:
            severity = "good"
            action = "approve_with_comments"
        elif score >= 60:
            severity = "warning"
            action = "comment_suggestions"
        else:
            severity = "critical"
            action = "request_changes"
        
        return {
            "pr_number": pr_number,
            "repo": repo_name,
            "score": score,
            "severity": severity,
            "action": action,
            "pr_data": pr_data,
            "title_analysis": title_analysis,
            "body_analysis": body_analysis,
            "files_analysis": files_analysis,
            "summary": _generate_pr_summary(score, title_analysis, body_analysis, files_analysis)
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur analyse PR : {e}")
        return {"error": str(e)}


def _analyze_pr_title(title: str) -> dict:
    """Analyse le titre de la PR"""
    issues = []
    suggestions = []
    score = 100
    
    # Vérifier la longueur
    if len(title) < 10:
        issues.append("Titre trop court (minimum 10 caractères)")
        suggestions.append("Sois plus descriptif : 'fix: correction du crash sur la page login'")
        score -= 30
    elif len(title) > 72:
        issues.append("Titre trop long (maximum 72 caractères)")
        suggestions.append("Raccourcis le titre, mets les détails dans la description")
        score -= 10
    
    # Vérifier le format conventionnel (feat:, fix:, docs:, etc.)
    conventional_prefixes = ['feat:', 'fix:', 'docs:', 'style:', 'refactor:', 
                             'test:', 'chore:', 'perf:', 'ci:', 'build:']
    has_prefix = any(title.lower().startswith(p) for p in conventional_prefixes)
    
    if not has_prefix:
        issues.append("Le titre ne suit pas le format conventionnel")
        suggestions.append("Utilise un préfixe : feat:, fix:, docs:, refactor:, test:, chore:")
        score -= 25
    
    # Vérifier les titres vagues
    vague_titles = ['fix', 'update', 'change', 'wip', 'test', 'minor', 
                    'fix bug', 'bug fix', 'changes', 'update code']
    if title.lower().strip() in vague_titles:
        issues.append("Titre trop vague")
        suggestions.append("Décris précisément ce que la PR fait")
        score -= 40
    
    # Vérifier majuscule après le préfixe
    if has_prefix and ':' in title:
        after_prefix = title.split(':', 1)[1].strip()
        if after_prefix and after_prefix[0].isupper():
            issues.append("La description après le préfixe ne doit pas commencer par une majuscule")
            suggestions.append(f"Exemple : '{title.split(':')[0]}: {after_prefix[0].lower()}{after_prefix[1:]}'")
            score -= 5
    
    return {
        "score": max(0, score),
        "issues": issues,
        "suggestions": suggestions,
        "has_conventional_prefix": has_prefix,
        "length": len(title)
    }


def _analyze_pr_body(body: str) -> dict:
    """Analyse la description de la PR"""
    issues = []
    suggestions = []
    score = 100
    
    # Vérifier si la description est vide
    if not body or len(body.strip()) < 20:
        issues.append("Description vide ou trop courte")
        suggestions.append("Explique le contexte, pourquoi ce changement, et comment tu l'as testé")
        score -= 50
        return {"score": 0, "issues": issues, "suggestions": suggestions}
    
    body_lower = body.lower()
    
    # Vérifier la section Description
    if '## 📋 description' not in body_lower and '## description' not in body_lower:
        issues.append("Section 'Description' manquante")
        suggestions.append("Ajoute une section ## Description avec au moins 50 caractères")
        score -= 20
    
    # Vérifier le type de changement coché
    has_checked_type = '- [x]' in body_lower
    if not has_checked_type:
        issues.append("Aucun type de changement coché")
        suggestions.append("Coche au moins un type : Bug fix, Feature, Refactoring, etc.")
        score -= 15
    
    # Vérifier le lien vers une issue
    has_issue_link = any(keyword in body_lower for keyword in 
                         ['fixes #', 'closes #', 'resolves #', 'fix #', 'close #'])
    if not has_issue_link:
        issues.append("Pas de lien vers une issue")
        suggestions.append("Ajoute 'Fixes #NUMERO' pour lier automatiquement l'issue")
        score -= 15
    
    # Vérifier la checklist
    checklist_items = body.count('- [x]') + body.count('- [ ]')
    checked_items = body.count('- [x]')
    
    if checklist_items == 0:
        issues.append("Checklist absente")
        suggestions.append("Ajoute une checklist pour confirmer la qualité du code")
        score -= 10
    elif checked_items == 0:
        issues.append("Aucune case de la checklist n'est cochée")
        suggestions.append("Coche les cases de la checklist qui s'appliquent")
        score -= 10
    
    # Vérifier si les placeholders sont encore présents
    if '<!-- ' in body and ' -->' in body:
        issues.append("Des commentaires de template non remplis sont présents")
        suggestions.append("Remplis tous les champs du template et supprime les commentaires")
        score -= 10
    
    return {
        "score": max(0, score),
        "issues": issues,
        "suggestions": suggestions,
        "has_issue_link": has_issue_link,
        "has_checked_type": has_checked_type,
        "checklist_total": checklist_items,
        "checklist_checked": checked_items,
        "word_count": len(body.split())
    }


def _analyze_pr_files(pr) -> dict:
    """Analyse les fichiers modifiés dans la PR"""
    issues = []
    suggestions = []
    score = 100
    
    try:
        files = list(pr.get_files())
        
        # PR trop grande
        if pr.changed_files > 20:
            issues.append(f"PR trop grande ({pr.changed_files} fichiers modifiés)")
            suggestions.append("Découpe en plusieurs PRs plus petites et ciblées")
            score -= 25
        elif pr.changed_files > 10:
            issues.append(f"PR assez grande ({pr.changed_files} fichiers)")
            suggestions.append("Considère de découper si les changements ne sont pas liés")
            score -= 10
        
        # Trop de lignes modifiées
        total_changes = pr.additions + pr.deletions
        if total_changes > 500:
            issues.append(f"Beaucoup de changements ({total_changes} lignes)")
            suggestions.append("Les grandes PRs sont difficiles à reviewer")
            score -= 15
        
        # Vérifier fichiers sensibles
        sensitive_files = ['.env', 'secrets', 'password', 'private_key', 'id_rsa']
        for f in files:
            if any(s in f.filename.lower() for s in sensitive_files):
                issues.append(f"⚠️ Fichier sensible détecté : {f.filename}")
                suggestions.append(f"Vérifie que {f.filename} ne contient pas de secrets")
                score -= 30
        
        return {
            "score": max(0, score),
            "issues": issues,
            "suggestions": suggestions,
            "files_count": pr.changed_files,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "total_changes": total_changes
        }
    
    except Exception as e:
        return {"score": 80, "issues": [], "suggestions": [], "error": str(e)}


def _calculate_pr_score(title_analysis, body_analysis, files_analysis, pr_data) -> int:
    """Calcule le score global de la PR"""
    # Poids de chaque section
    title_weight = 0.30   # 30%
    body_weight = 0.50    # 50%
    files_weight = 0.20   # 20%
    
    score = (
        title_analysis["score"] * title_weight +
        body_analysis["score"] * body_weight +
        files_analysis["score"] * files_weight
    )
    
    # Bonus si PR en draft (le dev sait que c'est pas fini)
    if pr_data.get("draft"):
        score = min(100, score + 10)
    
    return round(score)


def _generate_pr_summary(score, title_analysis, body_analysis, files_analysis) -> str:
    """Génère un résumé lisible pour le commentaire GitHub"""
    
    if score >= 80:
        header = "✅ **Bonne PR !** Quelques suggestions mineures."
    elif score >= 60:
        header = "⚠️ **PR à améliorer.** Des changements sont recommandés."
    else:
        header = "❌ **PR non conforme.** Des changements sont requis avant review."
    
    summary = f"""{header}

## 📊 Score : {score}/100

| Section | Score | Statut |
|---------|-------|--------|
| 📝 Titre | {title_analysis['score']}/100 | {'✅' if title_analysis['score'] >= 70 else '❌'} |
| 📋 Description | {body_analysis['score']}/100 | {'✅' if body_analysis['score'] >= 70 else '❌'} |
| 📁 Fichiers | {files_analysis['score']}/100 | {'✅' if files_analysis['score'] >= 70 else '❌'} |

"""
    
    # Problèmes détectés
    all_issues = (
        title_analysis.get("issues", []) +
        body_analysis.get("issues", []) +
        files_analysis.get("issues", [])
    )
    
    if all_issues:
        summary += "## ❌ Problèmes détectés\n\n"
        for issue in all_issues:
            summary += f"- {issue}\n"
        summary += "\n"
    
    # Suggestions
    all_suggestions = (
        title_analysis.get("suggestions", []) +
        body_analysis.get("suggestions", []) +
        files_analysis.get("suggestions", [])
    )
    
    if all_suggestions:
        summary += "## 💡 Suggestions\n\n"
        for suggestion in all_suggestions:
            summary += f"- {suggestion}\n"
        summary += "\n"
    
    summary += "---\n*Analyse automatique par MCP Agent 🤖*"
    
    return summary


def comment_on_pull_request(repo_name: str, pr_number: int, comment: str) -> dict:
    """Ajoute un commentaire sur une Pull Request"""
    logger.info(f"💬 Commentaire sur PR #{pr_number}")
    
    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}
    
    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
        pr = repo.get_pull(pr_number)
        
        pr.create_issue_comment(comment)
        
        logger.info("✅ Commentaire ajouté")
        return {
            "status": "success",
            "pr_number": pr_number,
            "repo": repo_name
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur commentaire : {e}")
        return {"error": str(e)}


def request_changes_on_pr(repo_name: str, pr_number: int, comment: str) -> dict:
    """Demande des modifications sur une Pull Request (bloque le merge)"""
    logger.info(f"🚫 Request changes sur PR #{pr_number}")
    
    if not GITHUB_TOKEN:
        return {"error": "Token GitHub non configuré"}
    
    try:
        client = _get_github_client()
        repo = client.get_repo(f"{GITHUB_ORG}/{repo_name}")
        pr = repo.get_pull(pr_number)
        
        pr.create_review(
            body=comment,
            event="REQUEST_CHANGES"
        )
        
        logger.info("✅ Request changes soumis")
        return {
            "status": "changes_requested",
            "pr_number": pr_number,
            "repo": repo_name
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur request changes : {e}")
        return {"error": str(e)}
