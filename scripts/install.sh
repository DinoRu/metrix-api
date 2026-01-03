#!/bin/bash

# Script d'installation initiale sur le VPS
# À exécuter UNE SEULE FOIS lors de la première installation

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "🔧 Installation initiale sur VPS"
echo "=========================================="

# Vérifier qu'on est sur Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}✗ Ce script doit être exécuté sur Linux${NC}"
    exit 1
fi

# 1. Mise à jour du système
echo ""
echo -e "${BLUE}1. Mise à jour du système...${NC}"
sudo apt update
sudo apt upgrade -y
echo -e "${GREEN}✓ Système mis à jour${NC}"

# 2. Installation des dépendances
echo ""
echo -e "${BLUE}2. Installation des dépendances...${NC}"
sudo apt install -y \
    curl \
    wget \
    git \
    make \
    vim \
    htop \
    ufw \
    fail2ban
echo -e "${GREEN}✓ Dépendances installées${NC}"

# 3. Vérifier Docker
echo ""
echo -e "${BLUE}3. Vérification de Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker est déjà installé ($(docker --version))${NC}"
else
    echo -e "${YELLOW}⚠️  Docker n'est pas installé${NC}"
    read -p "Voulez-vous installer Docker? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        echo -e "${GREEN}✓ Docker installé${NC}"
        echo -e "${YELLOW}⚠️  Vous devez vous reconnecter pour que les changements prennent effet${NC}"
    fi
fi

# 4. Vérifier Docker Compose
echo ""
echo -e "${BLUE}4. Vérification de Docker Compose...${NC}"
if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓ Docker Compose est déjà installé ($(docker-compose --version))${NC}"
else
    echo -e "${YELLOW}⚠️  Docker Compose n'est pas installé${NC}"
    read -p "Voulez-vous installer Docker Compose? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo apt install -y docker-compose
        echo -e "${GREEN}✓ Docker Compose installé${NC}"
    fi
fi

# 5. Configuration du firewall
echo ""
echo -e "${BLUE}5. Configuration du firewall (UFW)...${NC}"
read -p "Voulez-vous configurer le firewall? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable
    echo -e "${GREEN}✓ Firewall configuré${NC}"
    sudo ufw status
fi

# 6. Créer la structure des répertoires
echo ""
echo -e "${BLUE}6. Création de la structure des répertoires...${NC}"
mkdir -p ~/mon-api/{backups,logs,nginx}
echo -e "${GREEN}✓ Répertoires créés${NC}"

# 7. Rendre les scripts exécutables
echo ""
echo -e "${BLUE}7. Configuration des permissions...${NC}"
if [ -f "deploy.sh" ]; then
    chmod +x *.sh 2>/dev/null || true
    echo -e "${GREEN}✓ Scripts rendus exécutables${NC}"
fi

# 8. Créer le fichier .env exemple
echo ""
echo -e "${BLUE}8. Création du fichier .env exemple...${NC}"
if [ ! -f "app/.env" ]; then
    mkdir -p app
    cat > app/.env.example << 'EOF'
# Base de données
POSTGRES_USER=api_user
POSTGRES_PASSWORD=CHANGEZ_MOI_MOT_DE_PASSE_SECURISE
POSTGRES_DB=api_database
DATABASE_URL=postgresql://api_user:CHANGEZ_MOI_MOT_DE_PASSE_SECURISE@db:5432/api_database

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Application
APP_NAME=Mon API
DEBUG=False
SECRET_KEY=CHANGEZ_MOI_CLE_SECRETE_32_CARACTERES_MINIMUM
API_V1_STR=/api/v1

# JWT
JWT_SECRET_KEY=CHANGEZ_MOI_JWT_SECRET_32_CARACTERES_MINIMUM
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environnement
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}✓ Fichier .env.example créé${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Copiez et configurez app/.env.example vers app/.env${NC}"
else
    echo -e "${YELLOW}⚠️  Le fichier app/.env existe déjà${NC}"
fi

# 9. Configuration de fail2ban (protection contre les attaques)
echo ""
echo -e "${BLUE}9. Configuration de fail2ban...${NC}"
read -p "Voulez-vous configurer fail2ban? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
    echo -e "${GREEN}✓ fail2ban configuré et activé${NC}"
fi

# 10. Recommandations de sécurité
echo ""
echo "=========================================="
echo -e "${YELLOW}📋 Recommandations de Sécurité${NC}"
echo "=========================================="
echo ""
echo "1. Créez et configurez le fichier app/.env:"
echo "   cp app/.env.example app/.env"
echo "   nano app/.env"
echo ""
echo "2. Générez des clés secrètes sécurisées:"
echo "   python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
echo ""
echo "3. Configurez SSH avec authentification par clé:"
echo "   - Désactivez l'authentification par mot de passe"
echo "   - Changez le port SSH par défaut"
echo ""
echo "4. Configurez des backups automatiques"
echo ""
echo "5. Activez les mises à jour automatiques:"
echo "   sudo apt install unattended-upgrades"
echo ""

# 11. Prochaines étapes
echo "=========================================="
echo -e "${GREEN}✅ Installation initiale terminée!${NC}"
echo "=========================================="
echo ""
echo "📝 Prochaines étapes:"
echo ""
echo "1. Configurez le fichier .env:"
echo "   cp app/.env.example app/.env"
echo "   nano app/.env"
echo ""
echo "2. Transférez votre code:"
echo "   git clone <votre-repo>"
echo "   # ou utilisez scp/rsync"
echo ""
echo "3. Déployez l'application:"
echo "   ./deploy.sh"
echo ""
echo "4. Vérifiez le déploiement:"
echo "   make monitor"
echo "   # ou ./monitor.sh"
echo ""
echo "📚 Documentation complète: GUIDE_DEPLOIEMENT.md"
echo ""

# Vérifier si un redémarrage est nécessaire
if [ -f /var/run/reboot-required ]; then
    echo -e "${YELLOW}⚠️  Un redémarrage du système est recommandé${NC}"
    read -p "Voulez-vous redémarrer maintenant? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo reboot
    fi
fi