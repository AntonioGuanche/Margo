# Margó — Guide de démarrage Claude Code

## 1. Installation (5 minutes)

### Prérequis
- Node.js 18+ installé (Claude Code en a besoin)
- Python 3.12+ installé
- Git installé
- Un compte Anthropic avec une clé API

### Installer Claude Code
```bash
npm install -g @anthropic-ai/claude-code
```

### Créer le repo
```bash
mkdir margo && cd margo
git init
# Copie les fichiers CLAUDE.md, PLAN.md, .env.example à la racine
git add -A && git commit -m "Initial project setup"
```

### Lancer Claude Code
```bash
claude
```

C'est tout. Claude Code lit automatiquement le CLAUDE.md et comprend le projet.

---

## 2. Comment parler à Claude Code

### Tu peux parler normalement !
Claude Code comprend le français et le langage courant. Pas besoin de prompts structurés.

### Les 5 habitudes qui changent tout

**Habitude 1 — Donne le contexte du sprint**
```
Je commence le sprint 1. On attaque les fondations :
modèles SQLAlchemy, auth magic link, et CRUD ingrédients.
```

**Habitude 2 — Demande un plan avant le code**
```
Planifie comment tu vas structurer les modèles SQLAlchemy
pour les 5 tables du data model. Ne code pas encore.
```
→ Claude propose un plan. Tu valides ou ajustes. Puis :
```
Ok, implémente les modèles.
```

**Habitude 3 — Une tâche à la fois**
❌ "Fais tout le sprint 1"
✅ "Crée les modèles SQLAlchemy pour les 5 tables"
Puis : "Maintenant configure Alembic et crée la migration initiale"
Puis : "Maintenant crée l'endpoint POST /auth/login avec magic link"

**Habitude 4 — Sois précis sur le comportement attendu**
```
Crée l'endpoint POST /api/recipes. Il prend :
- name (str, required)
- selling_price (float, required)  
- category (str, optional)
- ingredients: [{ingredient_id: int, quantity: float, unit: str}]

Il doit calculer automatiquement le food_cost et le food_cost_percent
avant de sauvegarder. Retourne la recette complète avec le coût.
```

**Habitude 5 — /clear entre les tâches**
Quand tu passes d'un sujet à un autre (ex: du backend au frontend),
tape `/clear` pour repartir avec un contexte propre.
Claude relit le CLAUDE.md automatiquement.

---

## 3. Commandes utiles Claude Code

| Commande | Usage |
|----------|-------|
| `/clear` | Vider le contexte (garder le CLAUDE.md) |
| `/init` | Générer un CLAUDE.md de base (on en a déjà un) |
| `Esc` | Arrêter Claude en pleine action |
| `Shift+Tab ×2` | Mode Plan (Claude analyse sans modifier de fichiers) |
| `/help` | Aide |

---

## 4. Prompts prêts à l'emploi — Sprint 1

Copie-colle ces prompts dans Claude Code pour démarrer le sprint 1.
Adapte selon ce qui est déjà fait.

### Étape 1 : Setup projet
```
Initialise le projet backend :
- Crée pyproject.toml avec les dépendances (fastapi, uvicorn, 
  sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings,
  python-jose[cryptography], anthropic, httpx, pytest, pytest-asyncio)
- Crée backend/main.py avec l'app FastAPI, CORS configuré pour 
  FRONTEND_URL, et un endpoint /health
- Crée backend/app/config.py avec pydantic-settings qui lit le .env
- Crée backend/app/database.py avec async engine et session
- Configure Alembic
```

### Étape 2 : Modèles
```
Crée les modèles SQLAlchemy dans backend/app/models/ selon le 
data model décrit dans CLAUDE.md. Utilise la syntaxe SQLAlchemy 2.0
(mapped_column). N'oublie pas les relations et les foreign keys.
Crée la migration Alembic initiale.
```

### Étape 3 : Auth
```
Implémente l'auth magic link dans backend/app/routers/auth.py :
- POST /auth/login : reçoit {email}, génère un token temporaire,
  envoie un email avec le lien magic. Pour l'instant, juste log 
  le lien dans la console (on branchera Resend plus tard).
- POST /auth/verify : reçoit {token}, vérifie, crée ou récupère
  le restaurant associé à l'email, retourne un JWT.
- Crée un middleware/dependency get_current_user qui décode le JWT.
Écris les tests.
```

### Étape 4 : CRUD Ingrédients
```
Crée le CRUD complet pour les ingrédients :
- GET /api/ingredients — liste avec search par nom, paginé
- GET /api/ingredients/{id}
- POST /api/ingredients — créer
- PUT /api/ingredients/{id} — modifier
- DELETE /api/ingredients/{id}
Tous les endpoints nécessitent l'auth. Filtre par restaurant_id 
du user connecté. Crée les schemas Pydantic et les tests.
```

### Étape 5 : Frontend setup
```
Initialise le frontend React :
- npm create vite@latest frontend -- --template react-ts
- Installe tailwindcss, react-router-dom, @tanstack/react-query,
  lucide-react, vite-plugin-pwa
- Configure Tailwind, PWA manifest (nom: Margó, couleur: #c2410c),
  service worker basique
- Crée le routing : / (dashboard), /login, /ingredients, /recipes
- Crée api/client.ts : fetch wrapper qui ajoute le JWT header
  et gère le refresh
```

### Étape 6 : Pages frontend
```
Crée la page Login :
- Input email + bouton "Recevoir le lien magique"
- Appel POST /auth/login
- Message "Lien envoyé ! Vérifie ta boîte mail."
- Page /auth/callback qui récupère le token dans l'URL et appelle 
  POST /auth/verify, stocke le JWT

Puis crée la page Ingrédients :
- Liste des ingrédients avec barre de recherche
- Bouton "+ Ajouter" qui ouvre un formulaire (nom, unité, prix, fournisseur)
- Clic sur un ingrédient → édition inline ou modal
- Bouton supprimer avec confirmation

Mobile-first, Tailwind, couleurs Margó (#c2410c brand, #059669 green).
```

---

## 5. Quand ça coince

### Claude fait n'importe quoi
→ `Esc` pour arrêter. Puis explique ce qui ne va pas :
```
Stop. Tu as créé le modèle sans les relations. Recommence en 
ajoutant les relations SQLAlchemy entre Recipe et Ingredient 
via la table RecipeIngredient.
```

### Claude oublie le contexte
→ `/clear` puis rappelle le contexte :
```
On travaille sur le CRUD recettes (sprint 2). Les modèles et
l'auth sont déjà en place. Regarde les fichiers existants 
dans backend/app/ avant de commencer.
```

### Une erreur que tu ne comprends pas
```
J'ai cette erreur quand je lance pytest :
[colle l'erreur]
Regarde le code concerné et corrige.
```

### Tu veux que Claude explore le code existant d'abord
```
Lis les fichiers dans backend/app/models/ et backend/app/routers/ 
pour comprendre la structure actuelle. Puis dis-moi ce que tu 
comprends avant de coder quoi que ce soit.
```

---

## 6. Checklist avant chaque sprint

- [ ] Mettre à jour la section "Current sprint" dans CLAUDE.md
- [ ] Cocher les tâches terminées dans PLAN.md
- [ ] `git commit` le travail du sprint précédent
- [ ] `/clear` pour repartir propre
- [ ] Donner le contexte du nouveau sprint à Claude Code
