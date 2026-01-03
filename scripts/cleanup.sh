#!/bin/bash

# Script de nettoyage complet de l'environnement Docker
# ⚠️  ATTENTION: Ce script supprime TOUT (containers, networks, volumes, images)

set -e

echo "=========================================="
echo "🧹 Nettoyage complet de Docker"
echo "=========================================="

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}⚠️  ATTENTION: Ce script va supprimer:${NC}"
echo "  - Tous les containers"
echo "  - Tous les networks personnalisés"
echo "  - Tous les volumes"
echo "  - Toutes les images"
echo ""
read -p "Êtes-vous sûr de vouloir continuer? (yes/NO): " -r
echo

if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "Opération annulée."
    exit 0
fi

echo -e "${YELLOW}Arrêt de tous les containers...${NC}"
docker stop $(docker ps -aq) 2>/dev/null || true

echo -e "${YELLOW}Suppression de tous les containers...${NC}"
docker rm -f $(docker ps -aq) 2>/dev/null || true

echo -e "${YELLOW}Suppression de tous les networks...${NC}"
docker network prune -f

echo -e "${YELLOW}Suppression de tous les volumes...${NC}"
docker volume prune -f

echo -e "${YELLOW}Suppression de toutes les images...${NC}"
docker image prune -af

echo -e "${YELLOW}Nettoyage du cache de build...${NC}"
docker builder prune -af

echo ""
echo "✅ Nettoyage complet terminé!"
echo ""
docker system df