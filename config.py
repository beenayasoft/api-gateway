"""
Configuration pour l'API Gateway FastAPI - COMPATIBILITÉ FRONTEND
"""
from decouple import config

# Services backend avec mapping de compatibilité
SERVICES = {
    "tenant": {
        "url": config("TENANT_SERVICE_URL", default="http://localhost:8001"),
        "health": "/health/",
        "routes": ["/api/tenants/"]
    },
    "auth": {
        "url": config("AUTH_SERVICE_URL", default="http://localhost:8002"), 
        "health": "/health/",
        "routes": ["/api/auth/"]
    },
    "crm": {
        "url": config("CRM_SERVICE_URL", default="http://localhost:8003"),
        "health": "/health/",
        "routes": ["/api/crm/"]  # Nouvelle route unifiée
    },
    "documents": {
        "url": config("DOCUMENT_SERVICE_URL", default="http://localhost:8004"),
        "health": "/health/",
        "routes": ["/api/quotes/", "/api/invoices/", "/api/projects/", "/api/devis/", "/api/factures/", "/quotes/", "/invoices/"]
    },
    "library": {
        "url": config("LIBRARY_SERVICE_URL", default="http://localhost:8005"),
        "health": "/health/",
        "routes": ["/api/library/", "/api/categories/", "/api/fournitures/", "/api/main-oeuvre/", "/api/ouvrages/", "/api/ingredients/"]
    }
}

# Mapping de compatibilité frontend existant
LEGACY_ROUTE_MAPPING = {
    # Anciennes routes → Nouveaux services
    "/api/auth/login/": ("auth", "/api/auth/login/"),
    "/api/auth/register/": ("auth", "/api/auth/register/"),
    "/api/auth/refresh/": ("auth", "/api/auth/refresh/"),
    "/api/auth/me/": ("auth", "/api/auth/me/"),
    
    # Routes auth sans préfixe /api/
    "/auth/login/": ("auth", "/api/auth/login/"),
    "/auth/register/": ("auth", "/api/auth/register/"),
    "/auth/refresh/": ("auth", "/api/auth/refresh/"),
    "/auth/me/": ("auth", "/api/auth/me/"),
    
    # Routes tenant
    "/api/tenants/{tenant_id}/": ("tenant", "/api/tenants/{tenant_id}/"),
    "/api/tenants/": ("tenant", "/api/tenants/"),
    "/api/tenants/{tenant_id}/validate/": ("tenant", "/api/tenants/{tenant_id}/validate/"),
    "/api/tenants/{tenant_id}/stats/": ("tenant", "/api/tenants/{tenant_id}/stats/"),
    
    # Routes tenant via /api/auth/ (pour compatibilité frontend)
    "/api/auth/tenants/{tenant_id}/": ("tenant", "/api/tenants/{tenant_id}/"),
    "/api/auth/tenants/": ("tenant", "/api/tenants/"),
    "/api/auth/tenants/{tenant_id}/validate/": ("tenant", "/api/tenants/{tenant_id}/validate/"),
    "/api/auth/tenants/{tenant_id}/stats/": ("tenant", "/api/tenants/{tenant_id}/stats/"),

    # Routes tiers (redirection vers le nouveau module CRM)
    "/api/tiers/frontend_format/": ("crm", "/api/tiers/frontend_format/"),
    "/api/tiers/stats/": ("crm", "/api/tiers/stats/"),
    "/api/tiers/{id}/": ("crm", "/api/tiers/{id}/"),
    "/api/tiers/{id}/vue_360/": ("crm", "/api/tiers/{id}/vue_360/"),
    "/api/tiers/{id}/restaurer/": ("crm", "/api/tiers/{id}/restore/"),
    "/api/tiers/": ("crm", "/api/tiers/"),
    "/api/clients/": ("crm", "/api/tiers/"),
    "/api/prospects/": ("crm", "/api/tiers/"),
    "/api/fournisseurs/": ("crm", "/api/tiers/"),
    
    # Routes opportunités (redirection vers le nouveau module CRM)
    "/api/opportunities/": ("crm", "/api/opportunities/"),
    "/api/opportunities/{id}/": ("crm", "/api/opportunities/{id}/"),
    "/api/opportunities/stats/": ("crm", "/api/opportunities/stats/"),
    "/api/opportunities/kanban/": ("crm", "/api/opportunities/kanban/"),
    "/api/opportunities/{id}/update_stage/": ("crm", "/api/opportunities/{id}/update_stage/"),
    "/api/opportunities/{id}/mark_won/": ("crm", "/api/opportunities/{id}/mark_won/"),
    "/api/opportunities/{id}/mark_lost/": ("crm", "/api/opportunities/{id}/mark_lost/"),
    
    # Routes sans préfixe /api/ (redirection vers le nouveau module CRM)
    "/tiers/frontend_format/": ("crm", "/api/crm/tiers/frontend_format/"),
    "/tiers/stats/": ("crm", "/api/crm/tiers/stats/"),
    "/tiers/{id}/": ("crm", "/api/crm/tiers/{id}/"),
    "/tiers/{id}/vue_360/": ("crm", "/api/crm/tiers/{id}/vue_360/"),
    "/tiers/{id}/restaurer/": ("crm", "/api/crm/tiers/{id}/restore/"),
    "/tiers/": ("crm", "/api/crm/tiers/"),
    "/clients/": ("crm", "/api/crm/tiers/"),
    "/prospects/": ("crm", "/api/crm/tiers/"),
    "/fournisseurs/": ("crm", "/api/crm/tiers/"),
    
    # Routes opportunités sans préfixe /api/
    "/opportunities/": ("crm", "/api/crm/opportunities/"),
    "/opportunities/{id}/": ("crm", "/api/crm/opportunities/{id}/"),
    "/opportunities/stats/": ("crm", "/api/crm/opportunities/stats/"),
    "/opportunities/kanban/": ("crm", "/api/crm/opportunities/kanban/"),
    "/opportunities/{id}/update_stage/": ("crm", "/api/crm/opportunities/{id}/update_stage/"),
    "/opportunities/{id}/mark_won/": ("crm", "/api/crm/opportunities/{id}/mark_won/"),
    "/opportunities/{id}/mark_lost/": ("crm", "/api/crm/opportunities/{id}/mark_lost/"),
    
    # Routes devis (Document Service)
    "/api/devis/": ("documents", "/api/quotes/"),
    "/api/devis/stats/": ("documents", "/api/quotes/stats/"),
    "/api/devis/{id}/": ("documents", "/api/quotes/{id}/"),
    "/api/devis/{id}/send/": ("documents", "/api/quotes/{id}/send/"),
    "/api/devis/{id}/validate/": ("documents", "/api/quotes/{id}/validate/"),
    "/api/devis/{id}/convert_to_invoice/": ("documents", "/api/quotes/{id}/convert_to_invoice/"),
    "/api/devis/{id}/duplicate/": ("documents", "/api/quotes/{id}/duplicate/"),
    "/api/devis/{id}/pdf/": ("documents", "/api/quotes/{id}/pdf/"),
    "/api/devis/{id}/export/": ("documents", "/api/quotes/{id}/export/"),
    "/api/devis/{id}/items/": ("documents", "/api/quotes/{id}/items/"),
    
    # Routes factures (Document Service)
    "/api/factures/": ("documents", "/api/invoices/"),
    "/api/factures/stats/": ("documents", "/api/invoices/stats/"),
    "/api/factures/{id}/": ("documents", "/api/invoices/{id}/"),
    "/api/factures/{id}/validate/": ("documents", "/api/invoices/{id}/validate/"),
    "/api/factures/{id}/record_payment/": ("documents", "/api/invoices/{id}/record_payment/"),
    "/api/factures/{id}/create_credit_note/": ("documents", "/api/invoices/{id}/create_credit_note/"),
    "/api/factures/{id}/pdf/": ("documents", "/api/invoices/{id}/pdf/"),
    "/api/factures/{id}/export/": ("documents", "/api/invoices/{id}/export/"),
    "/api/factures/{id}/items/": ("documents", "/api/invoices/{id}/items/"),
    "/api/factures/{id}/payments/": ("documents", "/api/invoices/{id}/payments/"),
    
    # Routes nouvelles pour le frontend moderne (API directe)
    "/api/quotes/": ("documents", "/api/quotes/"),
    "/api/quotes/next-number/": ("documents", "/api/quotes/next_number/"),
    "/api/projects/next-reference/": ("documents", "/api/projects/next-reference/"),
    "/api/quote-items/": ("documents", "/api/quote-items/"),
    "/api/invoices/": ("documents", "/api/invoices/"),
    "/api/invoice-items/": ("documents", "/api/invoice-items/"),
    
    # Routes sans préfixe /api/ pour compatibilité frontend
    "/quotes/": ("documents", "/api/quotes/"),
    "/quotes/stats/": ("documents", "/api/quotes/stats/"),
    "/quotes/{id}/": ("documents", "/api/quotes/{id}/"),
    "/quotes/{id}/send/": ("documents", "/api/quotes/{id}/send/"),
    "/quotes/{id}/validate/": ("documents", "/api/quotes/{id}/validate/"),
    "/quotes/{id}/duplicate/": ("documents", "/api/quotes/{id}/duplicate/"),
    "/quotes/{id}/export/": ("documents", "/api/quotes/{id}/export/"),
    "/quotes/{id}/items/": ("documents", "/api/quotes/{id}/items/"),
    "/quote-items/": ("documents", "/api/quote-items/"),
    
    "/invoices/": ("documents", "/api/invoices/"),
    "/invoices/stats/": ("documents", "/api/invoices/stats/"),
    "/invoices/{id}/": ("documents", "/api/invoices/{id}/"),
    "/invoices/{id}/validate/": ("documents", "/api/invoices/{id}/validate/"),
    "/invoices/{id}/record_payment/": ("documents", "/api/invoices/{id}/record_payment/"),
    "/invoices/{id}/create_credit_note/": ("documents", "/api/invoices/{id}/create_credit_note/"),
    "/invoices/{id}/export/": ("documents", "/api/invoices/{id}/export/"),
    "/invoices/{id}/items/": ("documents", "/api/invoices/{id}/items/"),
    "/invoices/{id}/payments/": ("documents", "/api/invoices/{id}/payments/"),
    
    # Routes pour les taux de TVA
    "/vat-rates/": ("documents", "/api/quotes/vat-rates/"),
    "/api/quotes/vat-rates/": ("documents", "/api/quotes/vat-rates/"),
    
    # Routes pour les conditions de paiement du document-service
    "/api/quotes/payment-terms/": ("documents", "/api/payment-terms/"),
    "/payment-terms/": ("documents", "/api/payment-terms/"),
    
    # Routes tenant directes (sans préfixe /api)
    "/tenants/{tenant_id}/": ("tenant", "/api/tenants/{tenant_id}/"),
    "/tenants/{tenant_id}/validate/": ("tenant", "/api/tenants/{tenant_id}/validate/"),
    "/tenants/{tenant_id}/stats/": ("tenant", "/api/tenants/{tenant_id}/stats/"),
    "/tenants/current_tenant_info/": ("tenant", "/api/tenants/current_tenant_info/"),
    
    # Routes pour les taux de TVA du tenant (utiliser la nouvelle URL sans préfixe 'tenants/')
    "/api/tenant/vat_rates/": ("tenant", "/api/vat_rates/"),
    "/api/tenants/vat_rates/": ("tenant", "/api/vat_rates/"),
    "/tenants/vat_rates/": ("tenant", "/api/vat_rates/"),
    
    # Routes pour les conditions de paiement du tenant
    "/api/tenants/payment_terms/": ("tenant", "/api/payment_terms/"),
    "/tenants/payment_terms/": ("tenant", "/api/payment_terms/"),
    
    # Routes auth/tenants sans préfixe /api/
    "/auth/tenants/{tenant_id}/": ("tenant", "/api/tenants/current_tenant_info/"),  # Redirection vers current_tenant_info pour la mise à jour
    "/auth/tenants/": ("tenant", "/api/tenants/"),
    
    # Routes pour l'apparence des documents (tenant-service)
    "/api/document_appearance/": ("tenant", "/api/document_appearance/"),
    "/api/document_appearance/defaults/": ("tenant", "/api/document_appearance/defaults/"),
    "/api/document_appearance/templates/": ("tenant", "/api/document_appearance/templates/"),
    "/api/document_appearance/presets/": ("tenant", "/api/document_appearance/presets/"),
    "/api/document_appearance/colors/": ("tenant", "/api/document_appearance/colors/"),
    
    # Routes sans préfixe /api/ pour compatibilité
    "/document_appearance/": ("tenant", "/api/document_appearance/"),
    "/document_appearance/defaults/": ("tenant", "/api/document_appearance/defaults/"),
    "/document_appearance/templates/": ("tenant", "/api/document_appearance/templates/"),
    "/document_appearance/presets/": ("tenant", "/api/document_appearance/presets/"),
    "/document_appearance/colors/": ("tenant", "/api/document_appearance/colors/"),

    # ==================== ROUTES LIBRARY SERVICE ====================
    
    # Routes API library principales
    # NOTE: Mapping générique supprimé pour éviter les conflits avec les mappings spécifiques
    # "/api/library/": ("library", "/api/library/"),
    "/api/library/categories/": ("library", "/api/categories/"),
    "/api/library/fournitures/": ("library", "/api/fournitures/"),
    "/api/library/main-oeuvre/": ("library", "/api/main-oeuvre/"),
    "/api/library/ouvrages/": ("library", "/api/ouvrages/"),
    "/api/library/ingredients/": ("library", "/api/ingredients/"),
    "/api/library/search/": ("library", "/api/search/"),
    
    # Routes composite optimisées pour l'endpoint composite
    "/api/library/composite/": ("library", "/api/composite/"),
    "/api/library/composite/all_items/": ("library", "/api/composite/all_items/"),
    
    # Routes directes (sans préfixe library)
    "/api/categories/": ("library", "/api/categories/"),
    "/api/fournitures/": ("library", "/api/fournitures/"),
    "/api/main-oeuvre/": ("library", "/api/main-oeuvre/"),
    "/api/ouvrages/": ("library", "/api/ouvrages/"),
    "/api/ingredients/": ("library", "/api/ingredients/"),
    
    # Routes sans préfixe /api/ pour compatibilité frontend
    # NOTE: Mapping générique supprimé pour éviter les conflits
    # "/library/": ("library", "/api/library/"),
    "/categories/": ("library", "/api/categories/"),
    "/fournitures/": ("library", "/api/fournitures/"),
    "/main-oeuvre/": ("library", "/api/main-oeuvre/"),
    "/ouvrages/": ("library", "/api/ouvrages/"),
    "/ingredients/": ("library", "/api/ingredients/"),
    "/library/search/": ("library", "/api/search/"),
    
    # Routes composite sans préfixe /api/
    "/library/composite/": ("library", "/api/composite/"),
    "/library/composite/all_items/": ("library", "/api/composite/all_items/"),
    
    # Routes détaillées avec paramètres (avec préfixe library)
    "/api/library/categories/": ("library", "/api/categories/"),
    "/api/library/fournitures/": ("library", "/api/fournitures/"),
    "/api/library/main-oeuvre/": ("library", "/api/main-oeuvre/"),
    "/api/library/ouvrages/": ("library", "/api/ouvrages/"),
    "/api/library/ingredients/": ("library", "/api/ingredients/"),
    
    # Routes détaillées avec paramètres (sans préfixe library)
    "/api/categories/": ("library", "/api/categories/"),
    "/api/fournitures/": ("library", "/api/fournitures/"),
    "/api/main-oeuvre/": ("library", "/api/main-oeuvre/"),
    "/api/ouvrages/": ("library", "/api/ouvrages/"),
    "/api/ingredients/": ("library", "/api/ingredients/"),
    
    # Routes statistiques et actions spéciales
    "/api/categories/racines/": ("library", "/api/categories/racines/"),
    "/api/categories/stats/": ("library", "/api/categories/stats/"),
    "/api/fournitures/stats/": ("library", "/api/fournitures/stats/"),
    "/api/fournitures/par_categorie/": ("library", "/api/fournitures/par_categorie/"),
    "/api/main-oeuvre/stats/": ("library", "/api/main-oeuvre/stats/"),
    "/api/main-oeuvre/par_categorie/": ("library", "/api/main-oeuvre/par_categorie/"),
    "/api/ouvrages/stats/": ("library", "/api/ouvrages/stats/"),
    "/api/ouvrages/par_categorie/": ("library", "/api/ouvrages/par_categorie/"),
    "/api/ingredients/stats/": ("library", "/api/ingredients/stats/"),
    "/api/ingredients/par_ouvrage/": ("library", "/api/ingredients/par_ouvrage/"),
}

# Configuration JWT
JWT_SECRET_KEY = config("JWT_SECRET_KEY")
JWT_ALGORITHM = config("JWT_ALGORITHM", default="HS256")

# Configuration serveur
GATEWAY_HOST = config("GATEWAY_HOST", default="0.0.0.0")
GATEWAY_PORT = config("GATEWAY_PORT", default=8000, cast=int)
DEBUG = config("DEBUG", default=False, cast=bool)

# Routes publiques (pas d'authentification requise)
PUBLIC_ROUTES = [
    "/health/",
    "/docs",
    "/redoc", 
    "/openapi.json",
    "/api/auth/login/",
    "/api/auth/register/",
    "/auth/login/",
    "/auth/register/",
    "/api/tenants/",
    "/tenants/",
    "/vat-rates/",
    "/api/quotes/vat-rates/",
    # Routes publiques pour les tests library service
    "/api/library/health/",
]
