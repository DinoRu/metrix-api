#!/bin/bash

# Script de mise à jour de l'application

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "🔄 Mise à jour de l'application"
echo "=========================================="

# 1. Backup de la base de données
echo ""
echo -e "${BLUE}1. Création d'un backup de sécurité...${NC}"
if [ -f "./backup.sh" ]; then
    ./backup.sh
else
    echo -e "${YELLOW}⚠️  Script de backup non trouvé, backup manuel recommandé${NC}"
    read -p "Continuer sans backup? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 2. Récupérer les dernières modifications (si Git)
echo ""
echo -e "${BLUE}2. Récupération des dernières modifications...${NC}"
if [ -d ".git" ]; then
    git pull
    echo -e "${GREEN}✓ Code mis à jour${NC}"
else
    echo -e "${YELLOW}⚠️  Dépôt Git non détecté, assurez-vous d'avoir les derniers fichiers${NC}"
fi

# 3. Arrêter les services
echo ""
echo -e "${BLUE}3. Arrêt des services...${NC}"
docker-compose down
echo -e "${GREEN}✓ Services arrêtés${NC}"

# 4. Reconstruire les images
echo ""
echo -e "${BLUE}4. Reconstruction des images Docker...${NC}"
docker-compose build --no-cache
echo -e "${GREEN}✓ Images reconstruites${NC}"

# 5. Démarrer les services
echo ""
echo -e "${BLUE}5. Démarrage des services...${NC}"
docker-compose up -d
echo -e "${GREEN}✓ Services démarrés${NC}"

# 6. Attendre que les services soient prêts
echo ""
echo -e "${BLUE}6. Attente du démarrage complet...${NC}"
sleep 10

# 7. Exécuter les migrations
echo ""
echo -e "${BLUE}7. Exécution des migrations...${NC}"
docker-compose run --rm migrate
echo -e "${GREEN}✓ Migrations appliquées${NC}"

# 8. Vérifier l'état
echo ""
echo -e "${BLUE}8. Vérification de l'état...${NC}"
docker-compose ps

# 9. Test du healthcheck
echo ""
echo -e "${BLUE}9. Test du healthcheck...${NC}"
sleep 5
if docker-compose exec -T api curl -f http://localhost:8000/health 2>/dev/null; then
    echo -e "${GREEN}✓ API opérationnelle${NC}"
else
    echo -e "${YELLOW}⚠️  Le healthcheck a échoué, vérifiez les logs${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Mise à jour terminée!${NC}"
echo "=========================================="
echo ""
echo "📝 Vérifiez les logs avec: docker-compose logs -f api"
echo ""