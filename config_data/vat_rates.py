"""
Configuration des taux de TVA par pays
Données de référence réglementaires
"""

VAT_RATES_CONFIG = {
    # France
    "FR": [
        {
            'id': 'fr_vat_0',
            'code': "0", 
            'name': "Exonéré", 
            'rate': 0.0,
            'rate_display': "0%",
            'description': "Exonéré de TVA",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'fr_vat_5_5',
            'code': "5.5", 
            'name': "Taux réduit", 
            'rate': 5.5,
            'rate_display': "5,5%",
            'description': "Taux réduit (travaux d'amélioration énergétique)",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'fr_vat_10',
            'code': "10", 
            'name': "Taux intermédiaire", 
            'rate': 10.0,
            'rate_display': "10%",
            'description': "Taux intermédiaire (travaux, restauration)",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'fr_vat_20',
            'code': "20", 
            'name': "Taux normal", 
            'rate': 20.0,
            'rate_display': "20%",
            'description': "Taux normal français",
            'is_default': True,
            'is_active': True
        }
    ],
    
    # Belgique
    "BE": [
        {
            'id': 'be_vat_0',
            'code': "0", 
            'name': "Exonéré", 
            'rate': 0.0,
            'rate_display': "0%",
            'description': "Exonéré de TVA",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'be_vat_6',
            'code': "6", 
            'name': "Taux réduit", 
            'rate': 6.0,
            'rate_display': "6%",
            'description': "Taux réduit belge",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'be_vat_12',
            'code': "12", 
            'name': "Taux intermédiaire", 
            'rate': 12.0,
            'rate_display': "12%",
            'description': "Taux intermédiaire belge",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'be_vat_21',
            'code': "21", 
            'name': "Taux normal", 
            'rate': 21.0,
            'rate_display': "21%",
            'description': "Taux normal belge",
            'is_default': True,
            'is_active': True
        }
    ],
    
    # Espagne
    "ES": [
        {
            'id': 'es_vat_0',
            'code': "0", 
            'name': "Exento", 
            'rate': 0.0,
            'rate_display': "0%",
            'description': "Exento de IVA",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'es_vat_4',
            'code': "4", 
            'name': "Tipo superreducido", 
            'rate': 4.0,
            'rate_display': "4%",
            'description': "Tipo superreducido español",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'es_vat_10',
            'code': "10", 
            'name': "Tipo reducido", 
            'rate': 10.0,
            'rate_display': "10%",
            'description': "Tipo reducido español",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'es_vat_21',
            'code': "21", 
            'name': "Tipo general", 
            'rate': 21.0,
            'rate_display': "21%",
            'description': "Tipo general español",
            'is_default': True,
            'is_active': True
        }
    ],
    
    # Maroc
    "MA": [
        {
            'id': 'ma_vat_0',
            'code': "0", 
            'name': "Exonéré", 
            'rate': 0.0,
            'rate_display': "0%",
            'description': "Exonéré de TVA",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'ma_vat_7',
            'code': "7", 
            'name': "Taux réduit", 
            'rate': 7.0,
            'rate_display': "7%",
            'description': "Taux réduit marocain",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'ma_vat_10',
            'code': "10", 
            'name': "Taux intermédiaire", 
            'rate': 10.0,
            'rate_display': "10%",
            'description': "Taux intermédiaire marocain",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'ma_vat_20',
            'code': "20", 
            'name': "Taux normal", 
            'rate': 20.0,
            'rate_display': "20%",
            'description': "Taux normal marocain",
            'is_default': True,
            'is_active': True
        }
    ]
}

def get_vat_rates_for_country(country_code: str):
    """Récupère les taux de TVA pour un pays donné"""
    country_upper = country_code.upper()
    return VAT_RATES_CONFIG.get(country_upper, VAT_RATES_CONFIG.get('FR', []))

def get_supported_countries():
    """Retourne la liste des pays supportés"""
    return list(VAT_RATES_CONFIG.keys())

def get_default_vat_rate_for_country(country_code: str):
    """Récupère le taux de TVA par défaut pour un pays"""
    rates = get_vat_rates_for_country(country_code)
    default_rate = next((rate for rate in rates if rate.get('is_default')), None)
    return default_rate or rates[0] if rates else None