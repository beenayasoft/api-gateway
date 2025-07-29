# Configuration d'environnement - API Gateway

## Variables d'environnement requises

Créez un fichier `.env` dans le répertoire `soa/api-gateway/` avec les variables suivantes :

```bash
# Configuration API Gateway
DEBUG=True
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8000

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here-change-in-production
JWT_ALGORITHM=HS256

# Services Backend
TENANT_SERVICE_URL=http://localhost:8001
AUTH_SERVICE_URL=http://localhost:8002
CRM_SERVICE_URL=http://localhost:8003
DOCUMENT_SERVICE_URL=http://localhost:8004
```

## Services intégrés

- **Tenant Service** (port 8001) : Gestion des tenants
- **Auth Service** (port 8002) : Authentification et autorisation
- **CRM Service** (port 8003) : Tiers et opportunités
- **Document Service** (port 8004) : **NOUVEAU** - Devis et factures unifiés

## Routes disponibles

### Routes legacy (compatibilité frontend)
- `/api/devis/*` → Document Service (`/api/quotes/*`)
- `/api/factures/*` → Document Service (`/api/invoices/*`)
- `/api/tiers/*` → CRM Service
- `/api/opportunites/*` → CRM Service
- `/api/auth/*` → Auth Service
- `/api/tenants/*` → Tenant Service

### Routes modernes
- `/api/quotes/*` → Document Service
- `/api/invoices/*` → Document Service

## Démarrage

```bash
cd soa/api-gateway
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r requirements.txt
```
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

## Health Check

- **Gateway** : `GET /health/`
- **Documentation** : `GET /docs` (si DEBUG=True) 