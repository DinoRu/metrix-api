#!/bin/bash

# Script de déploiement pour l'API
# Ce script nettoie l'environnement Docker et déploie l'application

set -e  # Arrêter le script en cas d'erreur

echo "=========================================="
echo "🚀 Déploiement de l'API"
echo "=========================================="

# Couleurs pour les messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log_info() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

# 1. Arrêter tous les containers en cours
echo ""
log_info "Arrêt de tous les containers en cours d'exécution..."
if [ "$(docker ps -q)" ]; then
    docker stop $(docker ps -q)
    log_info "Containers arrêtés"
else
    log_warn "Aucun container en cours d'exécution"
fi

# 2. Supprimer tous les containers
echo ""
log_info "Suppression de tous les containers..."
if [ "$(docker ps -aq)" ]; then
    docker rm -f $(docker ps -aq)
    log_info "Containers supprimés"
else
    log_warn "Aucun container à supprimer"
fi

# 3. Supprimer tous les networks personnalisés (sauf les defaults)
echo ""
log_info "Suppression des networks personnalisés..."
CUSTOM_NETWORKS=$(docker network ls --filter type=custom -q)
if [ ! -z "$CUSTOM_NETWORKS" ]; then
    docker network rm $CUSTOM_NETWORKS 2>/dev/null || log_warn "Certains networks sont toujours en cours d'utilisation"
    log_info "Networks personnalisés supprimés"
else
    log_warn "Aucun network personnalisé à supprimer"
fi

# 4. Nettoyer les images non utilisées (optionnel)
echo ""
read -p "Voulez-vous nettoyer les images Docker non utilisées? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Nettoyage des images non utilisées..."
    docker image prune -af
    log_info "Images nettoyées"
fi

# 5. Vérifier la présence du fichier .env
echo ""
log_info "Vérification des fichiers requis..."
if [ ! -f "./app/.env" ]; then
    log_error "ERREUR: Le fichier ./app/.env est manquant!"
    log_warn "Créez le fichier .env avec les variables nécessaires avant de continuer"
    exit 1
fi
log_info "Fichier .env trouvé"

# 6. Vérifier la présence des fichiers docker-compose et Dockerfile
if [ ! -f "docker-compose.yml" ]; then
    log_error "ERREUR: docker-compose.yml est manquant!"
    exit 1
fi

if [ ! -f "Dockerfile" ]; then
    log_error "ERREUR: Dockerfile est manquant!"
    exit 1
fi

# 7. Build et démarrage des services
echo ""
log_info "Construction des images Docker..."
docker-compose build --no-cache

echo ""
log_info "Démarrage des services..."
docker-compose up -d

# 8. Attendre que les services soient prêts
echo ""
log_info "Attente du démarrage des services..."
sleep 10

# 9. Exécuter les migrations
echo ""
log_info "Exécution des migrations de base de données..."
docker-compose run --rm migrate
log_info "Migrations terminées"

# 10. Vérifier l'état des services
echo ""
log_info "État des services:"
docker-compose ps

# 11. Vérifier les logs de l'API
echo ""
log_info "Derniers logs de l'API:"
docker-compose logs --tail=20 api

# 12. Tester le healthcheck
echo ""
log_info "Test du healthcheck de l'API..."
sleep 5
if docker-compose exec -T api curl -f http://localhost:8000/health 2>/dev/null; then
    log_info "API opérationnelle! ✅"
else
    log_warn "Le healthcheck a échoué. Vérifiez les logs avec: docker-compose logs api"
fi

# Afficher les informations de connexion
echo ""
echo "=========================================="
echo "✅ Déploiement terminé!"
echo "=========================================="
echo ""
echo "📋 Informations de connexion:"
echo "  - API: http://localhost:8000"
echo "  - Documentation API: http://localhost:8000/docs"
echo "  - Flower (monitoring Celery): http://localhost:5555"
echo ""
echo "📝 Commandes utiles:"
echo "  - Voir les logs: docker-compose logs -f [service]"
echo "  - Arrêter les services: docker-compose down"
echo "  - Redémarrer un service: docker-compose restart [service]"
echo "  - Voir l'état: docker-compose ps"
echo ""