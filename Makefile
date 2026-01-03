.PHONY: help deploy update start stop restart logs logs-api logs-db logs-celery status monitor backup restore clean build migrate shell shell-db test health

# Couleurs pour l'aide
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

help: ## Afficher cette aide
	@echo "=========================================="
	@echo "🚀 Commandes disponibles pour l'API"
	@echo "=========================================="
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(BLUE)%-15s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ Déploiement

deploy: ## Déploiement complet de l'application
	@./deploy.sh

update: ## Mise à jour de l'application
	@./update.sh

build: ## Reconstruire les images Docker
	docker-compose build --no-cache

##@ Gestion des Services

start: ## Démarrer tous les services
	docker-compose up -d

stop: ## Arrêter tous les services
	docker-compose down

restart: ## Redémarrer tous les services
	docker-compose restart

restart-api: ## Redémarrer uniquement l'API
	docker-compose restart api

##@ Logs

logs: ## Voir tous les logs en temps réel
	docker-compose logs -f

logs-api: ## Voir les logs de l'API
	docker-compose logs -f api

logs-db: ## Voir les logs de la base de données
	docker-compose logs -f db

logs-celery: ## Voir les logs de Celery Worker
	docker-compose logs -f celery_worker

logs-all: ## Voir les derniers logs de tous les services
	docker-compose logs --tail=50

logs-errors: ## Voir uniquement les erreurs
	@./logs.sh

##@ Monitoring

status: ## Voir l'état des services
	docker-compose ps

monitor: ## Monitoring complet de l'application
	@./monitor.sh

health: ## Vérifier le healthcheck de l'API
	@curl -f http://localhost:8000/health && echo " ✓ API OK" || echo " ✗ API KO"

stats: ## Voir l'utilisation des ressources
	docker stats

##@ Base de Données

migrate: ## Exécuter les migrations
	docker-compose run --rm migrate

backup: ## Créer un backup de la base de données
	@./backup.sh

restore: ## Restaurer un backup
	@./restore.sh

shell-db: ## Ouvrir un shell PostgreSQL
	docker-compose exec db psql -U $(POSTGRES_USER:-api_user) -d $(POSTGRES_DB:-api_database)

##@ Développement

shell: ## Ouvrir un shell dans le container API
	docker-compose exec api bash

shell-worker: ## Ouvrir un shell dans le container Celery Worker
	docker-compose exec celery_worker bash

test: ## Exécuter les tests (à configurer)
	docker-compose exec api pytest

##@ Nettoyage

clean: ## Arrêter et supprimer les containers
	docker-compose down

clean-all: ## Nettoyage complet (containers + volumes)
	docker-compose down -v

clean-docker: ## Nettoyage complet de Docker (⚠️ supprime tout)
	@./cleanup.sh

##@ Utilitaires

flower: ## Ouvrir Flower dans le navigateur
	@echo "Ouvrez http://localhost:5555 dans votre navigateur"

docs: ## Ouvrir la documentation de l'API
	@echo "Ouvrez http://localhost:8000/docs dans votre navigateur"

env: ## Afficher les variables d'environnement (masquées)
	@echo "Variables d'environnement:"
	@docker-compose config | grep -v "password\|secret\|key" | head -20

permissions: ## Corriger les permissions des scripts
	chmod +x *.sh

##@ Production

prod-deploy: build migrate start ## Déploiement en production (build + migrate + start)
	@echo "✓ Déploiement en production terminé"

prod-update: backup update ## Mise à jour en production (backup + update)
	@echo "✓ Mise à jour en production terminée"

##@ Docker

docker-ps: ## Liste de tous les containers Docker
	docker ps -a

docker-images: ## Liste de toutes les images Docker
	docker images

docker-networks: ## Liste de tous les networks Docker
	docker network ls

docker-volumes: ## Liste de tous les volumes Docker
	docker volume ls

docker-clean: ## Nettoyer les ressources Docker inutilisées
	docker system prune -f

docker-clean-all: ## Nettoyer toutes les ressources Docker
	docker system prune -af --volumes