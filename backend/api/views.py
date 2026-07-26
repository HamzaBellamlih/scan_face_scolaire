from datetime import datetime
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Note, Absence, AssuranceEnseignant, AssuranceEtudiant, Etudiant, Enseignant, PaiementEnseignant, Personne
import os
from .utils import save_base64_image, delete_base64_image
from django.core.files.storage import default_storage
from django.conf import settings
import sys
import uuid
import time
import threading
import tempfile
import traceback
import cv2
import numpy as np
from django.views.decorators.http import require_http_methods

AI_DIR = os.path.join(settings.BASE_DIR, "ai")

JSON_PATH_ETUDIANT   = os.path.join(AI_DIR, "media", "etudiants.json")
JSON_PATH_ENSEIGNANT = os.path.join(AI_DIR, "media", "enseignants.json")
JSON_PATH_PERSONNE   = os.path.join(AI_DIR, "media", "personnes.json")

def build_media_url(filename: str) -> str:
    """Retourne un chemin web commençant par /media/... pour une filename relative."""
    fname = filename.lstrip("/")
    media = settings.MEDIA_URL.rstrip("/")
    url = f"{media}/{fname}"
    if not url.startswith("/"):
        url = f"/{url}"
    return url

def relative_media_path(field_or_path):
    """Retourne 'etudiants/xxx.png' (chemin relatif sous MEDIA_ROOT) ou None."""
    if not field_or_path:
        return None
    # ImageField/FileField -> use .name
    if hasattr(field_or_path, "name") and field_or_path.name:
        return str(field_or_path.name).lstrip("/")
    # string -> remove MEDIA_URL or leading slash if present
    if isinstance(field_or_path, str):
        s = field_or_path
        media_prefix = str(settings.MEDIA_URL).rstrip("/")
        if s.startswith(media_prefix):
            s = s[len(media_prefix):]
        if s.startswith("/"):
            s = s[1:]
        return s or None
    return None

def filesystem_path_for(field_or_path):
    """Retourne le chemin fichier absolu si possible, None sinon."""
    rel = relative_media_path(field_or_path)
    if rel:
        return os.path.join(settings.MEDIA_ROOT, rel)
    return None

def get_next_free_id():
    """Récupère un ID disponible parmi tous les modèles (Etudiant, Enseignant, Personne)"""
    id_candidate = 1
    while (Etudiant.objects.filter(id=id_candidate).exists() or 
           Enseignant.objects.filter(id=id_candidate).exists() or 
           Personne.objects.filter(id=id_candidate).exists()):
        id_candidate += 1
    return id_candidate

@csrf_exempt
def ajouter_etudiant(request):
    if request.method != "POST":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    # ── 1. Lecture du JSON envoyé ──────────────────────────────────────────
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"message": "JSON invalide"}, status=400)

    # ── 2. Validation des champs obligatoires ──────────────────────────────
    champs = [
        "nom", "prenom", "email", "date_naissance",
        "lieu_naissance", "niveau_etude", "classe",
        "telephone", "photo"
    ]
    for champ in champs:
        if champ not in data or not data[champ]:
            return JsonResponse(
                {"message": f"Le champ '{champ}' est manquant."},
                status=400
            )

    # ── 3. Vérification email déjà existant ────────────────────────────────
    if Etudiant.objects.filter(email=data["email"]).exists():
        return JsonResponse({"message": "Email déjà enregistré."}, status=400)

    # ── 4. Sauvegarde image Base64 ─────────────────────────────────────────
    try:
        content_file = save_base64_image(
            data["photo"],
            data["nom"],
            data["prenom"]
        )

        folder = "etudiants"
        folder_path = os.path.join(settings.MEDIA_ROOT, folder)
        os.makedirs(folder_path, exist_ok=True)

        if isinstance(content_file, str):
            filename = (
                content_file
                if content_file.startswith(folder)
                else os.path.join(folder, os.path.basename(content_file))
            )
            field_path = filename
        else:
            name = getattr(content_file, "name", None) or f"{data['nom']}_{data['prenom']}.png"
            content_file.name = name
            field_path = default_storage.save(
                os.path.join(folder, content_file.name),
                content_file
            )

        photo_url = build_media_url(field_path)

    except Exception as e:
        return JsonResponse(
            {"message": f"Erreur lors de l'enregistrement de la photo : {e}"},
            status=500
        )

    # ── 5. Enregistrement en base de données ───────────────────────────────
    etu = Etudiant.objects.create(
        nom=data["nom"],
        prenom=data["prenom"],
        email=data["email"],
        date_naissance=data["date_naissance"],
        lieu_naissance=data["lieu_naissance"],
        niveau_etude=data["niveau_etude"],
        classe=data["classe"],
        telephone=data["telephone"],
        photo=field_path
    )

    # ── 6. Gestion du fichier JSON ─────────────────────────────────────────

    # S'assurer que le dossier parent existe
    json_dir = os.path.dirname(JSON_PATH_ETUDIANT)
    if json_dir:
        os.makedirs(json_dir, exist_ok=True)

    if os.path.exists(JSON_PATH_ETUDIANT):
        try:
            with open(JSON_PATH_ETUDIANT, "r", encoding="utf-8") as f:
                etudiants = json.load(f)
            if not isinstance(etudiants, list):   # sécurité si le JSON est corrompu
                etudiants = []
        except (json.JSONDecodeError, IOError, OSError):
            etudiants = []
    else:
        etudiants = []

    # ── 7. Objet étudiant à ajouter dans le JSON ───────────────────────────
    etudiant_json = {
        "id": etu.id,
        "nom": etu.nom,
        "prenom": etu.prenom,
        "email": etu.email,
        "date_naissance": str(etu.date_naissance),
        "lieu_naissance": etu.lieu_naissance,
        "niveau_etude": etu.niveau_etude,
        "classe": etu.classe,
        "telephone": etu.telephone,
        "photo": photo_url
    }

    etudiants.append(etudiant_json)

    # Écriture atomique : on écrit dans un fichier temporaire puis on renomme
    # pour éviter un fichier JSON corrompu en cas de crash pendant l'écriture.
    tmp_path = JSON_PATH_ETUDIANT + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(etudiants, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, JSON_PATH_ETUDIANT)   # opération atomique
    except (IOError, OSError, TypeError) as e:
        # Nettoyer le fichier temporaire si besoin
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return JsonResponse({
            "message": f"Ajouté en DB mais erreur écriture JSON : {str(e)}",
            "id_db": etu.id
        }, status=207)

    return JsonResponse(
        {
            "message": "Étudiant ajouté avec succès (DB + JSON)",
            "id_db": etu.id,
            "id_json": etu.id   # ✅ Corrigé : next_id → etu.id
        },
        status=201
    )

@csrf_exempt
def modifier_etudiant(request, etudiant_id):
    if request.method != "PUT":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"message": "JSON invalide"}, status=400)

    # 1️⃣ Récupérer l’étudiant
    try:
        etudiant = Etudiant.objects.get(id=etudiant_id)
    except Etudiant.DoesNotExist:
        return JsonResponse({"message": "Étudiant introuvable"}, status=404)

    # 2️⃣ Mise à jour des champs (sans photo)
    champs = [
        "nom", "prenom", "email",
        "date_naissance", "lieu_naissance",
        "niveau_etude", "classe", "telephone"
    ]

    for champ in champs:
        if champ in data:
            setattr(etudiant, champ, data[champ])

    # 3️⃣ GESTION PROPRE DE LA PHOTO
    photo_base64 = data.get("photo")
    photo_relative_path = None

    if photo_base64 and photo_base64.startswith("data:image"):
        # 🔥 supprimer l'ancienne photo
        if etudiant.photo:
            delete_base64_image(etudiant.photo)

        # 💾 sauvegarder la nouvelle photo
        photo_path = save_base64_image(
            photo_base64,
            etudiant.nom,
            etudiant.prenom
        )

        # photo_path = "etudiants/xxx.png"
        etudiant.photo = photo_path
        photo_relative_path = f"{settings.MEDIA_URL}{photo_path}"  # /media/etudiants/xxx.png

    etudiant.save()

    # 4️⃣ Mise à jour du fichier JSON
    if not os.path.exists(JSON_PATH_ETUDIANT):
        return JsonResponse({
            "message": "Étudiant modifié en base, fichier JSON introuvable"
        }, status=200)

    with open(JSON_PATH_ETUDIANT, "r", encoding="utf-8") as f:
        try:
            etudiants = json.load(f)
        except json.JSONDecodeError:
            etudiants = []

    for e in etudiants:
        if e.get("id") == etudiant_id:
            e.update({
                "nom": etudiant.nom,
                "prenom": etudiant.prenom,
                "email": etudiant.email,
                "date_naissance": str(etudiant.date_naissance),
                "lieu_naissance": etudiant.lieu_naissance,
                "niveau_etude": etudiant.niveau_etude,
                "classe": etudiant.classe,
                "telephone": etudiant.telephone,
                "photo": (
                    photo_relative_path
                    if photo_relative_path
                    else e.get("photo")
                )
            })
            break

    # 5️⃣ Réécriture du fichier JSON
    with open(JSON_PATH_ETUDIANT, "w", encoding="utf-8") as f:
        json.dump(etudiants, f, indent=4, ensure_ascii=False)

    return JsonResponse({
        "message": "Étudiant modifié avec succès (DB + JSON)",
        "photo": photo_relative_path,
        "id": etudiant.id
    }, status=200)

@csrf_exempt
def supprimer_etudiant(request, etudiant_id):
    if request.method != "DELETE":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    # ── 1. Récupérer l'étudiant en base ────────────────────────────────────
    try:
        etudiant = Etudiant.objects.get(id=etudiant_id)
    except Etudiant.DoesNotExist:
        return JsonResponse({"message": "Étudiant introuvable"}, status=404)

    # ── 2. Supprimer la photo du système de fichiers ───────────────────────
    photo_fs_path = filesystem_path_for(etudiant.photo)
    if photo_fs_path:
        try:
            if os.path.exists(photo_fs_path):
                os.remove(photo_fs_path)
        except Exception:
            pass

    # ── 3. Supprimer de la base de données ────────────────────────────────
    etudiant.delete()

    # ── 4. Supprimer du fichier JSON ──────────────────────────────────────
    json_debug = {}

    if not os.path.exists(JSON_PATH_ETUDIANT):
        return JsonResponse({
            "message": "Supprimé de la DB mais fichier JSON introuvable",
            "json_path": JSON_PATH_ETUDIANT
        }, status=207)

    try:
        with open(JSON_PATH_ETUDIANT, "r", encoding="utf-8") as f:
            etudiants = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return JsonResponse({
            "message": f"Supprimé de la DB mais erreur lecture JSON : {str(e)}"
        }, status=207)

    # DEBUG : afficher les types et valeurs des ids dans le JSON
    json_debug["etudiant_id_recu"] = etudiant_id
    json_debug["type_etudiant_id"] = str(type(etudiant_id))
    json_debug["ids_dans_json"] = [
        {"id": e.get("id"), "type": str(type(e.get("id")))}
        for e in etudiants
    ]

    avant = len(etudiants)

    # Filtrage avec conversion str pour couvrir tous les cas
    etudiants = [
        e for e in etudiants
        if str(e.get("id", "")) != str(etudiant_id)
    ]

    apres = len(etudiants)
    json_debug["avant_suppression"] = avant
    json_debug["apres_suppression"] = apres
    json_debug["supprime"] = avant != apres

    try:
        with open(JSON_PATH_ETUDIANT, "w", encoding="utf-8") as f:
            json.dump(etudiants, f, indent=4, ensure_ascii=False)
    except IOError as e:
        return JsonResponse({
            "message": f"Supprimé de la DB mais erreur écriture JSON : {str(e)}",
            "debug": json_debug
        }, status=207)

    return JsonResponse({
        "message": "Étudiant supprimé avec succès (DB + JSON)",
        "id": etudiant_id,
        "debug": json_debug
    }, status=200)

@csrf_exempt
def lister_etudiants(request):
    if request.method != "GET":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    etudiants = Etudiant.objects.all()
    data = []
    DEFAULT_AVATAR = "https://via.placeholder.com/150?text=No+Photo"

    for e in etudiants:
        # Normaliser le chemin relatif puis produire URL publique (fallback front possible via photo_rel)
        rel_path = relative_media_path(e.photo)
        if rel_path:
            rel = build_media_url(rel_path)              # ex "/media/etudiants/xxx.png"
            photo_url = request.build_absolute_uri(rel)  # ex "http://127.0.0.1:8008/media/etudiants/xxx.png"
        else:
            rel = None
            photo_url = DEFAULT_AVATAR

        data.append({
            "id": e.id,
            "nom": e.nom,
            "prenom": e.prenom,
            "email": e.email,
            "date_naissance": str(e.date_naissance),
            "niveau_etude": e.niveau_etude,
            "classe": e.classe,
            "lieu_naissance": e.lieu_naissance,
            "telephone": e.telephone,
            "photo": photo_url,
            "photo_rel": rel,       # chemin public ("/media/...") utilisable côté front pour fallback
        })

    return JsonResponse(data, safe=False, status=200)

@csrf_exempt
def chercher_etudiant(request, etudiant_id):
    if request.method != "GET":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    try:
        etudiant = Etudiant.objects.get(id=etudiant_id)
    except Etudiant.DoesNotExist:
        return JsonResponse({"message": "Étudiant introuvable"}, status=404)

    DEFAULT_AVATAR = "https://via.placeholder.com/150?text=No+Photo"

    # Gestion de la photo (URL absolue si possible)
    rel_path = relative_media_path(etudiant.photo)
    if rel_path:
        rel = build_media_url(rel_path)
        photo_url = request.build_absolute_uri(rel)
    else:
        rel = None
        photo_url = DEFAULT_AVATAR

    data = {
        "id": etudiant.id,
        "nom": etudiant.nom,
        "prenom": etudiant.prenom,
        "date_naissance": str(etudiant.date_naissance),
        "niveau_etude": etudiant.niveau_etude,
        "classe": etudiant.classe,
        "lieu_naissance": etudiant.lieu_naissance,
        "telephone": etudiant.telephone,
        "email": etudiant.email,
        "photo": photo_url,
        "photo_rel": rel,
    }

    return JsonResponse(data, status=200)

@csrf_exempt
def ajouter_enseignant(request):
    if request.method != "POST":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    # ── 1. Lecture du JSON envoyé ──────────────────────────────────────────
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"message": "JSON invalide"}, status=400)

    # ── 2. Validation des champs obligatoires ──────────────────────────────
    champs = ["nom", "prenom", "date_naissance", "lieu_naissance",
              "matiere", "telephone", "email", "photo"]

    for champ in champs:
        if champ not in data or data[champ] in ["", None]:
            return JsonResponse(
                {"message": f"Le champ '{champ}' est manquant."},
                status=400
            )

    # ── 3. Vérification email déjà existant ────────────────────────────────
    if Enseignant.objects.filter(email=data["email"]).exists():
        return JsonResponse({"message": "Email déjà enregistré."}, status=400)

    # ── 4. Sauvegarde image Base64 ─────────────────────────────────────────
    try:
        content_file = save_base64_image(data["photo"], data["nom"], data["prenom"])

        folder = "enseignants"
        folder_path = os.path.join(settings.MEDIA_ROOT, folder)
        os.makedirs(folder_path, exist_ok=True)

        if isinstance(content_file, str):
            field_path = content_file
        else:
            field_path = default_storage.save(
                os.path.join(folder, content_file.name),
                content_file
            )

        photo_url = build_media_url(field_path)

    except Exception as e:
        return JsonResponse(
            {"message": f"Erreur lors de l'enregistrement de la photo : {e}"},
            status=500
        )

    # ── 5. Enregistrement en base de données ───────────────────────────────
    enseignant = Enseignant.objects.create(
        nom=data["nom"],
        prenom=data["prenom"],
        date_naissance=data["date_naissance"],
        lieu_naissance=data["lieu_naissance"],
        matiere=data["matiere"],
        telephone=data["telephone"],
        email=data["email"],
        photo=field_path
    )

    # ── 6. Gestion du fichier JSON ─────────────────────────────────────────
    if os.path.exists(JSON_PATH_ENSEIGNANT):
        try:
            with open(JSON_PATH_ENSEIGNANT, "r", encoding="utf-8") as f:
                enseignants = json.load(f)
        except (json.JSONDecodeError, IOError):
            enseignants = []
    else:
        enseignants = []

    # ── 7. Objet enseignant à ajouter dans le JSON ─────────────────────────
    enseignants.append({
        "id": enseignant.id,
        "nom": enseignant.nom,
        "prenom": enseignant.prenom,
        "date_naissance": str(enseignant.date_naissance),
        "lieu_naissance": enseignant.lieu_naissance,
        "matiere": enseignant.matiere,
        "telephone": enseignant.telephone,
        "email": enseignant.email,
        "photo": photo_url
    })

    try:
        with open(JSON_PATH_ENSEIGNANT, "w", encoding="utf-8") as f:
            json.dump(enseignants, f, indent=4, ensure_ascii=False)
    except IOError as e:
        return JsonResponse({
            "message": f"Ajouté en DB mais erreur écriture JSON : {str(e)}",
            "id": enseignant.id
        }, status=207)

    return JsonResponse({
        "message": "Enseignant ajouté avec succès (DB + JSON)",
        "id": enseignant.id
    }, status=201)

@csrf_exempt
def modifier_enseignant(request, enseignant_id):
    if request.method != "PUT":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"message": "JSON invalide"}, status=400)

    try:
        enseignant = Enseignant.objects.get(id=enseignant_id)
    except Enseignant.DoesNotExist:
        return JsonResponse({"message": "Enseignant introuvable"}, status=404)

    # mise à jour des champs simples
    for field in [
        "nom", "prenom", "email", "date_naissance",
        "lieu_naissance", "matiere", "telephone"
    ]:
        if field in data:
            setattr(enseignant, field, data[field])

    # gestion propre de la photo
    photo_relative_path = None
    if "photo" in data and data["photo"] and str(data["photo"]).startswith("data:image"):
        # suppression de l'ancienne photo si possible
        if enseignant.photo:
            try:
                delete_base64_image(enseignant.photo)
            except Exception:
                pass

        try:
            content_file = save_base64_image(data["photo"], enseignant.nom, enseignant.prenom)
            folder = "enseignants"
            folder_path = os.path.join(settings.MEDIA_ROOT, folder)
            os.makedirs(folder_path, exist_ok=True)

            if isinstance(content_file, str):
                filename = content_file
                field_path = filename
            else:
                filename = default_storage.save(os.path.join(folder, content_file.name), content_file)
                field_path = filename

            enseignant.photo = field_path
            # utiliser build_media_url (chemin relatif en DB, chemin JSON /media/...)
            photo_relative_path = build_media_url(field_path)
        except Exception as e:
            return JsonResponse({"message": f"Erreur lors de l'enregistrement de la photo : {e}"}, status=500)

    enseignant.save()

    # mise à jour du JSON enseignant
    if os.path.exists(JSON_PATH_ENSEIGNANT):
        with open(JSON_PATH_ENSEIGNANT, "r", encoding="utf-8") as f:
            try:
                enseignants = json.load(f)
            except json.JSONDecodeError:
                enseignants = []

        for e in enseignants:
            if e.get("id") == enseignant_id:
                e.update({
                    "nom": enseignant.nom,
                    "prenom": enseignant.prenom,
                    "date_naissance": str(enseignant.date_naissance),
                    "lieu_naissance": enseignant.lieu_naissance,
                    "matiere": enseignant.matiere,
                    "telephone": enseignant.telephone,
                    "email": enseignant.email,
                    "photo": photo_relative_path if photo_relative_path else e.get("photo"),
                })
                break

        with open(JSON_PATH_ENSEIGNANT, "w", encoding="utf-8") as f:
            json.dump(enseignants, f, indent=4, ensure_ascii=False)
    else:
        # fichier JSON manquant -> indiquer que la DB est modifiée
        return JsonResponse({"message": "Enseignant modifié en base, fichier JSON introuvable"}, status=200)

    return JsonResponse({"message": "Enseignant modifié (DB + JSON)", "photo": photo_relative_path}, status=200)

@csrf_exempt
def chercher_enseignant(request, enseignant_id):
    if request.method == "GET":
        try:
            enseignant = Enseignant.objects.get(id=enseignant_id)
        except Enseignant.DoesNotExist:
            return JsonResponse({"message": "Enseignant introuvable"}, status=404)

        DEFAULT_AVATAR = "https://via.placeholder.com/150?text=No+Photo"
        rel_path = relative_media_path(enseignant.photo)
        if rel_path:
            rel = build_media_url(rel_path)
            photo_url = request.build_absolute_uri(rel)
        else:
            photo_url = DEFAULT_AVATAR

        data = {
            "id": enseignant.id,
            "nom": enseignant.nom,
            "prenom": enseignant.prenom,
            "date_naissance": str(enseignant.date_naissance),
            "matiere": enseignant.matiere,
            "lieu_naissance": enseignant.lieu_naissance,
            "telephone": enseignant.telephone,
            "email": enseignant.email,
            "photo": photo_url,
            "photo_rel": rel,
        }

        return JsonResponse(data, status=200)

    return JsonResponse({"message": "Méthode non autorisée"}, status=405)

@csrf_exempt
def supprimer_enseignant(request, enseignant_id):
    if request.method != "DELETE":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    # ── 1. Récupérer l'enseignant en base ──────────────────────────────────
    try:
        enseignant = Enseignant.objects.get(id=enseignant_id)
    except Enseignant.DoesNotExist:
        return JsonResponse({"message": "Enseignant introuvable"}, status=404)

    # ── 2. Supprimer la photo du système de fichiers ───────────────────────
    photo_fs_path = filesystem_path_for(enseignant.photo)
    if photo_fs_path:
        try:
            if os.path.exists(photo_fs_path):
                os.remove(photo_fs_path)
        except Exception:
            pass

    # ── 3. Supprimer de la base de données ────────────────────────────────
    enseignant.delete()

    # ── 4. Supprimer du fichier JSON ──────────────────────────────────────
    if os.path.exists(JSON_PATH_ENSEIGNANT):
        try:
            with open(JSON_PATH_ENSEIGNANT, "r", encoding="utf-8") as f:
                enseignants = json.load(f)
        except (json.JSONDecodeError, IOError):
            enseignants = []

        # Comparaison sécurisée : convertir les deux en int
        enseignants = [
            e for e in enseignants
            if int(e["id"]) != int(enseignant_id)
        ]

        try:
            with open(JSON_PATH_ENSEIGNANT, "w", encoding="utf-8") as f:
                json.dump(enseignants, f, indent=4, ensure_ascii=False)
        except IOError as e:
            return JsonResponse({
                "message": f"Supprimé de la DB mais erreur JSON : {str(e)}",
                "id": enseignant_id
            }, status=207)

    return JsonResponse({
        "message": "Enseignant supprimé (DB + JSON)",
        "id": enseignant_id
    }, status=200)

@csrf_exempt
def lister_enseignants(request):
    if request.method == "GET":
        enseignants = Enseignant.objects.all()

        data = []
        DEFAULT_AVATAR = "https://via.placeholder.com/150?text=No+Photo"
        for e in enseignants:
            # déterminer chemin relatif puis produire URL absolue si fichier existe
            rel_path = relative_media_path(e.photo)
            if rel_path:
                rel = build_media_url(rel_path)
                photo_url = request.build_absolute_uri(rel)
            else:
                rel = None
                photo_url = DEFAULT_AVATAR

            data.append({
                "id": e.id,
                "nom": e.nom,
                "prenom": e.prenom,
                "date_naissance": str(e.date_naissance) if e.date_naissance else None,
                "matiere": e.matiere,
                "lieu_naissance": e.lieu_naissance,
                "telephone": e.telephone,
                "email": e.email,
                "photo": photo_url,
                "photo_rel": rel,
            })

        return JsonResponse(data, safe=False, status=200)

    return JsonResponse({"message": "Méthode non autorisée"}, status=405)

@csrf_exempt
def ajouter_personne(request):
    if request.method != "POST":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    # ── 1. Lecture du JSON envoyé ──────────────────────────────────────────
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"message": "JSON invalide"}, status=400)

    # ── 2. Validation des champs obligatoires ──────────────────────────────
    champs = [
        "nom", "prenom", "email", "date_naissance",
        "lieu_naissance", "telephone", "photo"
    ]
    for champ in champs:
        if champ not in data or not data[champ]:
            return JsonResponse(
                {"message": f"Le champ '{champ}' est manquant."},
                status=400
            )

    # ── 3. Vérification email déjà existant ────────────────────────────────
    if Personne.objects.filter(email=data["email"]).exists():
        return JsonResponse({"message": "Email déjà enregistré."}, status=400)

    # ── 4. Sauvegarde image Base64 ─────────────────────────────────────────
    try:
        content_file = save_base64_image(
            data["photo"],
            data["nom"],
            data["prenom"]
        )

        folder = "personnes"
        folder_path = os.path.join(settings.MEDIA_ROOT, folder)
        os.makedirs(folder_path, exist_ok=True)

        if isinstance(content_file, str):
            filename = (
                content_file
                if content_file.startswith(folder)
                else os.path.join(folder, os.path.basename(content_file))
            )
            field_path = filename
        else:
            name = getattr(content_file, "name", None) or f"{data['nom']}_{data['prenom']}.png"
            content_file.name = name
            field_path = default_storage.save(
                os.path.join(folder, content_file.name),
                content_file
            )

        photo_url = build_media_url(field_path)

    except Exception as e:
        return JsonResponse(
            {"message": f"Erreur lors de l'enregistrement de la photo : {e}"},
            status=500
        )

    # ── 5. Enregistrement en base de données ───────────────────────────────
    personne = Personne.objects.create(
        nom=data["nom"],
        prenom=data["prenom"],
        email=data["email"],
        date_naissance=data["date_naissance"],
        lieu_naissance=data["lieu_naissance"],
        telephone=data["telephone"],
        photo=field_path
    )

    # ── 6. Gestion du fichier JSON ─────────────────────────────────────────

    # S'assurer que le dossier parent existe
    json_dir = os.path.dirname(JSON_PATH_PERSONNE)
    if json_dir:
        os.makedirs(json_dir, exist_ok=True)

    if os.path.exists(JSON_PATH_PERSONNE):
        try:
            with open(JSON_PATH_PERSONNE, "r", encoding="utf-8") as f:
                personnes = json.load(f)
            if not isinstance(personnes, list):   # sécurité si le JSON est corrompu
                personnes = []
        except (json.JSONDecodeError, IOError, OSError):
            personnes = []
    else:
        personnes = []

    # ── 7. Objet personne à ajouter dans le JSON ───────────────────────────
    personne_json = {
        "id": personne.id,
        "nom": personne.nom,
        "prenom": personne.prenom,
        "email": personne.email,
        "date_naissance": str(personne.date_naissance),
        "lieu_naissance": personne.lieu_naissance,
        "telephone": personne.telephone,
        "photo": photo_url
    }

    personnes.append(personne_json)

    # Écriture atomique : on écrit dans un fichier temporaire puis on renomme
    # pour éviter un fichier JSON corrompu en cas de crash pendant l'écriture.
    tmp_path = JSON_PATH_PERSONNE + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(personnes, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, JSON_PATH_PERSONNE)   # opération atomique
    except (IOError, OSError, TypeError) as e:
        # Nettoyer le fichier temporaire si besoin
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return JsonResponse({
            "message": f"Ajouté en DB mais erreur écriture JSON : {str(e)}",
            "id_db": personne.id
        }, status=207)

    return JsonResponse(
        {
            "message": "Personne ajoutée avec succès (DB + JSON)",
            "id_db": personne.id,
            "id_json": personne.id   # ✅ Corrigé : next_id → personne.id
        },
        status=201
    )

@csrf_exempt
def modifier_personne(request, personne_id):
    if request.method != "PUT":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"message": "JSON invalide"}, status=400)

    # 1️⃣ Récupérer la personne
    try:
        personne = Personne.objects.get(id=personne_id)
    except Personne.DoesNotExist:
        return JsonResponse({"message": "Personne introuvable"}, status=404)

    # 2️⃣ Mise à jour des champs (sans photo)
    champs = [
        "nom", "prenom", "email",
        "date_naissance", "lieu_naissance", "telephone"
    ]

    for champ in champs:
        if champ in data:
            setattr(personne, champ, data[champ])

    # 3️⃣ GESTION PROPRE DE LA PHOTO
    photo_base64 = data.get("photo")
    photo_relative_path = None

    if photo_base64 and photo_base64.startswith("data:image"):
        # 🔥 supprimer l'ancienne photo
        if personne.photo:
            delete_base64_image(personne.photo)

        # 💾 sauvegarder la nouvelle photo
        photo_path = save_base64_image(
            photo_base64,
            personne.nom,
            personne.prenom
        )

        # photo_path = "personnes/xxx.png"
        personne.photo = photo_path
        photo_relative_path = f"{settings.MEDIA_URL}{photo_path}"  # /media/etudiants/xxx.png

    personne.save()

    # 4️⃣ Mise à jour du fichier JSON
    if not os.path.exists(JSON_PATH_PERSONNE):
        return JsonResponse({
            "message": "Personne modifiée en base, fichier JSON introuvable"
        }, status=200)

    with open(JSON_PATH_PERSONNE, "r", encoding="utf-8") as f:
        try:
            personnes = json.load(f)
        except json.JSONDecodeError:
            personnes = []

    for personne in personnes:
        if personne.get("id") == personne.id:
            personne.update({
                "nom": personne.nom,
                "prenom": personne.prenom,
                "email": personne.email,
                "date_naissance": str(personne.date_naissance),
                "lieu_naissance": personne.lieu_naissance,
                "telephone": personne.telephone,
                "photo": (
                    photo_relative_path
                    if photo_relative_path
                    else personne.get("photo")
                )
            })
            break

    # 5️⃣ Réécriture du fichier JSON
    with open(JSON_PATH_PERSONNE, "w", encoding="utf-8") as f:
        json.dump(personnes, f, indent=4, ensure_ascii=False)

    return JsonResponse({
        "message": "Personne modifié avec succès (DB + JSON)",
        "photo": photo_relative_path,
        "id": personne.id
    }, status=200)

@csrf_exempt
def supprimer_personne(request, personne_id):
    if request.method != "DELETE":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    # ── 1. Récupérer la personne en base ────────────────────────────────────
    try:
        personne = Personne.objects.get(id=personne_id)
    except Personne.DoesNotExist:
        return JsonResponse({"message": "Personne introuvable"}, status=404)

    # ── 2. Supprimer la photo du système de fichiers ───────────────────────
    photo_fs_path = filesystem_path_for(personne.photo)
    if photo_fs_path:
        try:
            if os.path.exists(photo_fs_path):
                os.remove(photo_fs_path)
        except Exception:
            pass

    # ── 3. Supprimer de la base de données ────────────────────────────────
    personne.delete()

    # ── 4. Supprimer du fichier JSON ──────────────────────────────────────
    json_debug = {}

    if not os.path.exists(JSON_PATH_PERSONNE):
        return JsonResponse({
            "message": "Supprimé de la DB mais fichier JSON introuvable",
            "json_path": JSON_PATH_PERSONNE
        }, status=207)

    try:
        with open(JSON_PATH_PERSONNE, "r", encoding="utf-8") as f:
            personnes = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return JsonResponse({
            "message": f"Supprimé de la DB mais erreur lecture JSON : {str(e)}"
        }, status=207)

    # DEBUG : afficher les types et valeurs des ids dans le JSON
    json_debug["personne_id_recu"] = personne_id
    json_debug["type_personne_id"] = str(type(personne_id))
    json_debug["ids_dans_json"] = [
        {"id": personne.get("id"), "type": str(type(personne.get("id")))}
        for personne in personnes
    ]

    avant = len(personnes)

    # Filtrage avec conversion str pour couvrir tous les cas
    personnes = [
        personne for personne in personnes
        if str(personne.get("id", "")) != str(personne_id)
    ]

    apres = len(personnes)
    json_debug["avant_suppression"] = avant
    json_debug["apres_suppression"] = apres
    json_debug["supprime"] = avant != apres

    try:
        with open(JSON_PATH_PERSONNE, "w", encoding="utf-8") as f:
            json.dump(personnes, f, indent=4, ensure_ascii=False)
    except IOError as e:
        return JsonResponse({
            "message": f"Supprimé de la DB mais erreur écriture JSON : {str(e)}",
            "debug": json_debug
        }, status=207)

    return JsonResponse({
        "message": "Personne supprimée avec succès (DB + JSON)",
        "id": personne_id,
        "debug": json_debug
    }, status=200)

@csrf_exempt
def lister_personnes(request):
    if request.method != "GET":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    personnes = Personne.objects.all()
    data = []
    DEFAULT_AVATAR = "https://via.placeholder.com/150?text=No+Photo"

    for personne in personnes:
        # Normaliser le chemin relatif puis produire URL publique (fallback front possible via photo_rel)
        rel_path = relative_media_path(personne.photo)
        if rel_path:
            rel = build_media_url(rel_path)              # ex "/media/etudiants/xxx.png"
            photo_url = request.build_absolute_uri(rel)  # ex "http://127.0.0.1:8008/media/etudiants/xxx.png"
        else:
            rel = None
            photo_url = DEFAULT_AVATAR

        data.append({
            "id": personne.id,
            "nom": personne.nom,
            "prenom": personne.prenom,
            "email": personne.email,
            "date_naissance": str(personne.date_naissance),
            "lieu_naissance": personne.lieu_naissance,
            "telephone": personne.telephone,
            "photo": photo_url,
            "photo_rel": rel,       # chemin public ("/media/...") utilisable côté front pour fallback
        })

    return JsonResponse(data, safe=False, status=200)

@csrf_exempt
def chercher_personne(request, personne_id):
    if request.method != "GET":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    try:
        personne = Personne.objects.get(id=personne_id)
    except Personne.DoesNotExist:
        return JsonResponse({"message": "Personne introuvable"}, status=404)

    DEFAULT_AVATAR = "https://via.placeholder.com/150?text=No+Photo"

    # Gestion de la photo (URL absolue si possible)
    rel_path = relative_media_path(personne.photo)
    if rel_path:
        rel = build_media_url(rel_path)
        photo_url = request.build_absolute_uri(rel)
    else:
        rel = None
        photo_url = DEFAULT_AVATAR

    data = {
        "id": personne.id,
        "nom": personne.nom,
        "prenom": personne.prenom,
        "date_naissance": str(personne.date_naissance),
        "lieu_naissance": personne.lieu_naissance,
        "telephone": personne.telephone,
        "email": personne.email,
        "photo": photo_url,
        "photo_rel": rel,
    }

    return JsonResponse(data, status=200)

"""
views_face.py — Vues Django pour la reconnaissance faciale
═══════════════════════════════════════════════════════════
Routes à ajouter dans urls.py :

    from .views_face import (
        scanner_face, train_face_model, training_status,
        face_stats, face_health, face_persons, diagnostic_face,
        face_reload
    )

    urlpatterns += [
        path("api/face/health/",         face_health),
        path("api/face/stats/",          face_stats),
        path("api/face/persons/",        face_persons),
        path("api/face/train/",          train_face_model),
        path("api/face/train/status/",   training_status),
        path("api/face/reload/",         face_reload),
        path("api/face/identify/",       scanner_face),
        path("api/face/identify/etudiants/",   scanner_face),
        path("api/face/identify/enseignants/", scanner_face),
        path("api/face/diagnostic/",     diagnostic_face),
    ]

Intégration avec :
    face_recognition_simple.py  → FaceRecognitionSimple
    face_service.py              → FaceRecognitionService (singleton)
    train.py                     → lancé en thread via train_face_model()
"""



"""
views_face.py — Vues Django pour la reconnaissance faciale
Routes à ajouter dans urls.py :

    path("api/face/health/",               face_health),
    path("api/face/stats/",                face_stats),
    path("api/face/persons/",              face_persons),
    path("api/face/train/",                train_face_model),
    path("api/face/train/status/",         training_status),
    path("api/face/reload/",               face_reload),
    path("api/face/identify/",             scanner_face),
    path("api/face/identify/etudiants/",   scanner_face),
    path("api/face/identify/enseignants/", scanner_face),
    path("api/scanner-face/",              scanner_face),
    path("api/face/diagnostic/",           diagnostic_face),
"""

import os, sys, uuid, time, threading, tempfile, traceback
import cv2, numpy as np

from django.http                  import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# ═════════════════════════════════════════════════════════════
# CHEMINS & IMPORT DU SERVICE IA
# ═════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_DIR   = os.path.join(BASE_DIR, "ai")

if AI_DIR not in sys.path:
    sys.path.insert(0, AI_DIR)

try:
    from face_service import face_service
    print("✅ face_service importé depuis", AI_DIR)
except Exception as e:
    face_service = None
    print(f"❌ face_service non disponible : {e}")


# ═════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════

def _cors(response):
    response["Access-Control-Allow-Origin"]  = "*"
    response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept"
    response["Access-Control-Max-Age"]       = "3600"
    return response

def _ok(data, status=200, **kwargs):
    return _cors(JsonResponse(
        {**data, "success": True}, status=status,
        json_dumps_params={"ensure_ascii": False, **kwargs}
    ))

def _err(msg, status=400, **extra):
    return _cors(JsonResponse(
        {"success": False, "error": msg, **extra},
        status=status,
        json_dumps_params={"ensure_ascii": False}
    ))

def _preflight(request):
    if request.method == "OPTIONS":
        return _cors(JsonResponse({}))
    return None

def _format_date(val):
    if val is None:          return None
    if isinstance(val, str): return val.split("T")[0] if val else None
    if hasattr(val, "strftime"): return val.strftime("%Y-%m-%d")
    return str(val)

def _image_from_request(request):
    """Extrait une image depuis multipart ou JSON base64."""
    import base64, json as _json

    if request.FILES.get("image"):
        f   = request.FILES["image"]
        arr = np.frombuffer(b"".join(f.chunks()), np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("cv2.imdecode a échoué sur le fichier uploadé")
        return img

    if request.content_type and "application/json" in request.content_type:
        body = _json.loads(request.body or "{}")
        b64  = body.get("image", "")
        if b64:
            if "," in b64: b64 = b64.split(",")[1]
            arr = np.frombuffer(base64.b64decode(b64), np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("cv2.imdecode a échoué sur le base64")
            return img

    raise ValueError("Aucune image — envoyez 'image' en multipart ou JSON base64")

def _img_to_tmpfile(img_bgr):
    tmp = os.path.join(tempfile.gettempdir(), f"face_{uuid.uuid4().hex}.jpg")
    if not cv2.imwrite(tmp, img_bgr):
        raise IOError(f"Impossible d'écrire : {tmp}")
    return tmp

def _enrich_from_django(result):
    """Enrichit result avec tous les champs depuis Django (email, téléphone, etc.)."""
    ptype     = result.get("type", "")
    nom       = result.get("nom",    "").strip()
    prenom    = result.get("prenom", "").strip()
    person_id = result.get("id")
    
    if not nom or not prenom:
        return

    try:
        if ptype == "etudiant":
            from api.models import Etudiant
            etud = (
                Etudiant.objects.filter(id=person_id).first() if person_id else None
            ) or Etudiant.objects.filter(prenom__iexact=prenom, nom__iexact=nom).first()
            
            if etud:
                result["email"]          = etud.email or ""
                result["telephone"]      = etud.telephone or ""
                result["date_naissance"] = _format_date(etud.date_naissance) if etud.date_naissance else ""
                result["lieu_naissance"] = etud.lieu_naissance or ""
                result["classe"]         = etud.classe or ""
                result["niveau_etude"]   = etud.niveau_etude or ""
                photo_path = relative_media_path(etud.photo) or result.get("photo", "")
                result["photo"]          = photo_path
                result["date_creation"]  = _format_date(etud.date_creation) if etud.date_creation else ""
                result["id"]             = etud.id
                print(f"✅ Photo étudiant {nom} {prenom}: {photo_path}")

        elif ptype == "enseignant":
            from api.models import Enseignant
            ens = (
                Enseignant.objects.filter(id=person_id).first() if person_id else None
            ) or Enseignant.objects.filter(prenom__iexact=prenom, nom__iexact=nom).first()
            
            if ens:
                result["email"]          = ens.email or ""
                result["telephone"]      = ens.telephone or ""
                result["date_naissance"] = _format_date(ens.date_naissance) if ens.date_naissance else ""
                result["lieu_naissance"] = ens.lieu_naissance or ""
                result["matiere"]        = ens.matiere or ""
                result["photo"]          = relative_media_path(ens.photo) or result.get("photo", "")
                result["date_creation"]  = _format_date(ens.date_creation) if ens.date_creation else ""
                result["id"]             = ens.id

        elif ptype == "personne":
            from api.models import Personne
            pers = (
                Personne.objects.filter(id=person_id).first() if person_id else None
            ) or Personne.objects.filter(prenom__iexact=prenom, nom__iexact=nom).first()
            
            if pers:
                result["email"]          = pers.email or ""
                result["telephone"]      = pers.telephone or ""
                result["date_naissance"] = _format_date(pers.date_naissance) if pers.date_naissance else ""
                result["lieu_naissance"] = pers.lieu_naissance or ""
                result["photo"]          = relative_media_path(pers.photo) or result.get("photo", "")
                result["date_creation"]  = _format_date(pers.date_creation) if pers.date_creation else ""
                result["id"]             = pers.id

    except Exception as e:
        print(f"⚠️  _enrich_from_django : {e}")


def _enrich_finances(result):
    """Enrichit result avec assurance + paiements depuis Django."""
    if result.get("assurance") is not None or result.get("paiements") is not None:
        return

    ptype     = result.get("type", "")
    nom       = result.get("nom",    "").strip()
    prenom    = result.get("prenom", "").strip()
    person_id = result.get("id")
    if not nom or not prenom:
        return

    try:
        if ptype == "etudiant":
            from api.models import Etudiant, AssuranceEtudiant
            etud = (
                Etudiant.objects.filter(id=person_id).first() if person_id else None
            ) or Etudiant.objects.filter(prenom__iexact=prenom, nom__iexact=nom).first()
            if not etud: return
            ass = AssuranceEtudiant.objects.filter(etudiant=etud).order_by("-date_paiement").first()
            if ass:
                result["assurance"] = {
                    "montant_total":   float(ass.montant_total),
                    "montant_paye":    float(ass.montant_paye),
                    "montant_restant": float(ass.montant_restant),
                    "statut":          ass.statut,
                    "date_paiement":   _format_date(ass.date_paiement),
                }

        elif ptype == "enseignant":
            from api.models import Enseignant, AssuranceEnseignant, PaiementEnseignant
            ens = (
                Enseignant.objects.filter(id=person_id).first() if person_id else None
            ) or Enseignant.objects.filter(prenom__iexact=prenom, nom__iexact=nom).first()
            if not ens: return
            ass = AssuranceEnseignant.objects.filter(enseignant=ens).order_by("-date_paiement").first()
            if ass:
                result["assurance"] = {
                    "montant_total":   float(ass.montant_total),
                    "montant_paye":    float(ass.montant_paye),
                    "montant_restant": float(ass.montant_restant),
                    "statut":          ass.statut,
                    "date_paiement":   _format_date(ass.date_paiement),
                }
            paiements = PaiementEnseignant.objects.filter(enseignant=ens)
            if paiements.exists():
                dernier = paiements.order_by("-date_paiement").first()
                result["paiements"] = {
                    "salaire_prevu":    float(dernier.salaire_prevu),
                    "total_paye":       float(sum(p.montant for p in paiements)),
                    "salaire_restant":  float(dernier.salaire_restant),
                    "nb_paiements":     paiements.count(),
                    "dernier_mois":     dernier.mois,
                    "derniere_annee":   dernier.annee,
                    "dernier_paiement": _format_date(dernier.date_paiement),
                }
    except Exception as e:
        print(f"⚠️  _enrich_finances : {e}")

def _build_match(result):
    """Construit le dict match compatible FaceRecognitionPage.jsx."""
    nom    = result.get("nom",    "")
    prenom = result.get("prenom", "")
    return {
        "identified":    True,
        "id":            result.get("id"),
        "type":          result.get("type",           ""),
        "name":          result.get("nom_complet") or f"{prenom} {nom}".strip(),
        "nom":           nom,
        "prenom":        prenom,
        "nom_complet":   result.get("nom_complet",    ""),
        "email":         result.get("email",          ""),
        "telephone":     result.get("telephone",      ""),
        "photo":         result.get("photo",          ""),
        "date_naissance":result.get("date_naissance", ""),
        "lieu_naissance":result.get("lieu_naissance", ""),
        "classe":        result.get("classe",         ""),
        "niveau":        result.get("niveau",         ""),
        "niveau_etude":  result.get("niveau_etude",   ""),
        "matiere":       result.get("matiere",        ""),
        "confidence":    result.get("confidence",     0),
        "distance":      result.get("distance"),
        "assurance":     result.get("assurance"),
        "paiements":     result.get("paiements"),
        "date_creation": result.get("date_creation",  ""),
    }


# ═════════════════════════════════════════════════════════════
# ÉTAT GLOBAL ENTRAÎNEMENT
# ═════════════════════════════════════════════════════════════
_train = {
    "running": False, "success": None, "message": "",
    "progress": 0, "started_at": None, "finished_at": None,
    "stats": None, "error": None,
}
_train_lock = threading.Lock()

def _run_training():
    global _train
    try:
        with _train_lock:
            _train.update({
                "running": True, "success": None,
                "message": "Scan des dossiers media...", "progress": 10,
                "error": None, "stats": None,
                "started_at": time.time(), "finished_at": None,
            })

        if face_service is None:
            raise RuntimeError("face_service non disponible")

        media_dir    = os.path.join(AI_DIR, "media")
        total_images = 0
        for cat in ("etudiants", "enseignants", "personnes"):
            cat_path = os.path.join(media_dir, cat)
            if os.path.isdir(cat_path):
                n = len([f for f in os.listdir(cat_path)
                         if f.lower().endswith((".jpg",".jpeg",".png"))])
                total_images += n
                print(f"   {cat:12} → {n} image(s)")

        if total_images == 0:
            raise ValueError("Aucune image dans ai/media/")

        with _train_lock:
            _train["message"]  = f"Encodage de {total_images} image(s) avec dlib..."
            _train["progress"] = 30

        success = face_service.train_model()

        with _train_lock:
            _train["message"]  = "Sauvegarde du modèle..."
            _train["progress"] = 90

        if not success:
            raise RuntimeError("train_model() a retourné False")

        stats = face_service.get_stats()
        with _train_lock:
            _train.update({
                "running": False, "success": True, "progress": 100,
                "message": f"Terminé — {stats.get('total', 0)} personne(s)",
                "stats": stats, "finished_at": time.time(), "error": None,
            })
        print(f"✅ Entraînement réussi — {stats.get('total', 0)} personne(s)")

    except Exception as e:
        traceback.print_exc()
        with _train_lock:
            _train.update({
                "running": False, "success": False, "progress": 0,
                "message": f"Erreur : {e}", "error": str(e),
                "finished_at": time.time(),
            })


# ═════════════════════════════════════════════════════════════
# VUES
# ═════════════════════════════════════════════════════════════

@csrf_exempt
def face_health(request):
    pre = _preflight(request)
    if pre: return pre
    if face_service is None:
        return _err("face_service non disponible", 503)
    stats     = face_service.get_stats()
    model_obj = getattr(face_service, "_model", None)
    return _ok({
        "model_trained": face_service.is_trained(),
        "dlib":          getattr(model_obj, "_use_dlib", None),
        "faces_loaded":  stats.get("total", 0),
        "breakdown": {
            "etudiants":   stats.get("etudiants",   0),
            "enseignants": stats.get("enseignants", 0),
            "personnes":   stats.get("personnes",   0),
        },
        "stats": stats,
    })


@csrf_exempt
def face_stats(request):
    pre = _preflight(request)
    if pre: return pre
    if face_service is None:
        return _err("Service non disponible", 503)
    try:
        return _ok({"stats": face_service.get_stats(), "personnes": face_service.get_all_persons()})
    except Exception as e:
        return _err(str(e), 500)


@csrf_exempt
def face_persons(request):
    pre = _preflight(request)
    if pre: return pre
    if face_service is None:
        return _err("Service non disponible", 503)
    try:
        persons = face_service.get_all_persons()
        return _ok({
            "etudiants":   persons.get("etudiants",   []),
            "enseignants": persons.get("enseignants", []),
            "personnes":   persons.get("personnes",   []),
            "total":       len(persons.get("etudiants", [])) + len(persons.get("enseignants", [])) + len(persons.get("personnes", [])),
        })
    except Exception as e:
        return _err(str(e), 500)


@csrf_exempt
def train_face_model(request):
    pre = _preflight(request)
    if pre: return pre
    if request.method != "POST":
        return _err("Méthode non autorisée", 405)
    if face_service is None:
        return _err("face_service non disponible", 503)
    with _train_lock:
        if _train["running"]:
            return _ok({"started": False, "running": True,
                        "message": "Entraînement déjà en cours",
                        "progress": _train["progress"]})
        _train.update({
            "running": True, "success": None, "progress": 2,
            "message": "Démarrage...", "error": None,
            "stats": None, "started_at": time.time(), "finished_at": None,
        })
    threading.Thread(target=_run_training, daemon=True, name="FaceTrainer").start()
    return _ok({"started": True, "running": True, "message": "Entraînement démarré", "progress": 2})


@csrf_exempt
def training_status(request):
    pre = _preflight(request)
    if pre: return pre
    with _train_lock:
        state = dict(_train)
    duration = None
    if state["started_at"]:
        duration = round((state["finished_at"] or time.time()) - state["started_at"], 1)
    return _ok({
        "running":  state["running"],
        "finished": (state["success"] is not None) and not state["running"],
        "trained":  state["success"] is True,
        "progress": state["progress"],
        "message":  state["message"],
        "error":    state["error"],
        "stats":    state["stats"],
        "duration": duration,
    })


@csrf_exempt
def face_reload(request):
    pre = _preflight(request)
    if pre: return pre
    if request.method != "POST":
        return _err("Méthode non autorisée", 405)
    if face_service is None:
        return _err("Service non disponible", 503)
    try:
        ok    = face_service.load_model()
        stats = face_service.get_stats()
        return _ok({
            "loaded":       ok,
            "faces_loaded": stats.get("total", 0),
            "breakdown": {
                "etudiants":   stats.get("etudiants",   0),
                "enseignants": stats.get("enseignants", 0),
            },
            "message": f"{stats.get('total',0)} visage(s) rechargé(s)" if ok
                       else "Aucun modèle trouvé — lancez d'abord /train/",
        })
    except Exception as e:
        return _err(str(e), 500)


@csrf_exempt
def scanner_face(request):
    """
    POST /api/face/identify/
    POST /api/face/identify/etudiants/
    POST /api/face/identify/enseignants/

    ✅ CORRECTION PRINCIPALE :
    - Seuil threshold abaissé à 40 (au lieu de 70)
      pour accepter les confidences autour de 50-60%
    - Retourne always identified=True si un nom est trouvé
      quelle que soit la confiance
    - Format de réponse unifié pour FaceRecognitionPage.jsx
    """
    pre = _preflight(request)
    if pre: return pre

    if request.method != "POST":
        return _err("Méthode non autorisée", 405)
    if face_service is None:
        return _err("face_service non disponible", 503)
    if not face_service.is_trained():
        return _err("Modèle non entraîné — POST /api/face/train/ d'abord", 400, identified=False)

    # Filtre par type selon l'URL
    path        = request.path.rstrip("/")
    auto_filter = (
        "etudiant"   if path.endswith("etudiants")  else
        "enseignant" if path.endswith("enseignants") else
        "tous"
    )

    # Lire la tolérance depuis le body
    import json as _json
    tolerance = 0.90   # 🎯 Augmenté pour meilleure correspondance
    try:
        if request.content_type and "application/json" in request.content_type:
            body      = _json.loads(request.body or "{}")
            tolerance = float(body.get("tolerance", 0.90))
        else:
            tolerance = float(request.POST.get("tolerance", 0.90))
    except (ValueError, TypeError):
        pass

    # ✅ Convertir tolerance (0-1) en threshold (plus bas = plus permissif)
    # tolerance 0.90 → threshold bas (permissif)
    # tolerance 0.40 → threshold haut (strict)
    threshold = max(20, int((1.0 - tolerance) * 100)) if tolerance < 0.95 else 20

    tmp_path = None
    try:
        img_bgr  = _image_from_request(request)
        tmp_path = _img_to_tmpfile(img_bgr)

        # Appel à FaceRecognitionSimple.recognize()
        result = face_service.recognize(tmp_path, threshold=threshold)

        stats    = face_service.get_stats()
        db_faces = stats.get("total", 0)

        # ── Aucun visage détecté ──────────────────────────────
        if not result.get("success"):
            return _ok({
                "identified": False,
                "message":    result.get("error", "Aucun visage détecté"),
                "confidence": 0,
                "debug": {"webcam_faces": 0, "db_faces": db_faces,
                          "message": result.get("error", ""), "tolerance": tolerance},
            })

        # ── ✅ CORRECTION : afficher même si confiance faible ──
        # On affiche le résultat dès qu'un nom est trouvé,
        # que identified soit True ou False côté dlib
        has_name = result.get("nom") or result.get("prenom") or result.get("nom_complet")

        if not result.get("identified") and not has_name:
            # Vraiment aucune correspondance
            return _ok({
                "identified": False,
                "message":    result.get("error", "Confiance insuffisante"),
                "confidence": result.get("confidence", 0),
                "distance":   result.get("distance"),
                "debug": {"webcam_faces": 1, "db_faces": db_faces,
                          "message": result.get("error", ""), "tolerance": tolerance},
            })

        # ── Filtre par type ───────────────────────────────────
        person_type = result.get("type", "")
        if auto_filter not in ("tous", "all", "") and person_type != auto_filter:
            return _ok({
                "identified": False,
                "message":    f"{person_type} détecté mais filtre={auto_filter}",
                "confidence": result.get("confidence", 0),
            })

        # ── Enrichir avec données Django (email, téléphone, etc.) ─
        _enrich_from_django(result)

        # ── Enrichir avec finances Django ─────────────────────
        _enrich_finances(result)

        # ── Construire la réponse ─────────────────────────────
        match = _build_match(result)
        
        print(f"🖼️  DEBUG scanner_face - match['photo']:", match.get("photo"))
        print(f"🖼️  DEBUG scanner_face - match keys:", list(match.keys()))

        return _ok({
            "identified":       True,
            "identified_count": 1,
            "matches":          [match],
            "personne":         match,          # rétrocompat
            "reconnaissance":   {"confidence": result.get("confidence", 0)},
            "debug": {
                "webcam_faces": 1,
                "db_faces":     db_faces,
                "message":      "Succès",
                "inference_ms": None,
                "tolerance":    tolerance,
                "threshold":    threshold,
                "confidence":   result.get("confidence", 0),
            },
        })

    except ValueError as e:
        return _err(str(e), 400, identified=False)
    except Exception as e:
        traceback.print_exc()
        return _err(str(e), 500, identified=False)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except Exception: pass


@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def diagnostic_face(request):
    pre = _preflight(request)
    if pre: return pre

    data = {}

    # Structure media
    AI_MEDIA = os.path.join(AI_DIR, "media")
    media    = {}
    for cat in ("etudiants", "enseignants", "personnes"):
        cat_path = os.path.join(AI_MEDIA, cat)
        if not os.path.isdir(cat_path):
            media[cat] = {"exists": False, "path": cat_path, "total_images": 0, "total_persons": 0}
            continue
        imgs    = [f for f in os.listdir(cat_path) if f.lower().endswith((".jpg",".jpeg",".png"))]
        persons = {}
        for img in imgs:
            parts = os.path.splitext(img)[0].split("_")
            if len(parts) >= 3:
                persons.setdefault(f"{parts[0]}_{parts[1]}", []).append(img)
        media[cat] = {
            "exists": True, "path": cat_path,
            "total_images": len(imgs), "total_persons": len(persons),
            "samples": list(persons.keys())[:5],
        }
    data["media_structure"] = media

    # Django DB
    try:
        from api.models import Etudiant, Enseignant, Personne, \
            AssuranceEtudiant, AssuranceEnseignant, PaiementEnseignant
        data["django_db"] = {
            "etudiants":   {"total": Etudiant.objects.count(),   "samples": [{"id": e.id, "prenom": e.prenom, "nom": e.nom} for e in Etudiant.objects.all()[:3]]},
            "enseignants": {"total": Enseignant.objects.count(), "samples": [{"id": e.id, "prenom": e.prenom, "nom": e.nom} for e in Enseignant.objects.all()[:3]]},
            "personnes":   {"total": Personne.objects.count()},
            "finances": {
                "assurances_etudiants":  {"total": AssuranceEtudiant.objects.count()},
                "assurances_enseignants":{"total": AssuranceEnseignant.objects.count()},
                "paiements_enseignants": {"total": PaiementEnseignant.objects.count()},
            },
        }
    except Exception as e:
        data["django_db"] = {"error": str(e)}

    # Modèle
    if face_service:
        try:
            stats     = face_service.get_stats()
            model_obj = getattr(face_service, "_model", None)
            data["face_model"] = {
                "loaded":         True,
                "trained":        stats.get("trained", False),
                "use_dlib":       getattr(model_obj, "_use_dlib", None),
                "nb_encodings":   len(getattr(model_obj, "_encodings", []) or []),
                "model_path":     getattr(face_service, "_model_path", ""),
                "stats":          stats,
            }
        except Exception as e:
            data["face_model"] = {"loaded": True, "error": str(e)}
    else:
        data["face_model"] = {"loaded": False, "error": "face_service non disponible"}

    # Checklist
    checks = []
    for cat in ("etudiants", "enseignants", "personnes"):
        m = media[cat]
        checks.append({
            "name":    f"ai/media/{cat}/",
            "status":  "ok" if m["exists"] and m["total_images"] > 0 else ("warning" if m["exists"] else "error"),
            "message": f"{m['total_images']} image(s) — {m['total_persons']} personne(s)" if m["exists"] else "Dossier manquant",
        })

    trained = face_service is not None and data["face_model"].get("trained", False)
    m_stats = data["face_model"].get("stats") or {}
    checks.append({
        "name":    "Modèle FaceRecognitionSimple",
        "status":  "ok" if trained else "error",
        "message": f"{m_stats.get('total',0)} personne(s) encodée(s)" if trained else "Non entraîné",
    })
    checks.append({
        "name":    "Moteur dlib",
        "status":  "ok" if data["face_model"].get("use_dlib") else "warning",
        "message": "dlib actif — précision 95-99%" if data["face_model"].get("use_dlib") else "OpenCV LBPH (pip install face_recognition)",
    })

    data["checks"]  = checks
    data["summary"] = {
        "ok":      sum(1 for c in checks if c["status"] == "ok"),
        "warning": sum(1 for c in checks if c["status"] == "warning"),
        "error":   sum(1 for c in checks if c["status"] == "error"),
    }

    return _ok({"diagnostic": data}, indent=2, ensure_ascii=False)

# Partie d'administrateur pour réinitialiser les données

@csrf_exempt
def assurance_etudiant(request):

    # ── GET : récupérer le dernier paiement par étudiant ──
    if request.method == "GET":
        paiements = AssuranceEtudiant.objects.values(
            "etudiant_id", "montant_total", "montant_paye", "montant_restant", "statut"
        ).order_by("etudiant_id", "-date_paiement")

        derniers = {}
        for p in paiements:
            eid = p["etudiant_id"]
            if eid not in derniers:
                derniers[eid] = {
                    "etudiant_id":     eid,
                    "montant_total":   float(p["montant_total"]),
                    "montant_paye":    float(p["montant_paye"]),
                    "montant_restant": float(p["montant_restant"]),
                    "statut":          p["statut"],
                }

        return JsonResponse(list(derniers.values()), safe=False, status=200)

    # ── POST : enregistrer un nouveau paiement ──
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message": "JSON invalide"}, status=400)

        etudiant_id     = data.get("etudiant_id")
        montant_total   = data.get("montant_total")
        montant_paye    = data.get("montant_paye")
        montant_restant = data.get("montant_restant")

        if not all([etudiant_id, montant_total is not None, montant_paye is not None]):
            return JsonResponse(
                {"message": "Champs manquants (etudiant_id, montant_total, montant_paye)"},
                status=400
            )

        try:
            etudiant = Etudiant.objects.get(id=etudiant_id)
        except Etudiant.DoesNotExist:
            return JsonResponse({"message": "Étudiant introuvable"}, status=404)

        try:
            montant_total   = float(montant_total)
            montant_paye    = float(montant_paye)
            montant_restant = float(montant_restant) if montant_restant is not None else montant_total - montant_paye
        except (ValueError, TypeError):
            return JsonResponse({"message": "Montants invalides"}, status=400)

        if montant_paye > montant_total:
            return JsonResponse(
                {"message": "Le montant payé ne peut pas dépasser le montant total"},
                status=400
            )

        # Sauvegarde en base via le modèle AssuranceEtudiant
        paiement = AssuranceEtudiant.objects.create(
            etudiant=etudiant,
            montant_total=montant_total,
            montant_paye=montant_paye,
            montant_restant=montant_restant,
        )

        return JsonResponse({
            "message": "Paiement d'assurance enregistré avec succès",
            "id":              paiement.id,
            "etudiant": {
                "id":     etudiant.id,
                "nom":    etudiant.nom,
                "prenom": etudiant.prenom,
            },
            "montant_total":   float(paiement.montant_total),
            "montant_paye":    float(paiement.montant_paye),
            "montant_restant": float(paiement.montant_restant),
            "statut":          paiement.statut,
            "date_paiement":   paiement.date_paiement.strftime("%Y-%m-%d %H:%M"),
        }, status=201)

    return JsonResponse({"message": "Méthode non autorisée"}, status=405)

@csrf_exempt
def assurance_etudiant_config(request):
    """Définir le montant mensuel d'assurance pour un étudiant"""
    if request.method != "POST":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"message": "JSON invalide"}, status=400)

    # Récupérer l'ID et le montant
    etudiant_id = data.get("etudiant_id")
    montant_mensuel = data.get("montant_mensuel")

    # Validation
    if etudiant_id is None:
        return JsonResponse({"message": "Champ 'etudiant_id' manquant"}, status=400)
    
    if montant_mensuel is None:
        return JsonResponse({"message": "Champ 'montant_mensuel' manquant"}, status=400)

    # Vérifier que l'étudiant existe
    try:
        etudiant = Etudiant.objects.get(id=etudiant_id)
    except Etudiant.DoesNotExist:
        return JsonResponse({"message": "Étudiant introuvable"}, status=404)

    # Validation du montant
    try:
        montant_mensuel = float(montant_mensuel)
        if montant_mensuel <= 0:
            return JsonResponse({"message": "Le montant doit être supérieur à 0"}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"message": "Montant invalide"}, status=400)

    # Option 1 : Enregistrer dans le modèle Etudiant directement
    # (Ajoute ce champ dans models.py si pas encore fait)
    etudiant.assurance_montant_mensuel = montant_mensuel
    etudiant.save()

    # Option 2 : OU créer un modèle dédié ConfigAssuranceEtudiant
    # from .models import ConfigAssuranceEtudiant
    # ConfigAssuranceEtudiant.objects.update_or_create(
    #     etudiant=etudiant,
    #     defaults={'montant_mensuel': montant_mensuel}
    # )

    return JsonResponse({
        "message": "Montant mensuel configuré avec succès",
        "etudiant": {
            "id": etudiant.id,
            "nom": etudiant.nom,
            "prenom": etudiant.prenom
        },
        "montant_mensuel": montant_mensuel
    }, status=201)

@csrf_exempt
def assurance_enseignant(request):

    # ── GET : récupérer le dernier paiement par enseignant ──
    if request.method == "GET":
        paiements = AssuranceEnseignant.objects.values(
            "enseignant_id", "montant_total", "montant_paye", "montant_restant", "statut"
        ).order_by("enseignant_id", "-date_paiement")

        derniers = {}
        for p in paiements:
            eid = p["enseignant_id"]
            if eid not in derniers:
                derniers[eid] = {
                    "enseignant_id":   eid,
                    "montant_total":   float(p["montant_total"]),
                    "montant_paye":    float(p["montant_paye"]),
                    "montant_restant": float(p["montant_restant"]),
                    "statut":          p["statut"],
                }

        return JsonResponse(list(derniers.values()), safe=False, status=200)

    # ── POST : enregistrer un nouveau paiement ──
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message": "JSON invalide"}, status=400)

        enseignant_id   = data.get("enseignant_id")
        montant_total   = data.get("montant_total")
        montant_paye    = data.get("montant_paye")
        montant_restant = data.get("montant_restant")

        if not all([enseignant_id, montant_total is not None, montant_paye is not None]):
            return JsonResponse(
                {"message": "Champs manquants (enseignant_id, montant_total, montant_paye)"},
                status=400
            )

        try:
            enseignant = Enseignant.objects.get(id=enseignant_id)
        except Enseignant.DoesNotExist:
            return JsonResponse({"message": "Enseignant introuvable"}, status=404)

        try:
            montant_total   = float(montant_total)
            montant_paye    = float(montant_paye)
            montant_restant = float(montant_restant) if montant_restant is not None else montant_total - montant_paye
        except (ValueError, TypeError):
            return JsonResponse({"message": "Montants invalides"}, status=400)

        if montant_paye > montant_total:
            return JsonResponse(
                {"message": "Le montant payé ne peut pas dépasser le montant total"},
                status=400
            )

        # Sauvegarde en base via le modèle AssuranceEnseignant
        paiement = AssuranceEnseignant.objects.create(
            enseignant=enseignant,
            montant_total=montant_total,
            montant_paye=montant_paye,
            montant_restant=montant_restant,
        )

        return JsonResponse({
            "message": "Paiement d'assurance enregistré avec succès",
            "id":              paiement.id,
            "enseignant": {
                "id":      enseignant.id,
                "nom":     enseignant.nom,
                "prenom":  enseignant.prenom,
                "matiere": enseignant.matiere,
            },
            "montant_total":   float(paiement.montant_total),
            "montant_paye":    float(paiement.montant_paye),
            "montant_restant": float(paiement.montant_restant),
            "statut":          paiement.statut,
            "date_paiement":   paiement.date_paiement.strftime("%Y-%m-%d %H:%M"),
        }, status=201)

    return JsonResponse({"message": "Méthode non autorisée"}, status=405)

@csrf_exempt
def assurance_enseignant_config(request):
    """Définir le montant mensuel d'assurance pour un enseignant"""
    if request.method != "POST":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"message": "JSON invalide"}, status=400)

    # Récupérer l'ID et le montant
    enseignant_id = data.get("enseignant_id")
    montant_mensuel = data.get("montant_mensuel")

    # Validation
    if enseignant_id is None:
        return JsonResponse({"message": "Champ 'enseignant_id' manquant"}, status=400)
    
    if montant_mensuel is None:
        return JsonResponse({"message": "Champ 'montant_mensuel' manquant"}, status=400)

    # Vérifier que l'enseignant existe
    try:
        enseignant = Enseignant.objects.get(id=enseignant_id)
    except Enseignant.DoesNotExist:
        return JsonResponse({"message": "Enseignant introuvable"}, status=404)

    # Validation du montant
    try:
        montant_mensuel = float(montant_mensuel)
        if montant_mensuel <= 0:
            return JsonResponse({"message": "Le montant doit être supérieur à 0"}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"message": "Montant invalide"}, status=400)

    # Option 1 : Enregistrer dans le modèle Enseignant directement
    # (Ajoute ce champ dans models.py si pas encore fait)
    enseignant.assurance_montant_mensuel = montant_mensuel
    enseignant.save()

    # Option 2 : OU créer un modèle dédié ConfigAssuranceEnseignant
    # from .models import ConfigAssuranceEnseignant
    # ConfigAssuranceEnseignant.objects.update_or_create(
    #     enseignant=enseignant,
    #     defaults={'montant_mensuel': montant_mensuel}
    # )

    return JsonResponse({
        "message": "Montant mensuel configuré avec succès",
        "enseignant": {
            "id": enseignant.id,
            "nom": enseignant.nom,
            "prenom": enseignant.prenom,
            "matiere": enseignant.matiere
        },
        "montant_mensuel": montant_mensuel
    }, status=201)

@csrf_exempt
def paiement_enseignant(request):

    # ── GET : récupérer le dernier paiement par enseignant ──
    if request.method == "GET":
        paiements = PaiementEnseignant.objects.values(
            "enseignant_id", "montant", "salaire_prevu", "salaire_restant", "mois", "annee", "date_paiement"
        ).order_by("enseignant_id", "-date_paiement")

        derniers = {}
        for p in paiements:
            eid = p["enseignant_id"]
            if eid not in derniers:
                derniers[eid] = {
                    "enseignant_id":   eid,
                    "salaire_prevu":   float(p["salaire_prevu"]),
                    "salaire_restant": float(p["salaire_restant"]),
                    "montant":         float(p["montant"]),
                }

        return JsonResponse(list(derniers.values()), safe=False, status=200)

    # ── POST : enregistrer un nouveau paiement ──
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message": "JSON invalide"}, status=400)

        enseignant_id   = data.get("enseignant_id")
        mois            = data.get("mois")
        annee           = data.get("annee")
        salaire_prevu   = data.get("salaire_prevu")
        salaire_paye    = data.get("salaire_paye")
        salaire_restant = data.get("salaire_restant")

        if not all([
            enseignant_id,
            mois is not None,
            annee is not None,
            salaire_prevu is not None,
            salaire_paye is not None,
        ]):
            return JsonResponse(
                {"message": "Champs manquants (enseignant_id, mois, annee, salaire_prevu, salaire_paye)"},
                status=400
            )

        try:
            enseignant = Enseignant.objects.get(id=enseignant_id)
        except Enseignant.DoesNotExist:
            return JsonResponse({"message": "Enseignant introuvable"}, status=404)

        try:
            mois            = int(mois)
            annee           = int(annee)
            salaire_prevu   = float(salaire_prevu)
            salaire_paye    = float(salaire_paye)
            salaire_restant = float(salaire_restant) if salaire_restant is not None else salaire_prevu - salaire_paye
        except (ValueError, TypeError):
            return JsonResponse({"message": "Données invalides"}, status=400)

        if not (1 <= mois <= 12):
            return JsonResponse({"message": "Mois invalide (doit être entre 1 et 12)"}, status=400)

        if not (2020 <= annee <= 2050):
            return JsonResponse({"message": "Année invalide"}, status=400)

        if salaire_paye > salaire_prevu:
            return JsonResponse(
                {"message": "Le salaire payé ne peut pas dépasser le salaire prévu"},
                status=400
            )

        # ── Sauvegarde en base avec tous les champs ──
        paiement = PaiementEnseignant.objects.create(
            enseignant=enseignant,
            montant=salaire_paye,
            salaire_prevu=salaire_prevu,
            salaire_restant=salaire_restant,
            mois=mois,
            annee=annee,
        )

        mois_noms = [
            "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ]

        return JsonResponse({
            "message":         "Paiement de salaire enregistré avec succès",
            "id":              paiement.id,
            "enseignant": {
                "id":      enseignant.id,
                "nom":     enseignant.nom,
                "prenom":  enseignant.prenom,
                "matiere": enseignant.matiere,
            },
            "periode":         f"{mois_noms[mois]} {annee}",
            "mois":            mois,
            "annee":           annee,
            "salaire_prevu":   float(paiement.salaire_prevu),
            "salaire_paye":    float(paiement.montant),
            "salaire_restant": float(paiement.salaire_restant),
            "statut":          "complet" if salaire_restant == 0 else "partiel",
            "date_paiement":   paiement.date_paiement.strftime("%Y-%m-%d %H:%M"),
        }, status=201)

    return JsonResponse({"message": "Méthode non autorisée"}, status=405)

# tout les routes du enseignant

def _json_response(data, status=200):
    """JsonResponse avec headers CORS sur chaque réponse"""
    response = JsonResponse(data, status=status)
    response["Access-Control-Allow-Origin"]  = "*"
    response["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def login_enseignant(request):
    """
    POST /api/login_enseignant/
    body: { "nom": "Alami", "prenom": "Ahmed", "matiere": "Mathématiques" }
    """

    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"]  = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return _json_response({"message": "JSON invalide"}, 400)

    nom     = (data.get("nom")     or "").strip()
    prenom  = (data.get("prenom")  or "").strip()
    matiere = (data.get("matiere") or "").strip()

    if not all([nom, prenom, matiere]):
        return _json_response(
            {"message": "Veuillez remplir tous les champs (nom, prenom, matiere)"},
            400
        )

    try:
        enseignant = Enseignant.objects.get(
            nom__iexact=nom,
            prenom__iexact=prenom,
            matiere__iexact=matiere,
        )
    except Enseignant.DoesNotExist:
        return _json_response(
            {"message": "Aucun enseignant trouvé avec ces informations."},
            404
        )
    except Exception as e:
        return _json_response({"message": f"Erreur serveur : {str(e)}"}, 500)

    return _json_response({
        "message":   "Connexion réussie",
        "id":        enseignant.id,
        "nom":       enseignant.nom,
        "prenom":    enseignant.prenom,
        "matiere":   enseignant.matiere,
        "email":     enseignant.email,
        "telephone": enseignant.telephone or "",
    }, 200)

@csrf_exempt
def enseignant_detail(request, enseignant_id):
    if request.method == "OPTIONS":
        return _json_response({})
    if request.method != "GET":
        return _json_response({"message": "Méthode non autorisée"}, 405)

    try:
        ens = Enseignant.objects.get(id=enseignant_id)
    except Enseignant.DoesNotExist:
        return _json_response({"message": "Enseignant introuvable"}, 404)
    except Exception as e:
        return _json_response({"message": f"Erreur serveur : {str(e)}"}, 500)

    # ── Présences saisies (par matière de l'enseignant) ──
    nb_presences_saisies = Absence.objects.filter(
        matiere__iexact=ens.matiere
    ).count()

    # ── Étudiants du niveau suivi ──
    niveaux = Note.objects.filter(
        enseignant=ens
    ).values_list("etudiant__niveau_etude", flat=True).distinct()

    nb_etudiants_niveau = Etudiant.objects.filter(
        niveau_etude__in=list(niveaux)
    ).count()

    # ── Moyenne par classe et par semestre ──
    def calc_moyenne(qs):
        if not qs.exists():
            return None
        tp = sum(float(n.note) * float(n.coefficient) for n in qs)
        tc = sum(float(n.coefficient) for n in qs)
        return round(tp / tc, 2) if tc > 0 else None

    # Récupérer les classes distinctes via les étudiants eux-mêmes
    etudiants_ids = Note.objects.filter(
        enseignant=ens
    ).values_list("etudiant_id", flat=True).distinct()

    classes_distinctes = Etudiant.objects.filter(
        id__in=etudiants_ids
    ).values_list("classe", flat=True).distinct()

    moyennes_par_classe = []
    for classe in classes_distinctes:
        etudiants_classe = Etudiant.objects.filter(
            id__in=etudiants_ids, classe=classe
        )
        notes_classe = Note.objects.filter(
            enseignant=ens, etudiant__in=etudiants_classe
        )
        moyennes_par_classe.append({
            "classe":           classe,
            "moyenne_s1":       calc_moyenne(notes_classe.filter(semestre=1)),
            "moyenne_s2":       calc_moyenne(notes_classe.filter(semestre=2)),
            "moyenne_generale": calc_moyenne(notes_classe),
            "nb_etudiants":     etudiants_classe.count(),
        })

    # Trier par nom de classe
    moyennes_par_classe.sort(key=lambda x: x["classe"])

    return _json_response({
        "id":        ens.id,
        "nom":       ens.nom,
        "prenom":    ens.prenom,
        "email":     ens.email,
        "telephone": ens.telephone or "",
        "matiere":   ens.matiere,
        "stats": {
            "presences_saisies":   nb_presences_saisies,
            "etudiants_du_niveau": nb_etudiants_niveau,
            "moyennes_par_classe": moyennes_par_classe,
        }
    }, 200)

@csrf_exempt
def absences_enseignant(request):

    if request.method == "OPTIONS":
        return _json_response({})

    # ── GET ──
    if request.method == "GET":
        etudiant_id = request.GET.get("etudiant_id")
        classe      = request.GET.get("classe")

        qs = Absence.objects.select_related("etudiant").order_by("-date")
        if etudiant_id:
            qs = qs.filter(etudiant_id=etudiant_id)
        if classe:
            qs = qs.filter(etudiant__classe__iexact=classe)

        data = [{
            "id":           a.id,
            "etudiant_id":  a.etudiant.id,
            "etudiant_nom": f"{a.etudiant.prenom} {a.etudiant.nom}",
            "classe":       a.etudiant.classe,
            "date":         a.date.strftime("%Y-%m-%d"),
            "matiere":      a.matiere,
            "type_absence": a.type_absence,
        } for a in qs]

        return _json_response(data, 200)

    # ── POST ──
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except Exception:
            return _json_response({"message": "JSON invalide"}, 400)

        etudiant_id  = data.get("etudiant_id")
        date_val     = data.get("date")
        matiere      = (data.get("matiere") or "").strip()
        type_absence = (data.get("type_absence") or "").strip()

        # Validation champs
        if not etudiant_id:
            return _json_response({"message": "Champ manquant : etudiant_id"}, 400)
        if not date_val:
            return _json_response({"message": "Champ manquant : date"}, 400)
        if not matiere:
            return _json_response({"message": "Champ manquant : matiere"}, 400)
        if not type_absence:
            return _json_response({"message": "Champ manquant : type_absence"}, 400)

        # Validation type_absence
        types_valides = ["present", "absence", "retard"]
        if type_absence not in types_valides:
            return _json_response(
                {"message": f"type_absence invalide. Valeurs : {types_valides}"},
                400
            )

        # Validation format date
        try:
            date_obj = datetime.strptime(str(date_val), "%Y-%m-%d").date()
        except ValueError:
            return _json_response(
                {"message": f"Format date invalide : '{date_val}'. Attendu : YYYY-MM-DD"},
                400
            )

        # Récupérer étudiant
        try:
            etudiant = Etudiant.objects.get(id=int(etudiant_id))
        except Etudiant.DoesNotExist:
            return _json_response({"message": f"Étudiant id={etudiant_id} introuvable"}, 404)
        except Exception as e:
            return _json_response({"message": f"Erreur etudiant : {str(e)}"}, 500)

        # Créer ou mettre à jour
        try:
            absence, created = Absence.objects.get_or_create(
                etudiant=etudiant,
                date=date_obj,
                matiere=matiere,
                defaults={"type_absence": type_absence},
            )
            if not created:
                absence.type_absence = type_absence
                absence.save()
        except Exception as e:
            return _json_response({"message": f"Erreur création absence : {str(e)}"}, 500)

        return _json_response({
            "message":      "Présence enregistrée" if created else "Présence mise à jour",
            "id":           absence.id,
            "etudiant":     {"id": etudiant.id, "nom": etudiant.nom, "prenom": etudiant.prenom},
            "date":         absence.date.strftime("%Y-%m-%d"),
            "matiere":      absence.matiere,
            "type_absence": absence.type_absence,
        }, 201 if created else 200)

    # ── DELETE ──
    if request.method == "DELETE":
        absence_id = request.GET.get("absence_id")
        if not absence_id:
            return _json_response({"message": "Paramètre absence_id manquant"}, 400)
        try:
            absence = Absence.objects.get(id=absence_id)
            absence.delete()
            return _json_response({"message": "Absence supprimée"}, 200)
        except Absence.DoesNotExist:
            return _json_response({"message": "Absence introuvable"}, 404)

    return _json_response({"message": "Méthode non autorisée"}, 405)

@csrf_exempt
def notes_enseignant(request):

    # ── GET ──
    if request.method == "GET":
        enseignant_id = request.GET.get("enseignant_id")
        if not enseignant_id:
            return JsonResponse({"message": "Paramètre enseignant_id manquant"}, status=400)

        try:
            enseignant = Enseignant.objects.get(id=enseignant_id)
        except Enseignant.DoesNotExist:
            return JsonResponse({"message": "Enseignant introuvable"}, status=404)

        notes = Note.objects.filter(
            enseignant=enseignant
        ).select_related("etudiant").order_by("-date_saisie")

        data = [{
            "id":           n.id,
            "etudiant_id":  n.etudiant.id,
            "etudiant_nom": f"{n.etudiant.prenom} {n.etudiant.nom}",
            "classe":       n.etudiant.classe,
            "matiere":      n.matiere,
            "note":         float(n.note),
            "coefficient":  float(n.coefficient),
            "type_examen":  n.type_examen,
            "semestre":     n.semestre,
            "date_saisie":  n.date_saisie.strftime("%Y-%m-%d"),
        } for n in notes]

        return JsonResponse(data, safe=False, status=200)

    # ── POST ──
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message": "JSON invalide"}, status=400)

        enseignant_id = data.get("enseignant_id")
        etudiant_id   = data.get("etudiant_id")
        note_val      = data.get("note")
        matiere       = data.get("matiere")
        coefficient   = data.get("coefficient", 1)
        type_examen   = data.get("type_examen", "devoir")
        semestre      = data.get("semestre", 1)

        if not all([enseignant_id, etudiant_id, note_val is not None, matiere]):
            return JsonResponse({"message": "Champs manquants (enseignant_id, etudiant_id, note, matiere)"}, status=400)

        try:
            enseignant = Enseignant.objects.get(id=enseignant_id)
        except Enseignant.DoesNotExist:
            return JsonResponse({"message": "Enseignant introuvable"}, status=404)

        try:
            etudiant = Etudiant.objects.get(id=etudiant_id)
        except Etudiant.DoesNotExist:
            return JsonResponse({"message": "Étudiant introuvable"}, status=404)

        try:
            note_val    = float(note_val)
            coefficient = float(coefficient)
            semestre    = int(semestre)
        except (ValueError, TypeError):
            return JsonResponse({"message": "Valeurs numériques invalides"}, status=400)

        if not (0 <= note_val <= 20):
            return JsonResponse({"message": "La note doit être entre 0 et 20"}, status=400)

        note = Note.objects.create(
            enseignant=enseignant,
            etudiant=etudiant,
            matiere=matiere,
            note=note_val,
            coefficient=coefficient,
            type_examen=type_examen,
            semestre=semestre,
        )

        return JsonResponse({
            "message":     "Note enregistrée avec succès",
            "id":          note.id,
            "etudiant":    {"id": etudiant.id, "nom": etudiant.nom, "prenom": etudiant.prenom},
            "matiere":     note.matiere,
            "note":        float(note.note),
            "coefficient": float(note.coefficient),
            "type_examen": note.type_examen,
            "semestre":    note.semestre,
        }, status=201)

    # ── PUT — modifier une note ──
    if request.method == "PUT":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message": "JSON invalide"}, status=400)

        note_id = data.get("note_id")
        if not note_id:
            return JsonResponse({"message": "Champ note_id manquant"}, status=400)

        try:
            note = Note.objects.get(id=note_id)
        except Note.DoesNotExist:
            return JsonResponse({"message": "Note introuvable"}, status=404)

        if "note" in data:
            val = float(data["note"])
            if not (0 <= val <= 20):
                return JsonResponse({"message": "La note doit être entre 0 et 20"}, status=400)
            note.note = val
        if "coefficient" in data:
            note.coefficient = float(data["coefficient"])
        if "type_examen" in data:
            note.type_examen = data["type_examen"]
        if "semestre" in data:
            note.semestre = int(data["semestre"])
        note.save()

        return JsonResponse({
            "message":     "Note mise à jour",
            "id":          note.id,
            "note":        float(note.note),
            "coefficient": float(note.coefficient),
        }, status=200)

    # ── DELETE ──
    if request.method == "DELETE":
        note_id = request.GET.get("note_id")
        if not note_id:
            return JsonResponse({"message": "Paramètre note_id manquant"}, status=400)

        try:
            note = Note.objects.get(id=note_id)
        except Note.DoesNotExist:
            return JsonResponse({"message": "Note introuvable"}, status=404)

        note.delete()
        return JsonResponse({"message": "Note supprimée"}, status=200)

    return JsonResponse({"message": "Méthode non autorisée"}, status=405)

@csrf_exempt
def lister_classes(request):
    if request.method != "GET":
        return JsonResponse({"message": "Méthode non autorisée"}, status=405)

    classes = Etudiant.objects.values_list("classe", flat=True).distinct().order_by("classe")
    return JsonResponse({"classes": list(classes)}, status=200)

# tout les routes du etudiant

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def login_etudiant(request):
    """
    POST /api/login_etudiant/
    body: { "nom": "Bellamlih", "prenom": "Hamza", "classe": "L2 Info", "niveau_etude": "licence" }
    """

    # Preflight CORS
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"]  = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return _json_response({"message": "JSON invalide"}, 400)

    nom          = (data.get("nom",          "") or "").strip()
    prenom       = (data.get("prenom",       "") or "").strip()
    classe       = (data.get("classe",       "") or "").strip()
    niveau_etude = (data.get("niveau_etude", "") or "").strip()

    if not all([nom, prenom, classe, niveau_etude]):
        return _json_response(
            {"message": "Veuillez remplir tous les champs (nom, prenom, classe, niveau_etude)"},
            400
        )

    try:
        etudiant = Etudiant.objects.get(
            nom__iexact=nom,
            prenom__iexact=prenom,
            classe__iexact=classe,
            niveau_etude__iexact=niveau_etude,
        )
    except Etudiant.DoesNotExist:
        return _json_response(
            {"message": "Aucun étudiant trouvé avec ces informations."},
            404
        )
    except Exception as e:
        return _json_response({"message": f"Erreur serveur : {str(e)}"}, 500)

    return _json_response({
        "message":      "Connexion réussie",
        "id":           etudiant.id,
        "nom":          etudiant.nom,
        "prenom":       etudiant.prenom,
        "classe":       etudiant.classe,
        "niveau_etude": etudiant.niveau_etude,
        "email":        etudiant.email,
        "telephone":    etudiant.telephone or "",
    }, 200)


def _json_response(data, status=200):
    """JsonResponse avec headers CORS sur chaque réponse"""
    response = JsonResponse(data, status=status)
    response["Access-Control-Allow-Origin"]  = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@csrf_exempt
def etudiant_detail(request, etudiant_id):
    if request.method == "OPTIONS":
        return _json_response({})
    if request.method != "GET":
        return _json_response({"message": "Méthode non autorisée"}, 405)

    try:
        etud = Etudiant.objects.get(id=etudiant_id)
    except Etudiant.DoesNotExist:
        return _json_response({"message": "Étudiant introuvable"}, 404)
    except Exception as e:
        return _json_response({"message": f"Erreur serveur : {str(e)}"}, 500)

    # Nombre d'absences de l'étudiant
    nb_absences = Absence.objects.filter(etudiant=etud, type_absence="absence").count()

    # Nombre d'étudiants dans la même classe
    nb_etudiants_classe = Etudiant.objects.filter(classe=etud.classe).count()

    return _json_response({
        "id":           etud.id,
        "nom":          etud.nom,
        "prenom":       etud.prenom,
        "email":        etud.email,
        "telephone":    etud.telephone or "",
        "classe":       etud.classe,
        "niveau_etude": etud.niveau_etude,
        "stats": {
            "absences":           nb_absences,
            "etudiants_en_classe": nb_etudiants_classe,
        }
    }, 200)

@csrf_exempt
def notes_etudiant(request):
    """
    GET /api/notes_etudiant/?etudiant_id=1
    GET /api/notes_etudiant/?etudiant_id=1&semestre=1
    """
    if request.method == "OPTIONS":
        return _json_response({})

    if request.method != "GET":
        return _json_response({"message": "Méthode non autorisée"}, 405)

    etudiant_id = request.GET.get("etudiant_id")
    semestre    = request.GET.get("semestre")

    if not etudiant_id:
        return _json_response({"message": "Paramètre etudiant_id manquant"}, 400)

    try:
        etudiant = Etudiant.objects.get(id=etudiant_id)
    except Etudiant.DoesNotExist:
        return _json_response({"message": "Étudiant introuvable"}, 404)
    except Exception as e:
        return _json_response({"message": f"Erreur serveur : {str(e)}"}, 500)

    notes_qs = Note.objects.filter(etudiant=etudiant).select_related("enseignant")
    if semestre:
        try:
            notes_qs = notes_qs.filter(semestre=int(semestre))
        except ValueError:
            return _json_response({"message": "semestre doit être 1 ou 2"}, 400)

    notes_qs = notes_qs.order_by("matiere", "-date_saisie")

    # Grouper par matière
    matieres = {}
    for n in notes_qs:
        m = n.matiere
        if m not in matieres:
            matieres[m] = []
        matieres[m].append({
            "id":          n.id,
            "note":        float(n.note),
            "coefficient": float(n.coefficient),
            "type_examen": n.type_examen,
            "semestre":    n.semestre,
            "enseignant":  f"{n.enseignant.prenom} {n.enseignant.nom}",
            "date_saisie": n.date_saisie.strftime("%Y-%m-%d"),
        })

    # Moyenne par matière
    resume = []
    for matiere, liste in matieres.items():
        total_p = sum(n["note"] * n["coefficient"] for n in liste)
        total_c = sum(n["coefficient"] for n in liste)
        resume.append({
            "matiere": matiere,
            "moyenne": round(total_p / total_c, 2) if total_c > 0 else 0,
            "notes":   liste,
        })

    resume.sort(key=lambda x: x["matiere"])

    # Moyenne générale
    total_p = sum(r["moyenne"] * sum(n["coefficient"] for n in r["notes"]) for r in resume)
    total_c = sum(sum(n["coefficient"] for n in r["notes"]) for r in resume)
    moyenne_generale = round(total_p / total_c, 2) if total_c > 0 else 0

    return _json_response({
        "etudiant_id":      etudiant.id,
        "etudiant_nom":     f"{etudiant.prenom} {etudiant.nom}",
        "moyenne_generale": moyenne_generale,
        "matieres":         resume,
    }, 200)

@csrf_exempt
def absences_etudiant(request):
    """
    GET /api/absences_etudiant/?etudiant_id=1
    """
    if request.method == "OPTIONS":
        return _json_response({})

    if request.method != "GET":
        return _json_response({"message": "Méthode non autorisée"}, 405)

    etudiant_id = request.GET.get("etudiant_id")
    if not etudiant_id:
        return _json_response({"message": "Paramètre etudiant_id manquant"}, 400)

    try:
        etudiant = Etudiant.objects.get(id=etudiant_id)
    except Etudiant.DoesNotExist:
        return _json_response({"message": "Étudiant introuvable"}, 404)
    except Exception as e:
        return _json_response({"message": f"Erreur serveur : {str(e)}"}, 500)

    absences_qs = Absence.objects.filter(etudiant=etudiant).order_by("-date")

    absences_list = [{
        "id":           a.id,
        "date":         a.date.strftime("%Y-%m-%d"),
        "matiere":      a.matiere,
        "type_absence": a.type_absence,
    } for a in absences_qs]

    return _json_response({
        "etudiant_id":   etudiant.id,
        "etudiant_nom":  f"{etudiant.prenom} {etudiant.nom}",
        "absences":      absences_list,
        "total_absences": absences_qs.filter(type_absence="absence").count(),
        "total_retards":  absences_qs.filter(type_absence="retard").count(),
        "total_presents": absences_qs.filter(type_absence="present").count(),
    }, 200)