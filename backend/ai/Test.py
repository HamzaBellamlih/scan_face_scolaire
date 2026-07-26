"""
Script de test pour vérifier que les routes fonctionnent
À lancer APRÈS avoir démarré Django : python manage.py runserver 8000
"""

import requests
import json

API_BASE = "http://127.0.0.1:8008/api"

print("="*60)
print("🧪 TEST DES ROUTES API")
print("="*60)

# ──────────────────────────────────────────────────────────────────
# 1. Test Health Check
# ──────────────────────────────────────────────────────────────────
print("\n1️⃣ Test Health Check : GET /api/face/health")
try:
    response = requests.get(f"{API_BASE}/face/health", timeout=5)
    print(f"   Status : {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ {data.get('message')}")
        print(f"   face_service_loaded : {data.get('face_service_loaded')}")
        print(f"   model_trained : {data.get('model_trained')}")
    else:
        print(f"   ❌ Erreur : {response.text}")
except Exception as e:
    print(f"   ❌ Impossible de contacter l'API : {e}")
    print("   💡 Assure-toi que Django tourne : python manage.py runserver 8000")

# ──────────────────────────────────────────────────────────────────
# 2. Test Stats
# ──────────────────────────────────────────────────────────────────
print("\n2️⃣ Test Stats : GET /api/face/stats")
try:
    response = requests.get(f"{API_BASE}/face/stats", timeout=5)
    print(f"   Status : {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            stats = data.get('stats', {})
            print(f"   ✅ Étudiants   : {stats.get('etudiants')}")
            print(f"   ✅ Enseignants : {stats.get('enseignants')}")
            print(f"   ✅ Personnes   : {stats.get('personnes')}")
            print(f"   ✅ Total       : {stats.get('total')}")
            print(f"   ✅ Trained     : {stats.get('trained')}")
        else:
            print(f"   ❌ {data.get('error')}")
    else:
        print(f"   ❌ Erreur {response.status_code}")
except Exception as e:
    print(f"   ❌ Erreur : {e}")

# ──────────────────────────────────────────────────────────────────
# 3. Test Train (optionnel - commente si tu ne veux pas entraîner)
# ──────────────────────────────────────────────────────────────────
print("\n3️⃣ Test Train : POST /api/face/train")
print("   ⚠️  Cette requête va entraîner le modèle (peut prendre du temps)")
reponse_user = input("   Continuer ? (o/n) : ").strip().lower()

if reponse_user == 'o':
    try:
        response = requests.post(f"{API_BASE}/face/train", timeout=120)
        print(f"   Status : {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"   ✅ {data.get('message')}")
                stats = data.get('stats', {})
                print(f"   📊 Total : {stats.get('total')} personne(s)")
            else:
                print(f"   ❌ {data.get('error')}")
        else:
            print(f"   ❌ Erreur {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
else:
    print("   ⏭️  Entraînement ignoré")

# ──────────────────────────────────────────────────────────────────
# 4. Résumé
# ──────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("✅ TESTS TERMINÉS")
print("="*60)
print("\n💡 Si tu as des erreurs 404 :")
print("   1. Vérifie que Django tourne : python manage.py runserver 8000")
print("   2. Vérifie api/urls.py (routes bien définies)")
print("   3. Vérifie backend/urls.py (include api.urls)")
print("\n💡 Si tu as des erreurs 500 :")
print("   1. Regarde les logs Django dans le terminal")
print("   2. Vérifie que ai/face_service.py existe")
print("   3. Vérifie que le modèle est entraîné")