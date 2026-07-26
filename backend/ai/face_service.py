"""
face_service.py — API Flask CORRIGÉE pour la reconnaissance faciale
====================================================================
Corrections :
  - CORS complet (toutes origines, tous headers, preflight OPTIONS)
  - Chemins robustes (fonctionne depuis n'importe quel répertoire)
  - Gestion propre import face_recognition (avec message d'erreur clair)
  - Route /health sans authentification
  - Chargement au démarrage avec diagnostic complet

Lancement :
  cd backend/ai
  python face_service.py

  Ou depuis n'importe où :
  PYTHONPATH=/chemin/vers/backend/ai python /chemin/vers/backend/ai/face_service.py
"""

import os
import sys
import json
import base64
import logging
import time
from datetime import datetime

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("FaceService")

# ── Dépendances obligatoires ──────────────────────────────────────
try:
    import numpy as np
except ImportError:
    print("❌ numpy manquant → pip install numpy")
    sys.exit(1)

try:
    import cv2
except ImportError:
    print("❌ opencv manquant → pip install opencv-python")
    sys.exit(1)

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    print("❌ flask ou flask-cors manquant → pip install flask flask-cors")
    sys.exit(1)

# ── face_recognition (optionnel mais recommandé) ──────────────────
try:
    import face_recognition as fr
    USE_DLIB = True
    log.info("✅ face_recognition (dlib) chargé")
except ImportError:
    USE_DLIB = False
    log.warning("⚠️  face_recognition non installé → mode dégradé")
    log.warning("   Installez-le : pip install face_recognition")

# ════════════════════════════════════════════════════════════════
# FLASK + CORS COMPLET
# ════════════════════════════════════════════════════════════════
app = Flask(__name__)

# CORS complet — autorise React (localhost:3000) et toute autre origine
CORS(
    app,
    origins="*",
    allow_headers=["Content-Type", "Authorization", "Accept"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    supports_credentials=False,
)

# Répondre aux requêtes OPTIONS (preflight) sur toutes les routes
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        from flask import make_response
        resp = make_response()
        resp.headers["Access-Control-Allow-Origin"]  = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        resp.headers["Access-Control-Max-Age"]       = "3600"
        return resp, 200

app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB
app.config["JSON_SORT_KEYS"]     = False

# ════════════════════════════════════════════════════════════════
# CHEMINS — robustes depuis n'importe quel répertoire de travail
# ════════════════════════════════════════════════════════════════
# Ce script peut être dans backend/ai/ ou backend/
# On cherche le dossier "ai" de façon flexible
_this_file = os.path.abspath(__file__)
_this_dir  = os.path.dirname(_this_file)

# Chercher le dossier media
def _find_media():
    candidates = [
        os.path.join(_this_dir, "media"),
        os.path.join(_this_dir, "..", "media"),
        os.path.join(os.getcwd(), "media"),
        os.path.join(os.getcwd(), "ai", "media"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return os.path.normpath(c)
    # Créer le dossier si absent
    path = os.path.join(_this_dir, "media")
    os.makedirs(os.path.join(path, "etudiants"),   exist_ok=True)
    os.makedirs(os.path.join(path, "enseignants"), exist_ok=True)
    return path

MEDIA_DIR      = _find_media()
ETU_IMAGES_DIR = os.path.join(MEDIA_DIR, "etudiants")
ENS_IMAGES_DIR = os.path.join(MEDIA_DIR, "enseignants")

# Chercher les fichiers JSON
def _find_json(name):
    candidates = [
        os.path.join(_this_dir, name),
        os.path.join(_this_dir, "..", name),
        os.path.join(os.getcwd(), name),
        os.path.join(os.getcwd(), "ai", name),
        os.path.join(MEDIA_DIR, "..", name),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.normpath(c)
    return os.path.join(_this_dir, name)   # chemin par défaut (peut ne pas exister)

ETU_JSON = _find_json("etudiants.json")
ENS_JSON = _find_json("enseignants.json")

# ════════════════════════════════════════════════════════════════
# CACHE GLOBAL
# ════════════════════════════════════════════════════════════════
KNOWN_ENCODINGS = []
KNOWN_IDS       = []
KNOWN_TYPES     = []
ALL_DATA        = {}   # {(type, id): dict}
LOAD_ERRORS     = []   # erreurs collectées au chargement


def _read_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"JSON invalide {path} : {e}")
        return []


def load_all_faces():
    """Charge et encode tous les visages depuis les JSON."""
    global KNOWN_ENCODINGS, KNOWN_IDS, KNOWN_TYPES, ALL_DATA, LOAD_ERRORS
    KNOWN_ENCODINGS = []
    KNOWN_IDS       = []
    KNOWN_TYPES     = []
    ALL_DATA        = {}
    LOAD_ERRORS     = []

    log.info("=" * 55)
    log.info("🔄 Chargement des visages...")
    log.info(f"   MEDIA_DIR : {MEDIA_DIR}")
    log.info(f"   ETU_JSON  : {ETU_JSON} {'✅' if os.path.exists(ETU_JSON) else '❌ ABSENT'}")
    log.info(f"   ENS_JSON  : {ENS_JSON} {'✅' if os.path.exists(ENS_JSON) else '❌ ABSENT'}")

    sources = [
        ("etudiant",   ETU_JSON, ETU_IMAGES_DIR),
        ("enseignant", ENS_JSON, ENS_IMAGES_DIR),
    ]

    for ptype, json_path, images_dir in sources:
        persons = _read_json(json_path)
        log.info(f"\n  {ptype.upper()} ({len(persons)} entrées)")

        if not persons:
            LOAD_ERRORS.append(f"{ptype}: JSON vide ou absent ({json_path})")
            continue

        ok, skip = 0, 0
        for person in persons:
            pid      = person.get("id")
            img_file = person.get("image_file", "")
            name     = person.get("name", f"ID={pid}")

            if not img_file:
                log.warning(f"    ⚠️  'image_file' manquant pour {name}")
                skip += 1
                continue

            img_path = os.path.join(images_dir, img_file)
            if not os.path.exists(img_path):
                log.warning(f"    ❌ Image introuvable : {img_path}")
                LOAD_ERRORS.append(f"Image manquante : {img_path}")
                skip += 1
                continue

            try:
                if USE_DLIB:
                    img_rgb   = fr.load_image_file(img_path)
                    locations = fr.face_locations(img_rgb, model="hog")
                    if not locations:
                        locations = fr.face_locations(img_rgb, model="cnn")
                    if not locations:
                        log.warning(f"    ⚠️  Aucun visage dans : {img_file}")
                        LOAD_ERRORS.append(f"Aucun visage détectable dans {img_file}")
                        skip += 1
                        continue
                    encodings = fr.face_encodings(img_rgb, locations)
                    if not encodings:
                        skip += 1
                        continue
                    encoding = encodings[0]
                else:
                    log.warning("    ⚠️  dlib absent — encodage impossible")
                    skip += 1
                    continue

                KNOWN_ENCODINGS.append(encoding)
                KNOWN_IDS.append(pid)
                KNOWN_TYPES.append(ptype)
                ALL_DATA[(ptype, pid)] = {**person, "type": ptype}
                ok += 1
                log.info(f"    ✅ {name}")

            except Exception as e:
                log.error(f"    ❌ Erreur {img_file} : {e}")
                LOAD_ERRORS.append(f"Erreur encodage {img_file} : {e}")
                skip += 1

        log.info(f"  → {ok} encodés, {skip} ignorés")

    log.info(f"\n✅ Total : {len(KNOWN_ENCODINGS)} visage(s) chargé(s)")
    log.info("=" * 55)
    return len(KNOWN_ENCODINGS) > 0


# ════════════════════════════════════════════════════════════════
# RECONNAISSANCE
# ════════════════════════════════════════════════════════════════

def decode_image(b64):
    """Décode base64 → numpy BGR."""
    if "," in b64:
        b64 = b64.split(",")[1]
    arr = np.frombuffer(base64.b64decode(b64), dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


def recognize_frame(img_bgr, tolerance=0.50):
    """
    Détecte et identifie les visages dans une image BGR.
    Retourne (list_résultats, message_debug).
    """
    if not USE_DLIB:
        return [], "face_recognition (dlib) non installé"
    if not KNOWN_ENCODINGS:
        return [], "Aucun visage chargé en mémoire"

    # BGR → RGB
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    # Améliorer le contraste
    lab   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l     = clahe.apply(l)
    img_rgb = cv2.cvtColor(
        cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR),
        cv2.COLOR_BGR2RGB
    )

    # Détection visages
    locations = fr.face_locations(img_rgb, model="hog")
    if not locations:
        locations = fr.face_locations(img_rgb, model="cnn")
    if not locations:
        return [], "Aucun visage détecté dans l'image"

    unknowns = fr.face_encodings(img_rgb, locations)
    if not unknowns:
        return [], "Visage(s) détecté(s) mais encodage échoué"

    known_arr = np.array(KNOWN_ENCODINGS)
    results   = []

    for enc, loc in zip(unknowns, locations):
        top, right, bottom, left = loc
        distances = fr.face_distance(known_arr, enc)
        best_idx  = int(np.argmin(distances))
        min_dist  = float(distances[best_idx])
        confidence = round(max(0.0, (1 - min_dist / 0.6) * 100), 1)

        log.info(f"  dist={min_dist:.4f} conf={confidence}% seuil={tolerance}")

        bbox = {"top": top, "right": right, "bottom": bottom, "left": left}

        if min_dist <= tolerance:
            pid    = KNOWN_IDS[best_idx]
            ptype  = KNOWN_TYPES[best_idx]
            pdata  = ALL_DATA.get((ptype, pid), {})
            results.append({
                "identified":  True,
                "id":          pid,
                "type":        ptype,
                "name":        pdata.get("name", ""),
                "image_file":  pdata.get("image_file", ""),
                "email":       pdata.get("email", ""),
                "telephone":   pdata.get("telephone", ""),
                "classe":      pdata.get("classe", ""),
                "niveau":      pdata.get("niveau", ""),
                "matiere":     pdata.get("matiere", ""),
                "confidence":  confidence,
                "distance":    round(min_dist, 4),
                "bbox":        bbox,
            })
        else:
            results.append({
                "identified": False,
                "confidence": confidence,
                "distance":   round(min_dist, 4),
                "bbox":       bbox,
                "error":      f"Distance {min_dist:.3f} > seuil {tolerance}",
            })

    msg = f"{len(locations)} visage(s) détecté(s), {sum(r['identified'] for r in results)} reconnu(s)"
    return results, msg


# ════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.route("/health", methods=["GET"])
def health():
    """Statut complet du service — utilisé par React pour le badge vert/rouge."""
    return jsonify({
        "status":        "ok",
        "dlib":          USE_DLIB,
        "faces_loaded":  len(KNOWN_ENCODINGS),
        "breakdown": {
            "etudiants":   sum(1 for t in KNOWN_TYPES if t == "etudiant"),
            "enseignants": sum(1 for t in KNOWN_TYPES if t == "enseignant"),
        },
        "paths": {
            "media_dir": MEDIA_DIR,
            "etu_json":  ETU_JSON,
            "ens_json":  ENS_JSON,
            "etu_json_exists": os.path.exists(ETU_JSON),
            "ens_json_exists": os.path.exists(ENS_JSON),
        },
        "load_errors":   LOAD_ERRORS,
        "timestamp":     datetime.now().isoformat(),
    })


@app.route("/persons", methods=["GET"])
def persons():
    etudiants   = [v for (t, _), v in ALL_DATA.items() if t == "etudiant"]
    enseignants = [v for (t, _), v in ALL_DATA.items() if t == "enseignant"]
    return jsonify({
        "etudiants":   etudiants,
        "enseignants": enseignants,
        "total":       len(ALL_DATA),
    })


@app.route("/reload", methods=["POST"])
def reload():
    ok = load_all_faces()
    return jsonify({
        "success":      ok,
        "faces_loaded": len(KNOWN_ENCODINGS),
        "breakdown": {
            "etudiants":   sum(1 for t in KNOWN_TYPES if t == "etudiant"),
            "enseignants": sum(1 for t in KNOWN_TYPES if t == "enseignant"),
        },
        "errors": LOAD_ERRORS,
        "message": f"{len(KNOWN_ENCODINGS)} visage(s) chargé(s)" if ok else "Aucun visage chargé",
    })


def _do_identify(filter_type=None):
    """Logique commune à /identify, /identify/etudiants, /identify/enseignants."""
    if not request.is_json:
        return jsonify({"error": "Content-Type doit être application/json"}), 400
    data = request.get_json(silent=True) or {}
    b64  = data.get("image", "")
    tol  = float(data.get("tolerance", 0.50))

    if not b64:
        return jsonify({"error": "Champ 'image' manquant ou vide"}), 400

    if not USE_DLIB:
        return jsonify({
            "error":   "face_recognition (dlib) non installé",
            "hint":    "pip install face_recognition",
            "matches": [],
        }), 503

    if not KNOWN_ENCODINGS:
        return jsonify({
            "error":   "Aucun visage en mémoire",
            "hint":    "Vérifiez vos JSON et images, puis appelez POST /reload",
            "errors":  LOAD_ERRORS,
            "matches": [],
        }), 503

    try:
        img = decode_image(b64)
        if img is None:
            return jsonify({"error": "Image base64 invalide"}), 400

        t0             = time.time()
        results, msg   = recognize_frame(img, tolerance=tol)
        elapsed        = round((time.time() - t0) * 1000, 1)

        # Filtrer par type si demandé
        if filter_type:
            results = [r for r in results if not r.get("identified") or r.get("type") == filter_type]

        identified_count = sum(1 for r in results if r.get("identified"))
        db_count = (
            sum(1 for t in KNOWN_TYPES if t == filter_type)
            if filter_type else len(KNOWN_ENCODINGS)
        )

        return jsonify({
            "matches":          results,
            "identified_count": identified_count,
            "debug": {
                "webcam_faces":  len(results),
                "db_faces":      db_count,
                "message":       msg if not identified_count else "Succès",
                "inference_ms":  elapsed,
                "tolerance":     tol,
            },
        })

    except Exception as e:
        log.error(f"CRASH /identify : {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/identify", methods=["POST"])
def identify():
    """Identifie depuis tous les visages chargés (étudiants + enseignants)."""
    return _do_identify(filter_type=None)


@app.route("/identify/etudiants", methods=["POST"])
def identify_etudiants():
    """Identifie en filtrant uniquement les étudiants."""
    return _do_identify(filter_type="etudiant")


@app.route("/identify/enseignants", methods=["POST"])
def identify_enseignants():
    """Identifie en filtrant uniquement les enseignants."""
    return _do_identify(filter_type="enseignant")


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Endpoint introuvable", "disponibles": [
        "GET  /health",
        "GET  /persons",
        "POST /reload",
        "POST /identify",
        "POST /identify/etudiants",
        "POST /identify/enseignants",
    ]}), 404

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "Image trop grande (max 32 MB)"}), 413

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Erreur interne", "detail": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# WRAPPER — Classe exportable pour Django
# ════════════════════════════════════════════════════════════════

# Importer la classe FaceRecognitionSimple
try:
    from face_recognition_simple import FaceRecognitionSimple
    log.info("✅ FaceRecognitionSimple importé")
    HAVE_SIMPLE_CLASS = True
except ImportError as e:
    log.warning(f"⚠️  FaceRecognitionSimple non trouvé : {e}")
    HAVE_SIMPLE_CLASS = False


class FaceRecognitionService:
    """Wrapper autour du service de reconnaissance faciale pour Django."""

    def __init__(self):
        """Initialise le service."""
        self._model = None
        # Chemin correct du modèle dans le dossier ai/
        ai_dir = os.path.dirname(os.path.abspath(__file__))
        self._model_path = os.path.join(ai_dir, "trained_model.yml")
        self._use_dlib = USE_DLIB
        
        # Utiliser la classe FaceRecognitionSimple si disponible
        if HAVE_SIMPLE_CLASS:
            try:
                self._model = FaceRecognitionSimple(base_path=MEDIA_DIR)
                log.info("✅ Instance FaceRecognitionSimple créée")
                
                # Essayer de charger un modèle sauvegardé
                if os.path.exists(self._model_path):
                    log.info(f"📂 Modèle trouvé : {self._model_path}")
                    loaded = self._model.load_model(self._model_path)
                    if loaded:
                        log.info(f"✅ Modèle chargé automatiquement")
                    else:
                        log.warning(f"⚠️  Impossible de charger le modèle")
                else:
                    log.info(f"ℹ️  Aucun modèle sauvegardé — lancez POST /api/face/train/")
            except Exception as e:
                log.error(f"❌ Erreur création FaceRecognitionSimple : {e}", exc_info=True)
                self._model = None
        else:
            log.error("❌ FaceRecognitionSimple non disponible")

    def get_stats(self):
        """Retourne les stats actuelles du modèle."""
        if self._model and hasattr(self._model, 'database'):
            total = sum(len(v) for v in self._model.database.values())
            return {
                "total": total,
                "etudiants": len(self._model.database.get("etudiants", {})),
                "enseignants": len(self._model.database.get("enseignants", {})),
                "personnes": len(self._model.database.get("personnes", {})),
                "trained": self._model.trained if self._model else False,
            }
        
        # Fallback aux stats du module
        return {
            "total": len(KNOWN_ENCODINGS),
            "etudiants": sum(1 for t in KNOWN_TYPES if t == "etudiant"),
            "enseignants": sum(1 for t in KNOWN_TYPES if t == "enseignant"),
            "personnes": sum(1 for t in KNOWN_TYPES if t == "personne"),
            "trained": len(KNOWN_ENCODINGS) > 0,
        }

    def is_trained(self):
        """Indique si le modèle est entraîné."""
        if self._model and hasattr(self._model, 'trained'):
            return self._model.trained
        return len(KNOWN_ENCODINGS) > 0

    def get_all_persons(self):
        """Retourne tous les visages chargés."""
        if self._model and hasattr(self._model, 'database'):
            persons = self._model.database
            etudiants = list(persons.get("etudiants", {}).values())
            enseignants = list(persons.get("enseignants", {}).values())
            personnes = list(persons.get("personnes", {}).values())
            return {
                "etudiants": etudiants,
                "enseignants": enseignants,
                "personnes": personnes,
                "total": len(etudiants) + len(enseignants) + len(personnes),
            }
        
        # Fallback
        etudiants = [v for (t, _), v in ALL_DATA.items() if t == "etudiant"]
        enseignants = [v for (t, _), v in ALL_DATA.items() if t == "enseignant"]
        personnes = [v for (t, _), v in ALL_DATA.items() if t == "personne"]
        return {
            "etudiants": etudiants,
            "enseignants": enseignants,
            "personnes": personnes,
            "total": len(ALL_DATA),
        }

    def load_model(self):
        """Charge le modèle sauvegardé depuis le disque."""
        if self._model and hasattr(self._model, 'load_model'):
            try:
                result = self._model.load_model(self._model_path)
                log.info(f"✅ Modèle chargé : {result}")
                return result
            except Exception as e:
                log.error(f"❌ Erreur chargement : {e}")
                return False
        
        # Fallback
        return load_all_faces()

    def train_model(self):
        """Entraîne le modèle depuis les images du dossier media/."""
        if not self._model or not hasattr(self._model, 'train_from_folders'):
            log.error("❌ FaceRecognitionSimple non disponible")
            return False
        
        try:
            log.info("🎓 Démarrage de l'entraînement...")
            success = self._model.train_from_folders()
            
            if success:
                # Sauvegarder le modèle
                log.info("💾 Sauvegarde du modèle...")
                save_ok = self._model.save_model(self._model_path)
                log.info(f"   Sauvegarde : {'✅ OK' if save_ok else '❌ KO'}")
                log.info(f"   Fichiers : {self._model_path} + _db.json")
                return True
            else:
                log.error("❌ train_from_folders() a échoué")
                return False
        
        except Exception as e:
            log.error(f"❌ Erreur entraînement : {e}", exc_info=True)
            return False

    def recognize(self, image_path, threshold=50):
        """Reconnaît un visage dans une image."""
        if not self._model or not hasattr(self._model, 'recognize'):
            log.error("❌ FaceRecognitionSimple non disponible pour reconnaissance")
            return {"error": "Service non disponible", "matches": []}
        
        if not self._model.trained:
            return {"error": "Modèle non entraîné", "matches": []}
        
        try:
            result = self._model.recognize(image_path, threshold=threshold)
            return result
        except Exception as e:
            log.error(f"❌ Erreur reconnaissance : {e}", exc_info=True)
            return {"error": str(e), "matches": []}


# Créer une instance singleton exportable
log.info("🚀 Initialisation du service FaceRecognitionService...")
face_service = FaceRecognitionService()
log.info("✅ FaceRecognitionService prêt")


# ════════════════════════════════════════════════════════════════
# DÉMARRAGE
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Face Recognition Service — Flask")
    print("=" * 60)
    print(f"\n  Script    : {_this_file}")
    print(f"  MEDIA_DIR : {MEDIA_DIR}")
    print(f"  ETU_JSON  : {ETU_JSON} {'✅' if os.path.exists(ETU_JSON) else '❌ ABSENT'}")
    print(f"  ENS_JSON  : {ENS_JSON} {'✅' if os.path.exists(ENS_JSON) else '❌ ABSENT'}")
    print(f"  dlib      : {'✅ Disponible' if USE_DLIB else '❌ Non installé'}")

    if not USE_DLIB:
        print("\n  ⚠️  face_recognition manquant !")
        print("  Installez-le :")
        print("    pip install cmake dlib face_recognition")
        print("\n  Le service démarrera en mode dégradé.")

    print()
    load_all_faces()

    if LOAD_ERRORS:
        print(f"\n  ⚠️  {len(LOAD_ERRORS)} erreur(s) au chargement :")
        for err in LOAD_ERRORS[:5]:
            print(f"     • {err}")

    print(f"\n  ✅ {len(KNOWN_ENCODINGS)} visage(s) chargé(s)")
    print(f"  API  : http://localhost:5001")
    print(f"  Test : http://localhost:5001/health")
    print("=" * 60 + "\n")

    app.run(
        host     = "0.0.0.0",
        port     = 5001,
        debug    = False,
        threaded = True,
    )