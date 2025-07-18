#!/usr/bin/env python
"""
Script de test pour vérifier l'intégration du Document Service avec l'API Gateway.
"""

import asyncio
import httpx
import json
from typing import Dict, List

# Configuration des tests
GATEWAY_URL = "http://localhost:8000"
DOCUMENT_SERVICE_URL = "http://localhost:8004"

class DocumentServiceIntegrationTester:
    """Testeur d'intégration pour le Document Service via l'API Gateway."""
    
    def __init__(self):
        self.gateway_url = GATEWAY_URL
        self.document_service_url = DOCUMENT_SERVICE_URL
        self.results = []
    
    async def test_gateway_health(self) -> Dict:
        """Test du health check de l'API Gateway."""
        
        print("🔍 Test du health check de l'API Gateway...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.gateway_url}/health/")
                
                if response.status_code == 200:
                    health_data = response.json()
                    document_service_status = health_data.get("services", {}).get("documents", {})
                    
                    return {
                        "test": "Gateway Health Check",
                        "status": "✅ PASS" if document_service_status.get("status") == "healthy" else "❌ FAIL",
                        "details": {
                            "gateway_status": health_data.get("gateway", {}).get("overall_status"),
                            "document_service": document_service_status
                        }
                    }
                else:
                    return {
                        "test": "Gateway Health Check",
                        "status": "❌ FAIL",
                        "details": f"HTTP {response.status_code}"
                    }
                    
        except Exception as e:
            return {
                "test": "Gateway Health Check",
                "status": "❌ FAIL",
                "details": f"Erreur: {str(e)}"
            }
    
    async def test_legacy_route_mapping(self) -> List[Dict]:
        """Test du mapping des routes legacy."""
        
        print("🔍 Test du mapping des routes legacy...")
        
        legacy_routes = [
            "/api/devis/",
            "/api/factures/",
            "/api/quotes/",
            "/api/invoices/"
        ]
        
        results = []
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                
                for route in legacy_routes:
                    try:
                        # Test avec un simple GET pour vérifier le routage
                        response = await client.get(
                            f"{self.gateway_url}{route}",
                            headers={"X-Tenant-ID": "test"}
                        )
                        
                        # Nous nous attendons soit à un 200, soit à un 401 (pas d'auth),
                        # mais pas à un 404 (service non trouvé)
                        is_routed_correctly = response.status_code != 404
                        
                        results.append({
                            "test": f"Route Mapping: {route}",
                            "status": "✅ PASS" if is_routed_correctly else "❌ FAIL",
                            "details": {
                                "status_code": response.status_code,
                                "routed": is_routed_correctly
                            }
                        })
                        
                    except Exception as e:
                        results.append({
                            "test": f"Route Mapping: {route}",
                            "status": "❌ FAIL",
                            "details": f"Erreur: {str(e)}"
                        })
                        
        except Exception as e:
            results.append({
                "test": "Route Mapping (Global)",
                "status": "❌ FAIL",
                "details": f"Erreur: {str(e)}"
            })
        
        return results
    
    async def test_document_service_direct(self) -> Dict:
        """Test direct du Document Service (bypass Gateway)."""
        
        print("🔍 Test direct du Document Service...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.document_service_url}/health/")
                
                if response.status_code == 200:
                    return {
                        "test": "Document Service Direct",
                        "status": "✅ PASS",
                        "details": "Service accessible directement"
                    }
                else:
                    return {
                        "test": "Document Service Direct",
                        "status": "❌ FAIL",
                        "details": f"HTTP {response.status_code}"
                    }
                    
        except Exception as e:
            return {
                "test": "Document Service Direct",
                "status": "❌ FAIL",
                "details": f"Service non accessible: {str(e)}"
            }
    
    async def test_cors_headers(self) -> Dict:
        """Test des headers CORS pour le frontend."""
        
        print("🔍 Test des headers CORS...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Simuler une requête OPTIONS pour CORS preflight
                response = await client.options(
                    f"{self.gateway_url}/api/quotes/",
                    headers={
                        "Origin": "http://localhost:3000",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "X-Tenant-ID"
                    }
                )
                
                has_cors_headers = "access-control-allow-origin" in response.headers
                
                return {
                    "test": "CORS Headers",
                    "status": "✅ PASS" if has_cors_headers else "❌ FAIL",
                    "details": {
                        "has_cors": has_cors_headers,
                        "cors_headers": {k: v for k, v in response.headers.items() if k.startswith("access-control")}
                    }
                }
                
        except Exception as e:
            return {
                "test": "CORS Headers",
                "status": "❌ FAIL",
                "details": f"Erreur: {str(e)}"
            }
    
    async def run_all_tests(self):
        """Exécute tous les tests."""
        
        print("🚀 Tests d'intégration Document Service - API Gateway")
        print("=" * 60)
        
        # Exécuter tous les tests
        results = []
        
        results.append(await self.test_gateway_health())
        results.append(await self.test_document_service_direct())
        results.extend(await self.test_legacy_route_mapping())
        results.append(await self.test_cors_headers())
        
        # Afficher les résultats
        print("\n📋 Résultats des tests :")
        print("-" * 40)
        
        passed = 0
        failed = 0
        
        for result in results:
            print(f"{result['status']} {result['test']}")
            if result.get('details'):
                print(f"   Détails: {result['details']}")
            
            if "✅ PASS" in result['status']:
                passed += 1
            else:
                failed += 1
        
        print("\n" + "=" * 60)
        print(f"📊 Résumé : {passed} tests réussis, {failed} tests échoués")
        
        if failed == 0:
            print("🎉 Tous les tests sont passés ! L'intégration est fonctionnelle.")
            return True
        else:
            print("⚠️ Certains tests ont échoué. Vérifiez la configuration.")
            return False

async def main():
    """Point d'entrée principal."""
    
    tester = DocumentServiceIntegrationTester()
    success = await tester.run_all_tests()
    
    if not success:
        print("\n🔧 Actions recommandées :")
        print("1. Vérifiez que le Document Service est démarré (port 8004)")
        print("2. Vérifiez que l'API Gateway est démarré (port 8000)")
        print("3. Vérifiez les variables d'environnement")
        print("4. Consultez les logs des services")
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main())) 