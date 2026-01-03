#!/bin/bash

# Script interactif pour visualiser les logs

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "📋 Visualisation des Logs"
echo "=========================================="
echo ""
echo "Choisissez un service:"
echo ""
echo "  1) API (FastAPI)"
echo "  2) Base de données (PostgreSQL)"
echo "  3) Redis"
echo "  4) Celery Worker"
echo "  5) Celery Beat"
echo "  6) Flower"
echo "  7) Migrations"
echo "  8) Tous les services"
echo "  9) Logs d'erreur uniquement"
echo "  0) Quitter"
echo ""
read -p "Votre choix (1-9): " choice

case $choice in
    1)
        echo -e "${BLUE}Logs de l'API (appuyez sur Ctrl+C pour quitter):${NC}"
        docker-compose logs -f --tail=100 api
        ;;
    2)
        echo -e "${BLUE}Logs PostgreSQL (appuyez sur Ctrl+C pour quitter):${NC}"
        docker-compose logs -f --tail=100 db
        ;;
    3)
        echo -e "${BLUE}Logs Redis (appuyez sur Ctrl+C pour quitter):${NC}"
        docker-compose logs -f --tail=100 redis
        ;;
    4)
        echo -e "${BLUE}Logs Celery Worker (appuyez sur Ctrl+C pour quitter):${NC}"
        docker-compose logs -f --tail=100 celery_worker
        ;;
    5)
        echo -e "${BLUE}Logs Celery Beat (appuyez sur Ctrl+C pour quitter):${NC}"
        docker-compose logs -f --tail=100 celery_beat
        ;;
    6)
        echo -e "${BLUE}Logs Flower (appuyez sur Ctrl+C pour quitter):${NC}"
        docker-compose logs -f --tail=100 flower
        ;;
    7)
        echo -e "${BLUE}Logs des Migrations:${NC}"
        docker-compose logs migrate
        ;;
    8)
        echo -e "${BLUE}Logs de tous les services (appuyez sur Ctrl+C pour quitter):${NC}"
        docker-compose logs -f --tail=50
        ;;
    9)
        echo -e "${BLUE}Logs d'erreur uniquement:${NC}"
        echo ""
        echo -e "${YELLOW}API:${NC}"
        docker-compose logs api | grep -i "error\|exception\|failed\|traceback" | tail -20
        echo ""
        echo -e "${YELLOW}Celery Worker:${NC}"
        docker-compose logs celery_worker | grep -i "error\|exception\|failed\|traceback" | tail -20
        echo ""
        echo -e "${YELLOW}Base de données:${NC}"
        docker-compose logs db | grep -i "error\|exception\|failed" | tail -20
        ;;
    0)
        echo "Au revoir!"
        exit 0
        ;;
    *)
        echo -e "${YELLOW}Choix invalide${NC}"
        exit 1
        ;;
esac