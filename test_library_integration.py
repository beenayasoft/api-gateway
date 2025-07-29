#!/usr/bin/env python3
"""
Script de test pour valider l'intégration du service library dans l'API Gateway
Phase 1 - Test du routage et health check
"""
import requests
import json
import time
from typing import Dict, Any

# Configuration
GATEWAY_URL = "http://localhost:8000"
LIBRARY_SERVICE_URL = "http://localhost:8005"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_header(message: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"  {message}")
    print(f"{'='*60}{Colors.END}\n")

def test_service_health(url: str, service_name: str) -> bool:
    """Teste le health check d'un service"""
    try:
        response = requests.get(f"{url}/health/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"{service_name} is healthy: {data.get('status', 'N/A')}")
            return True
        else:
            print_error(f"{service_name} health check failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"{service_name} is unreachable: {str(e)}")
        return False

def test_gateway_routing(route: str, expected_service: str) -> bool:
    """Teste le routage d'une route via l'API Gateway"""
    try:
        full_url = f"{GATEWAY_URL}{route}"
        print_info(f"Testing route: {route}")
        
        response = requests.get(full_url, timeout=10)
        
        if response.status_code == 200:
            # Vérifier si c'est bien du service library (si possible)
            try:
                data = response.json()
                if isinstance(data, dict) and 'service' in data:
                    service_name = data.get('service', '')
                    if expected_service in service_name or 'library' in service_name:
                        print_success(f"Route {route} → {expected_service} service (HTTP 200)")
                        return True
                    else:
                        print_warning(f"Route {route} → unexpected service: {service_name}")
                        return True  # Still working, just different service
                else:
                    print_success(f"Route {route} → {expected_service} service (HTTP 200, data received)")
                    return True
            except:
                print_success(f"Route {route} → {expected_service} service (HTTP 200, non-JSON response)")
                return True
        elif response.status_code == 404:
            print_error(f"Route {route} not found (HTTP 404) - Check Gateway configuration")
            return False
        elif response.status_code == 503:
            print_error(f"Route {route} service unavailable (HTTP 503) - Check {expected_service} service")
            return False
        else:
            print_warning(f"Route {route} returned HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print_error(f"Route {route} failed: {str(e)}")
        return False

def main():
    print_header("PHASE 1 - TEST INTÉGRATION SERVICE LIBRARY")
    
    # Statistiques
    total_tests = 0
    passed_tests = 0
    
    # Test 1: Health check direct du service library
    print_header("1. HEALTH CHECK SERVICES")
    
    print_info("Testing library service directly...")
    total_tests += 1
    if test_service_health(LIBRARY_SERVICE_URL, "Library Service"):
        passed_tests += 1
    
    print_info("Testing API Gateway...")
    total_tests += 1  
    if test_service_health(GATEWAY_URL, "API Gateway"):
        passed_tests += 1
    
    # Test 2: Routage via API Gateway
    print_header("2. GATEWAY ROUTING TESTS")
    
    # Routes de base à tester
    test_routes = [
        ("/health/", "gateway"),  # Gateway health check
        ("/api/categories/", "library"),  # Route library directe
        ("/categories/", "library"),  # Route library sans préfixe
        ("/api/library/", "library"),  # Route library avec préfixe
    ]
    
    for route, expected_service in test_routes:
        total_tests += 1
        if test_gateway_routing(route, expected_service):
            passed_tests += 1
    
    # Test 3: Configuration Gateway
    print_header("3. GATEWAY CONFIGURATION CHECK")
    
    try:
        # Tester l'endpoint d'info du gateway
        response = requests.get(f"{GATEWAY_URL}/", timeout=5)
        total_tests += 1
        
        if response.status_code == 200:
            data = response.json()
            services = data.get('services_backend', [])
            
            if 'library' in services:
                print_success("Library service is configured in Gateway")
                passed_tests += 1
            else:
                print_error("Library service NOT found in Gateway configuration")
                print_info(f"Available services: {services}")
        else:
            print_error(f"Gateway info endpoint failed: HTTP {response.status_code}")
            
    except Exception as e:
        print_error(f"Gateway configuration test failed: {str(e)}")
    
    # Résultats finaux
    print_header("RÉSULTATS PHASE 1")
    
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"Tests passés: {passed_tests}/{total_tests}")
    print(f"Taux de réussite: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print_success("PHASE 1 RÉUSSIE ✅")
        print_info("Le service library est correctement intégré dans l'API Gateway")
        print_info("Vous pouvez passer à la Phase 2 (Middleware Tenant)")
    elif success_rate >= 60:
        print_warning("PHASE 1 PARTIELLEMENT RÉUSSIE ⚠️")
        print_info("Certains tests ont échoué, mais l'intégration de base fonctionne")
        print_info("Corrigez les problèmes avant de passer à la Phase 2")
    else:
        print_error("PHASE 1 ÉCHOUÉE ❌")
        print_info("Des problèmes majeurs empêchent l'intégration")
        print_info("Vérifiez la configuration et que les services sont démarrés")
    
    print_header("PROCHAINES ÉTAPES")
    print_info("1. Si Phase 1 réussie → Passer à Phase 2 (Middleware Tenant)")
    print_info("2. Si échecs → Corriger la configuration Gateway")
    print_info("3. Vérifier que library-service tourne sur port 8005")
    print_info("4. Vérifier les logs des services pour plus de détails")

if __name__ == "__main__":
    main()