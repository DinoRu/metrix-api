# =========================
# Étape 1 : Builder
# =========================
FROM python:3.11-slim AS builder

WORKDIR /app

# Installer dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements et installer dans un répertoire temporaire
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt gunicorn uvicorn

# Copier le code de l'application
COPY app /app/app

# =========================
# Étape 2 : Image finale
# =========================
FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système de runtime
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier packages Python et binaires depuis le builder
COPY --from=builder /install /usr/local
COPY --from=builder /app /app

# Exposer le port de l'API
EXPOSE 8000

# Définir les variables d'environnement (optionnel si déjà dans docker-compose)
# ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:$PATH"
# Commande par défaut : Gunicorn pour l'API
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--log-level", "info"]
