#!/bin/bash

# Script de restauration de la base de données PostgreSQL

set -e

BACKUP_DIR="./backups"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "♻️  Restauration de la base de données"
echo "=========================================="

# Vérifier que le container db est en cours d'exécution
if ! docker-compose ps db | grep -q "Up"; then
    echo -e "${RED}✗ Le container de base de données n'est pas en cours d'exécution${NC}"
    exit 1
fi

# Lister les backups disponibles
echo "Backups disponibles:"
echo ""
ls -lht ${BACKUP_DIR}/db_backup_*.sql.gz 2>/dev/null || {
    echo -e "${RED}✗ Aucun backup trouvé dans ${BACKUP_DIR}${NC}"
    exit 1
}

echo ""
echo -e "${YELLOW}⚠️  ATTENTION: Cette opération va REMPLACER toutes les données actuelles!${NC}"
read -p "Entrez le nom complet du fichier de backup à restaurer: " BACKUP_FILE

# Vérifier que le fichier existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}✗ Le fichier $BACKUP_FILE n'existe pas${NC}"
    exit 1
fi

# Confirmation finale
echo ""
echo -e "${RED}Vous êtes sur le point de restaurer: $BACKUP_FILE${NC}"
read -p "Êtes-vous absolument sûr? (yes/NO): " -r
echo

if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "Opération annulée."
    exit 0
fi

# Décompresser si nécessaire
if [[ $BACKUP_FILE == *.gz ]]; then
    echo "Décompression du backup..."
    TEMP_FILE=$(mktemp)
    gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
else
    TEMP_FILE="$BACKUP_FILE"
fi

# Arrêter l'API pendant la restauration
echo "Arrêt de l'API..."
docker-compose stop api celery_worker celery_beat

# Restaurer le backup
echo "Restauration en cours..."
docker-compose exec -T db psql -U ${POSTGRES_USER:-api_user} ${POSTGRES_DB:-api_database} < "$TEMP_FILE"

# Nettoyer le fichier temporaire
if [[ $BACKUP_FILE == *.gz ]]; then
    rm "$TEMP_FILE"
fi

# Redémarrer l'API
echo "Redémarrage de l'API..."
docker-compose start api celery_worker celery_beat

echo ""
echo -e "${GREEN}✓ Restauration terminée avec succès!${NC}"
echo "Vérifiez les logs avec: docker-compose logs -f api"