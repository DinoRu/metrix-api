# 🚀 MeterSync API

**MeterSync API** est une solution professionnelle de gestion de relevés de compteurs, conçue pour faciliter la collecte, la synchronisation et l'analyse des données de comptage sur le terrain.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-316192.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-Commercial-red.svg)](LICENSE)

---

## 📋 Table des matières

- [Présentation](#-présentation)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Démarrage](#-démarrage)
- [API Documentation](#-api-documentation)
- [Tests](#-tests)
- [Monitoring](#-monitoring)
- [Déploiement](#-déploiement)
- [Structure du projet](#-structure-du-projet)
- [Technologies utilisées](#-technologies-utilisées)
- [Contribution](#-contribution)
- [Support](#-support)

---

## 🎯 Présentation

MeterSync API est une API RESTful robuste conçue pour gérer efficacement les relevés de compteurs en environnement mobile et offline. Elle permet aux techniciens sur le terrain de collecter des données de comptage, de prendre des photos, et de synchroniser leurs données même en cas de connexion intermittente.

### Cas d'usage

- 📊 Gestion de parcs de compteurs (électricité, eau, gaz)
- 📱 Applications mobiles de relevé terrain
- 🔄 Synchronisation offline-first avec résolution automatique de conflits
- 📈 Analyse et export de données de consommation
- 📸 Documentation photo des installations

---

## ✨ Fonctionnalités

### 🔐 Authentification & Sécurité
- Authentification JWT avec refresh tokens
- Contrôle d'accès basé sur les rôles (RBAC)
- Middleware de sécurité (CORS, rate limiting, headers sécurisés)
- Support optionnel d'API keys
- Hash des mots de passe avec bcrypt

### 📊 Gestion des Compteurs
- CRUD complet des compteurs avec métadonnées
- Import/export Excel avec validation
- Recherche et filtrage avancés
- Historique des relevés par compteur
- Gestion des états (actif, inactif, en maintenance)

### 📝 Relevés de Compteurs
- Enregistrement de relevés avec géolocalisation
- Synchronisation offline-first
- Résolution automatique des conflits
- Support de photos multiples par relevé
- Validation des données en temps réel

### 📸 Gestion des Photos
- Upload vers stockage S3-compatible
- URLs pré-signées pour téléchargement sécurisé
- Compression et optimisation automatiques
- Support de plusieurs formats d'image

### 🔄 Tâches Asynchrones
- Traitement en arrière-plan avec Celery
- Import/export de données volumineuses
- Tâches planifiées (Celery Beat)
- Monitoring des tâches avec Flower

### 📡 Temps Réel
- WebSocket pour notifications instantanées
- Mises à jour de statut en temps réel
- Synchronisation collaborative

### 📤 Export de Données
- Export Excel avec formatage personnalisé
- Export CSV pour analyses
- API de génération de rapports
- Tâches d'export asynchrones

### 📈 Monitoring
- Métriques Prometheus
- Dashboard Grafana pré-configuré
- Health checks automatiques
- Logs structurés avec request IDs

---

## 🏗 Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │──────▶│   Nginx      │──────▶│   FastAPI   │
│  (Mobile)   │      │  (Optional)  │      │     API     │
└─────────────┘      └──────────────┘      └─────────────┘
                                                   │
                           ┌───────────────────────┼───────────────────┐
                           ▼                       ▼                   ▼
                    ┌─────────────┐        ┌─────────────┐    ┌─────────────┐
                    │ PostgreSQL  │        │    Redis    │    │   S3/Minio  │
                    │  Database   │        │    Cache    │    │   Storage   │
                    └─────────────┘        └─────────────┘    └─────────────┘
                                                   │
                                                   ▼
                                           ┌──────────────┐
                                           │    Celery    │
                                           │   Workers    │
                                           └──────────────┘
```

### Composants principaux

- **FastAPI** : Framework web asynchrone haute performance
- **PostgreSQL** : Base de données relationnelle principale
- **Redis** : Cache et broker de messages pour Celery
- **Celery** : Traitement asynchrone des tâches
- **S3** : Stockage objet pour les photos
- **Flower** : Interface de monitoring Celery
- **Prometheus/Grafana** : Stack de monitoring

---

## 📦 Prérequis

- **Python** 3.11+
- **Docker** 20.10+ et **Docker Compose** 2.0+
- **PostgreSQL** 17+ (si installation locale)
- **Redis** 7+ (si installation locale)
- **S3-compatible storage** (AWS S3, MinIO, etc.)

---

## 🚀 Installation

### Option 1 : Docker Compose (Recommandé)

1. **Cloner le repository**
```bash
git clone https://github.com/DinoRu/metrix-api.git
cd metrix-api
```

2. **Créer le fichier de configuration**
```bash
cp app/.env.example app/.env
# Éditer app/.env avec vos valeurs
```

3. **Lancer l'application**
```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f api
```

4. **Appliquer les migrations**
```bash
docker-compose run --rm migrate
```

### Option 2 : Installation locale

1. **Cloner et configurer l'environnement**
```bash
git clone https://github.com/DinoRu/metrix-api.git
cd metrix-api

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
```

2. **Configurer la base de données**
```bash
# Créer la base PostgreSQL
createdb metrix_db

# Appliquer les migrations
alembic upgrade head
```

3. **Lancer l'application**
```bash
# Démarrer l'API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Dans un autre terminal, démarrer Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Dans un troisième terminal, démarrer Celery beat
celery -A app.core.celery_app beat --loglevel=info
```

---

## ⚙️ Configuration

### Variables d'environnement principales

Créer un fichier `app/.env` avec les variables suivantes :

```bash
# Application
APP_NAME=Meter Reading API
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production

# Base de données
DATABASE_URL=postgresql://user:password@db:5432/metrix_db
PROD_DB_URL=postgresql://user:password@prod-host:5432/metrix_db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://redis:6379/0
PRO_REDIS_URL=redis://prod-redis:6379/0
REDIS_TTL=3600

# JWT
JWT_SECRET=your-super-secret-jwt-key-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
JWT_REFRESH_EXPIRATION_DAYS=7

# S3 Storage
S3_ENDPOINT_URL=https://s3.yandexcloud.net
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=metrix-photos
S3_REGION=ru-central1
PRESIGNED_URL_EXPIRATION=3600

# PostgreSQL (pour docker-compose)
POSTGRES_USER=metrix_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=metrix_db

# Sécurité
RATE_LIMIT_PER_MINUTE=60
REQUIRE_API_KEY=false
BCRYPT_ROUNDS=12

# Monitoring
EXPOSE_METRICS=true
```

### Configuration avancée

Pour une configuration détaillée, consulter `app/config.py`.

---

## 🎬 Démarrage

### Avec Docker Compose

```bash
# Démarrer tous les services
docker-compose up -d

# Services disponibles :
# - API : http://localhost:8000
# - Flower : http://localhost:5555
# - Documentation : http://localhost:8000/docs

# Arrêter les services
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v
```

### Services individuels

```bash
# API uniquement
docker-compose up -d api

# Avec monitoring
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Voir les logs
docker-compose logs -f [service-name]
```

---

## 📚 API Documentation

### Documentation interactive

Une fois l'application démarrée, accédez à :

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc
- **OpenAPI JSON** : http://localhost:8000/openapi.json

### Endpoints principaux

#### Authentication
```bash
POST /api/v1/auth/register     # Créer un compte
POST /api/v1/auth/login        # Se connecter
POST /api/v1/auth/refresh      # Rafraîchir le token
POST /api/v1/auth/logout       # Se déconnecter
```

#### Meters (Compteurs)
```bash
GET    /api/v1/meters          # Lister les compteurs
POST   /api/v1/meters          # Créer un compteur
GET    /api/v1/meters/{id}     # Détails d'un compteur
PUT    /api/v1/meters/{id}     # Modifier un compteur
DELETE /api/v1/meters/{id}     # Supprimer un compteur
POST   /api/v1/meters/import   # Importer depuis Excel
```

#### Readings (Relevés)
```bash
GET    /api/v1/readings        # Lister les relevés
POST   /api/v1/readings        # Créer un relevé
GET    /api/v1/readings/{id}   # Détails d'un relevé
PUT    /api/v1/readings/{id}   # Modifier un relevé
DELETE /api/v1/readings/{id}   # Supprimer un relevé
POST   /api/v1/readings/sync   # Synchroniser (batch)
```

#### Photos
```bash
POST   /api/v1/photos/upload   # Upload une photo
GET    /api/v1/photos/{id}     # URL de téléchargement
DELETE /api/v1/photos/{id}     # Supprimer une photo
```

#### Export
```bash
POST   /api/v1/export/excel    # Générer export Excel
POST   /api/v1/export/csv      # Générer export CSV
GET    /api/v1/export/{task_id}/status  # Statut de l'export
GET    /api/v1/export/{task_id}/download # Télécharger l'export
```

### Authentification

L'API utilise JWT Bearer tokens :

```bash
# 1. Se connecter
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Réponse : {"access_token": "eyJ...", "token_type": "bearer"}

# 2. Utiliser le token
curl -X GET http://localhost:8000/api/v1/meters \
  -H "Authorization: Bearer eyJ..."
```

---

## 🧪 Tests

### Exécuter les tests

```bash
# Tous les tests
pytest

# Avec couverture
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_meters.py
pytest tests/test_auth.py -v

# Mode watch
pytest-watch
```

### Structure des tests

```
tests/
├── conftest.py           # Fixtures communes
├── test_auth.py          # Tests d'authentification
├── test_meters.py        # Tests des compteurs
└── test_readings.py      # Tests des relevés
```

---

## 📊 Monitoring

### Prometheus & Grafana

Démarrer la stack de monitoring :

```bash
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

Services disponibles :
- **Prometheus** : http://localhost:9090
- **Grafana** : http://localhost:3000 (admin/admin)

### Métriques disponibles

- Requêtes HTTP (count, latency)
- Taux d'erreur par endpoint
- Pool de connexions DB
- Tâches Celery (success, failure, latency)
- Utilisation mémoire/CPU

### Health Check

```bash
curl http://localhost:8000/health

# Réponse
{
  "status": "healthy",
  "timestamp": "2025-01-13T10:30:00Z",
  "version": "1.0.0"
}
```

### Flower (Celery Monitoring)

Interface de monitoring Celery disponible sur : http://localhost:5555

---

## 🚢 Déploiement

### Production avec Docker

1. **Préparer l'environnement**
```bash
# Créer le fichier .env de production
cp app/.env.example app/.env.production
# Configurer les variables avec les valeurs de production
```

2. **Builder les images**
```bash
docker-compose -f docker-compose.yml build
```

3. **Déployer**
```bash
docker-compose -f docker-compose.yml up -d
```

### CI/CD avec GitHub Actions

Le projet inclut un workflow GitHub Actions (`.github/workflows/deploy.yml`) pour le déploiement automatique.

### Reverse Proxy (Nginx)

Configuration Nginx incluse dans `nginx/default.conf` :

```bash
# Décommenter dans docker-compose.yml
docker-compose up -d nginx
```

### Recommandations de production

- ✅ Utiliser des secrets managers (AWS Secrets, Vault)
- ✅ Activer HTTPS avec certificats SSL
- ✅ Configurer les backups automatiques PostgreSQL
- ✅ Mettre en place la rotation des logs
- ✅ Utiliser un CDN pour les assets statiques
- ✅ Configurer le monitoring et alerting
- ✅ Implémenter le rate limiting au niveau nginx

---

## 📁 Structure du projet

```
metrix-api/
├── .github/
│   └── workflows/
│       └── deploy.yml          # CI/CD configuration
├── alembic/
│   ├── versions/               # Migrations de schéma
│   └── env.py                  # Configuration Alembic
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py         # Endpoints d'authentification
│   │       ├── meters.py       # Endpoints compteurs
│   │       ├── readings.py     # Endpoints relevés
│   │       ├── photos.py       # Endpoints photos
│   │       ├── export.py       # Endpoints d'export
│   │       ├── tasks.py        # Endpoints tâches
│   │       ├── websocket.py    # WebSocket
│   │       └── user.py         # Gestion utilisateurs
│   ├── auth/
│   │   ├── jwt.py              # Gestion JWT
│   │   └── dependencies.py     # Dépendances auth
│   ├── core/
│   │   ├── celery_app.py       # Configuration Celery
│   │   ├── redis.py            # Client Redis
│   │   └── s3_config.py        # Configuration S3
│   ├── middleware/
│   │   ├── api_key.py          # Middleware API key
│   │   ├── logging.py          # Logging structuré
│   │   ├── monitoring.py       # Métriques
│   │   ├── rate_limit.py       # Rate limiting
│   │   ├── request_id.py       # Request tracking
│   │   └── security.py         # Headers sécurité
│   ├── models/
│   │   ├── meter.py            # Modèle Compteur
│   │   ├── reading.py          # Modèle Relevé
│   │   ├── photo.py            # Modèle Photo
│   │   ├── user.py             # Modèle Utilisateur
│   │   ├── task.py             # Modèle Tâche
│   │   └── outbox.py           # Pattern Outbox
│   ├── schemas/
│   │   ├── meter.py            # Schémas Pydantic
│   │   ├── reading.py
│   │   └── ...
│   ├── services/
│   │   ├── meter_service.py    # Logique métier
│   │   ├── reading_service.py
│   │   ├── export_service.py
│   │   ├── storage_service.py  # Service S3
│   │   └── ...
│   ├── workers/
│   │   ├── tasks/
│   │   │   ├── meter_tasks.py  # Tâches Celery
│   │   │   └── export_tasks.py
│   │   └── scheduled_tasks.py  # Tâches planifiées
│   ├── monitoring/
│   │   └── metrics.py          # Métriques Prometheus
│   ├── config.py               # Configuration centrale
│   ├── database.py             # Configuration DB
│   └── main.py                 # Point d'entrée FastAPI
├── nginx/
│   └── default.conf            # Configuration Nginx
├── scripts/
│   └── ...                     # Scripts utilitaires
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_meters.py
│   └── test_readings.py
├── docker-compose.yml          # Stack principale
├── docker-compose.monitoring.yml # Stack monitoring
├── Dockerfile                  # Image Docker
├── requirements.txt            # Dépendances Python
├── alembic.ini                 # Config migrations
├── prometheus.yml              # Config Prometheus
├── grafana-dashboard.json      # Dashboard Grafana
└── README.md                   # Ce fichier
```

---

## 🛠 Technologies utilisées

### Backend
- **[FastAPI](https://fastapi.tiangolo.com/)** - Framework web moderne et performant
- **[SQLAlchemy](https://www.sqlalchemy.org/)** - ORM Python
- **[Alembic](https://alembic.sqlalchemy.org/)** - Migrations de base de données
- **[Pydantic](https://pydantic-docs.helpmanual.io/)** - Validation de données
- **[Celery](https://docs.celeryq.dev/)** - Tâches asynchrones
- **[Redis](https://redis.io/)** - Cache et broker

### Base de données
- **[PostgreSQL](https://www.postgresql.org/)** 17 - Base de données principale

### Stockage
- **[Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)** - Client S3 Python

### Sécurité
- **[python-jose](https://python-jose.readthedocs.io/)** - JWT tokens
- **[passlib](https://passlib.readthedocs.io/)** - Hash des mots de passe
- **[bcrypt](https://github.com/pyca/bcrypt/)** - Algorithme de hash

### Monitoring
- **[Prometheus](https://prometheus.io/)** - Métriques
- **[Grafana](https://grafana.com/)** - Dashboards
- **[Flower](https://flower.readthedocs.io/)** - Monitoring Celery

### Développement
- **[Pytest](https://docs.pytest.org/)** - Framework de tests
- **[Black](https://black.readthedocs.io/)** - Formatage de code
- **[Ruff](https://beta.ruff.rs/)** - Linter Python

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Voici comment contribuer :

1. **Fork** le projet
2. Créer une **branche feature** (`git checkout -b feature/AmazingFeature`)
3. **Commit** vos changements (`git commit -m 'Add some AmazingFeature'`)
4. **Push** vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une **Pull Request**

### Standards de code

- Suivre PEP 8
- Ajouter des tests pour les nouvelles fonctionnalités
- Documenter les fonctions et classes
- Mettre à jour le README si nécessaire

---

## 📝 License

Ce projet est sous licence commerciale. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 💬 Support

Pour toute question ou problème :

- 📧 **Email** : support@metersync.com
- 🐛 **Issues** : [GitHub Issues](https://github.com/DinoRu/metrix-api/issues)
- 📚 **Documentation** : https://docs.metersync.com

---

## 🙏 Remerciements

- FastAPI pour son framework exceptionnel
- La communauté Python pour les excellentes bibliothèques
- Tous les contributeurs du projet

---

**Développé avec ❤️ par l'équipe MeterSync**
