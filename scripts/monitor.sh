#!/bin/bash

# Script de monitoring de l'API

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo "=========================================="
echo "📊 Monitoring de l'API"
echo "=========================================="
echo ""

# Fonction pour vérifier un service
check_service() {
    local service=$1
    local status=$(docker-compose ps $service 2>/dev/null | grep -v "Name" | awk '{print $4}')
    
    if [ -z "$status" ]; then
        echo -e "${service}: ${RED}✗ Non démarré${NC}"
        return 1
    elif [[ $status == *"Up"* ]]; then
        echo -e "${service}: ${GREEN}✓ Opérationnel${NC} ($status)"
        return 0
    else
        echo -e "${service}: ${YELLOW}⚠ ${status}${NC}"
        return 1
    fi
}

# Vérifier tous les services
echo -e "${BLUE}État des Services:${NC}"
echo "---"
check_service "api"
check_service "db"
check_service "redis"
check_service "celery_worker"
check_service "celery_beat"
check_service "flower"

echo ""
echo -e "${BLUE}Healthchecks:${NC}"
echo "---"

# Test API health
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "API Health: ${GREEN}✓ OK${NC}"
else
    echo -e "API Health: ${RED}✗ Échec${NC}"
fi

# Test Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "Redis: ${GREEN}✓ OK${NC}"
else
    echo -e "Redis: ${RED}✗ Échec${NC}"
fi

# Test PostgreSQL
if docker-compose exec -T db pg_isready -U ${POSTGRES_USER:-api_user} > /dev/null 2>&1; then
    echo -e "PostgreSQL: ${GREEN}✓ OK${NC}"
else
    echo -e "PostgreSQL: ${RED}✗ Échec${NC}"
fi

echo ""
echo -e "${BLUE}Utilisation des Ressources:${NC}"
echo "---"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -7

echo ""
echo -e "${BLUE}Espace Disque:${NC}"
echo "---"
df -h / | tail -1 | awk '{print "Système: " $3 " / " $2 " utilisé (" $5 ")"}'
docker system df | grep "Images\|Containers\|Local Volumes" | awk '{print $1 ": " $3 " (" $4 ")"}'

echo ""
echo -e "${BLUE}Derniers Logs (API):${NC}"
echo "---"
docker-compose logs --tail=5 api 2>/dev/null || echo "Aucun log disponible"

echo ""
echo -e "${BLUE}Informations:${NC}"
echo "---"
echo "Dernière mise à jour: $(date)"
echo "Uptime containers:"
docker-compose ps --format "table {{.Name}}\t{{.Status}}" | grep -v "Name"

echo ""
echo "=========================================="
echo "💡 Commandes utiles:"
echo "  - Logs en direct: docker-compose logs -f api"
echo "  - Redémarrer: docker-compose restart"
echo "  - État détaillé: docker-compose ps"
echo "=========================================="