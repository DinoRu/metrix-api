#!/bin/bash

# Script de backup de la base de données PostgreSQL

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "💾 Backup de la base de données"
echo "=========================================="

# Créer le répertoire de backup s'il n'existe pas
mkdir -p "$BACKUP_DIR"

# Vérifier que le container db est en cours d'exécution
if ! docker-compose ps db | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  Le container de base de données n'est pas en cours d'exécution${NC}"
    exit 1
fi

# Effectuer le backup
echo "Création du backup..."
docker-compose exec -T db pg_dump -U ${POSTGRES_USER:-api_user} ${POSTGRES_DB:-api_database} > "$BACKUP_FILE"

# Compresser le backup
echo "Compression du backup..."
gzip "$BACKUP_FILE"

echo -e "${GREEN}✓ Backup créé avec succès: ${BACKUP_FILE}.gz${NC}"
echo "Taille: $(du -h ${BACKUP_FILE}.gz | cut -f1)"

# Nettoyer les anciens backups (garder les 7 derniers)
echo ""
echo "Nettoyage des anciens backups (conservation des 7 derniers)..."
ls -t ${BACKUP_DIR}/db_backup_*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm
echo -e "${GREEN}✓ Nettoyage terminé${NC}"

# Lister les backups disponibles
echo ""
echo "Backups disponibles:"
ls -lh ${BACKUP_DIR}/db_backup_*.sql.gz 2>/dev/null || echo "Aucun backup trouvé"