import base64
from django.core.files.base import ContentFile
import uuid
import os
from django.conf import settings

def save_base64_image(base64_image, nom, prenom):
    # Supprimer le préfixe si présent
    if ";base64," in base64_image:
        base64_image = base64_image.split(";base64,")[1]

    # Corriger le padding si nécessaire
    missing_padding = len(base64_image) % 4
    if missing_padding:
        base64_image += "=" * (4 - missing_padding)

    image_bytes = base64.b64decode(base64_image)

    # Générer un nom unique
    unique_id = uuid.uuid4().hex
    filename = f"{nom}_{prenom}_{unique_id}.png"

    # Créer ContentFile avec le nom
    return ContentFile(image_bytes, name=filename)

def delete_base64_image(photo):
    """
    Supprime une image stockée dans MEDIA_ROOT.
    photo peut être :
    - ImageField (etudiant.photo)
    - string ('etudiants/xxx.png')
    """

    if not photo:
        return

    # Cas ImageField
    if hasattr(photo, "path"):
        file_path = photo.path

    # Cas string
    else:
        file_path = os.path.join(settings.MEDIA_ROOT, str(photo))

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print("🗑️ Image supprimée :", file_path)
    except Exception as e:
        print("❌ Erreur suppression image :", e)

import os
import sys

# Ajouter le chemin vers le module face_recognition_simple
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, 'ai'))

from face_recognition_simple import FaceRecognitionSimple

ETUDIANTS_DIR = os.path.join(BASE_DIR, "ai", "media", "etudiants")
ENSEIGNANTS_DIR = os.path.join(BASE_DIR, "ai", "media", "enseignants")
PERSONNES_DIR = os.path.join(BASE_DIR, "ai", "media", "personnes")

# Instance du modèle manuel
_model_instance = None

def get_face_model():
    """
    Récupère ou crée l'instance du modèle de reconnaissance faciale
    """
    global _model_instance
    
    if _model_instance is None:
        _model_instance = FaceRecognitionSimple(base_path=os.path.join(BASE_DIR, 'ai', 'media'))
        
        # Charger le modèle s'il existe, sinon l'entraîner
        model_path = os.path.join(BASE_DIR, 'ai', 'trained_model.yml')
        
        if os.path.exists(model_path):
            _model_instance.load_model(model_path)
            print("✅ Modèle de reconnaissance faciale chargé")
        else:
            print("⚠️ Aucun modèle trouvé. Entraînement en cours...")
            success = _model_instance.train_from_folders()
            if success:
                _model_instance.save_model(model_path)
                print("✅ Modèle entraîné et sauvegardé")
            else:
                print("❌ Échec de l'entraînement du modèle")
    
    return _model_instance


def distance_to_similarity(confidence):
    """
    Convertit la confidence du modèle en similarité (0-100%)
    Le modèle LBPH donne une distance : plus elle est basse, meilleure est la correspondance
    
    Args:
        confidence: Score de confidence du modèle (0-100+)
        
    Returns:
        float: Similarité en pourcentage (0-100)
    """
    # Plus la confidence est basse, meilleure est la correspondance
    # On inverse et normalise pour avoir un pourcentage de similarité
    similarity = max(0, 100 - confidence)
    return round(similarity, 2)


def find_face(image_path, threshold=70):
    """
    Trouve et identifie un visage dans une image
    
    Args:
        image_path: Chemin vers l'image à analyser
        threshold: Seuil de confidence (défaut: 70)
        
    Returns:
        dict ou None: {
            "role": "etudiant" ou "enseignant",
            "identity": "Prenom_Nom",
            "prenom": "Prenom",
            "nom": "Nom",
            "similarity": 85.5,
            "confidence": 35.2,
            "id": 0
        }
    """
    # Vérifier que l'image existe
    if not os.path.exists(image_path):
        print(f"❌ Image non trouvée: {image_path}")
        return None
    
    # Récupérer le modèle
    model = get_face_model()
    
    if not model.trained:
        print("❌ Modèle non entraîné")
        return None
    
    # Reconnaître le visage
    result = model.recognize(image_path, threshold=threshold)
    
    if not result['success']:
        print(f"❌ Erreur: {result.get('error', 'Erreur inconnue')}")
        return None
    
    if not result['identified']:
        print("❌ Aucune personne reconnue")
        return None
    
    # Formater le résultat
    best_result = {
        "role": result['type'],  # 'etudiant' ou 'enseignant'
        "identity": f"{result['prenom']}_{result['nom']}",
        "prenom": result['prenom'],
        "nom": result['nom'],
        "similarity": result['similarity'],
        "confidence": result['confidence'],
        "id": result['id']
    }
    
    print(f"✅ Personne identifiée: {result['prenom']} {result['nom']} ({result['type']})")
    print(f"   Similarité: {result['similarity']}%")
    
    return best_result


def train_model():
    """
    Entraîne ou réentraîne le modèle avec les données actuelles
    
    Returns:
        bool: True si succès, False sinon
    """
    model = get_face_model()
    
    print("🎓 Entraînement du modèle en cours...")
    success = model.train_from_folders()
    
    if success:
        model_path = os.path.join(BASE_DIR, 'ai', 'trained_model.yml')
        model.save_model(model_path)
        print("✅ Modèle entraîné et sauvegardé avec succès")
        return True
    else:
        print("❌ Échec de l'entraînement")
        return False


def get_database_stats():
    """
    Retourne les statistiques de la base de données
    
    Returns:
        dict: {
            'trained': bool,
            'etudiants': int,
            'enseignants': int,
            'total': int
        }
    """
    model = get_face_model()
    
    if not model.trained:
        return {
            'trained': False,
            'etudiants': 0,
            'enseignants': 0,
            'total': 0
        }
    
    nb_etudiants = len(model.database['etudiants'])
    nb_enseignants = len(model.database['enseignants'])
    
    return {
        'trained': True,
        'etudiants': nb_etudiants,
        'enseignants': nb_enseignants,
        'total': nb_etudiants + nb_enseignants
    }


def get_all_persons():
    """
    Retourne la liste de toutes les personnes dans la base de données
    
    Returns:
        dict: {
            'etudiants': [...],
            'enseignants': [...]
        }
    """
    model = get_face_model()
    
    if not model.trained:
        return {
            'etudiants': [],
            'enseignants': []
        }
    
    etudiants = [
        {
            'id': k,
            'prenom': v['prenom'],
            'nom': v['nom'],
            'nom_complet': f"{v['prenom']} {v['nom']}"  # ✅ Ajouté
        }
        for k, v in model.database['etudiants'].items()
    ]
    
    enseignants = [
        {
            'id': k,
            'prenom': v['prenom'],
            'nom': v['nom'],
            'nom_complet': f"{v['prenom']} {v['nom']}"  # ✅ Ajouté
        }
        for k, v in model.database['enseignants'].items()
    ]
    
    return {
        'etudiants': etudiants,
        'enseignants': enseignants
    }


# Exemple d'utilisation
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TEST DU MODULE DE RECONNAISSANCE FACIALE")
    print("=" * 60)
    
    # Test 1 : Entraîner le modèle
    print("\n1️⃣ Entraînement du modèle...")
    train_model()
    
    # Test 2 : Statistiques
    print("\n2️⃣ Statistiques de la base de données...")
    stats = get_database_stats()
    print(f"   Modèle entraîné: {stats['trained']}")
    print(f"   Étudiants: {stats['etudiants']}")
    print(f"   Enseignants: {stats['enseignants']}")
    print(f"   Total: {stats['total']}")
    
    # Test 3 : Liste des personnes
    print("\n3️⃣ Liste des personnes enregistrées...")
    persons = get_all_persons()
    
    print(f"\n   📚 Étudiants ({len(persons['etudiants'])}):")
    for p in persons['etudiants']:
        print(f"      - {p['nom_complet']} (ID: {p['id']})")
    
    print(f"\n   👨‍🏫 Enseignants ({len(persons['enseignants'])}):")
    for p in persons['enseignants']:
        print(f"      - {p['nom_complet']} (ID: {p['id']})")
    
    # Test 4 : Reconnaissance (si une image de test existe)
    if os.path.exists(ETUDIANTS_DIR) and os.listdir(ETUDIANTS_DIR):
        test_image = os.path.join(ETUDIANTS_DIR, os.listdir(ETUDIANTS_DIR)[0])
        print(f"\n4️⃣ Test de reconnaissance sur: {os.path.basename(test_image)}")
        result = find_face(test_image)
        
        if result:
            print(f"\n   ✅ Résultat:")
            print(f"      Nom: {result['prenom']} {result['nom']}")
            print(f"      Type: {result['role']}")
            print(f"      Similarité: {result['similarity']}%")
            print(f"      Confidence: {result['confidence']}")
    else:
        print("\n4️⃣ Aucune image de test disponible")
    
    print("\n" + "=" * 60)
    print("✅ Tests terminés!")
    print("=" * 60)