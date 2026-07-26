#!/usr/bin/env python
"""
Diagnostic complet du système de reconnaissance faciale.
Vérifie :
  - Existence des dossiers media/
  - Présence des images
  - Format des noms de fichiers
  - Détection de visages dans les images
  - Installation des dépendances (dlib, opencv, etc.)
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path

# Couleurs pour le terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def log_ok(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def log_err(msg):
    print(f"{RED}❌ {msg}{RESET}")

def log_warn(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def log_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def header(title):
    print(f"\n{BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{RESET}\n")

# ════════════════════════════════════════════════════════════════
# 1. VÉRIFIER LES DÉPENDANCES
# ════════════════════════════════════════════════════════════════
header("1. DÉPENDANCES")

deps_ok = True

# numpy
try:
    import numpy
    log_ok(f"numpy {numpy.__version__}")
except ImportError:
    log_err("numpy manquant → pip install numpy")
    deps_ok = False

# opencv
try:
    import cv2
    log_ok(f"opencv {cv2.__version__}")
except ImportError:
    log_err("opencv manquant → pip install opencv-python")
    deps_ok = False

# face_recognition (dlib)
try:
    import face_recognition
    log_ok(f"face_recognition installé (dlib disponible)")
    use_dlib = True
except ImportError:
    log_warn("face_recognition non installé")
    log_warn("Installez-le : pip install face_recognition")
    use_dlib = False

if not deps_ok:
    print("\n❌ Dépendances manquantes — arrêt du diagnostic")
    sys.exit(1)

# ════════════════════════════════════════════════════════════════
# 2. CHEMINS ET DOSSIERS
# ════════════════════════════════════════════════════════════════
header("2. CHEMINS ET DOSSIERS")

# Déterminer la localisation
this_file = os.path.abspath(__file__)
ai_dir    = os.path.dirname(this_file)
backend_dir = os.path.dirname(ai_dir)
media_dir = os.path.join(ai_dir, "media")

log_info(f"Script : {this_file}")
log_info(f"AI DIR : {ai_dir}")
log_info(f"BACKEND DIR : {backend_dir}")
log_info(f"MEDIA DIR : {media_dir}")

if not os.path.exists(media_dir):
    log_err(f"Dossier media absent : {media_dir}")
    sys.exit(1)
else:
    log_ok(f"Dossier media trouvé")

# ════════════════════════════════════════════════════════════════
# 3. ANALYSE DES DOSSIERS
# ════════════════════════════════════════════════════════════════
header("3. CONTENU DES DOSSIERS")

categories = {
    "etudiants":   os.path.join(media_dir, "etudiants"),
    "enseignants": os.path.join(media_dir, "enseignants"),
    "personnes":   os.path.join(media_dir, "personnes"),
}

total_images = 0
file_details = {}

for cat_name, cat_path in categories.items():
    print(f"\n📂 {cat_name.upper()}")
    print(f"   Chemin : {cat_path}")
    
    if not os.path.exists(cat_path):
        log_warn(f"Dossier absent : {cat_path}")
        continue
    
    if not os.path.isdir(cat_path):
        log_err(f"Ce n'est pas un dossier : {cat_path}")
        continue
    
    # Lister les fichiers images
    files = sorted([
        f for f in os.listdir(cat_path)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif"))
    ])
    
    if not files:
        log_warn(f"Aucune image dans ce dossier")
        continue
    
    log_ok(f"{len(files)} image(s) trouvée(s)")
    
    file_details[cat_name] = []
    
    for filename in files[:10]:  # Limiter à 10 pour ne pas spammer
        filepath = os.path.join(cat_path, filename)
        size = os.path.getsize(filepath)
        size_kb = size / 1024
        
        # Vérifier le format du nom
        name_no_ext = os.path.splitext(filename)[0]
        parts = name_no_ext.split('_')
        
        is_valid = len(parts) >= 3
        
        # Essayer de charger l'image
        img = cv2.imread(filepath)
        img_ok = img is not None
        if img_ok:
            h, w = img.shape[:2]
            format_str = f"{w}x{h}"
        else:
            format_str = "ERREUR LECTURE"
        
        status = "✅" if (is_valid and img_ok) else "❌"
        
        print(f"   {status} {filename:45} | {format_str:10} | {size_kb:6.1f} KB")
        
        if not is_valid:
            print(f"      ⚠️  Format nom invalide : attendu Nom_Prenom_UUID.ext")
        if not img_ok:
            print(f"      ⚠️  Impossible de charger l'image")
        
        file_details[cat_name].append({
            "filename": filename,
            "valid_name": is_valid,
            "readable": img_ok,
            "size": size,
        })
        
        total_images += 1

log_info(f"Total images : {total_images}")

# ════════════════════════════════════════════════════════════════
# 4. DÉTECTION DE VISAGES
# ════════════════════════════════════════════════════════════════
if use_dlib:
    header("4. DÉTECTION DE VISAGES (DLIB)")
    
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    
    import face_recognition as fr
    
    total_faces = 0
    
    for cat_name, files_info in file_details.items():
        if not files_info:
            continue
        
        print(f"\n📂 {cat_name.upper()}")
        
        cat_path = categories[cat_name]
        detected_count = 0
        undetected = []
        
        for file_info in files_info:
            filename = file_info["filename"]
            filepath = os.path.join(cat_path, filename)
            
            if not file_info["readable"]:
                continue
            
            try:
                # Essayer dlib
                img_rgb = fr.load_image_file(filepath)
                
                # HOG (rapide)
                locations = fr.face_locations(img_rgb, model="hog")
                
                if not locations:
                    # CNN (plus précis mais lent)
                    locations = fr.face_locations(img_rgb, model="cnn")
                
                if locations:
                    detected_count += 1
                    total_faces += len(locations)
                    print(f"   ✅ {filename:45} | {len(locations)} visage(s)")
                else:
                    undetected.append(filename)
                    print(f"   ❌ {filename:45} | AUCUN VISAGE")
            
            except Exception as e:
                print(f"   ⚠️  {filename:45} | ERREUR : {str(e)[:40]}")
        
        log_info(f"{detected_count}/{len(files_info)} images avec visage(s)")
        
        if undetected and detected_count > 0:
            log_warn(f"Images sans visage détecté :")
            for f in undetected[:5]:
                print(f"        • {f}")

else:
    header("4. DÉTECTION DE VISAGES (CASCADE HAAR — FALLBACK)")
    
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    
    total_faces = 0
    
    for cat_name, files_info in file_details.items():
        if not files_info:
            continue
        
        print(f"\n📂 {cat_name.upper()}")
        
        cat_path = categories[cat_name]
        detected_count = 0
        
        for file_info in files_info:
            filename = file_info["filename"]
            filepath = os.path.join(cat_path, filename)
            
            if not file_info["readable"]:
                continue
            
            img = cv2.imread(filepath)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            if len(faces) > 0:
                detected_count += 1
                total_faces += len(faces)
                print(f"   ✅ {filename:45} | {len(faces)} visage(s)")
            else:
                print(f"   ❌ {filename:45} | AUCUN VISAGE")
        
        log_info(f"{detected_count}/{len(files_info)} images avec visage(s)")

# ════════════════════════════════════════════════════════════════
# 5. RÉSUMÉ
# ════════════════════════════════════════════════════════════════
header("5. RÉSUMÉ")

if total_images == 0:
    log_err("Aucune image trouvée dans les dossiers media/")
    print("\n   Actions suggérées :")
    print("   1. Créer les dossiers si nécessaire :")
    print(f"      mkdir -p {os.path.join(media_dir, 'etudiants')}")
    print(f"      mkdir -p {os.path.join(media_dir, 'enseignants')}")
    print(f"      mkdir -p {os.path.join(media_dir, 'personnes')}")
    print("   2. Ajouter des images au format Nom_Prenom_UUID.png")
    print("   3. Relancer ce diagnostic")
    sys.exit(1)

if total_faces == 0:
    log_err("Aucun visage détecté dans les images !")
    print("\n   Vérifications suggérées :")
    print("   • Images de qualité suffisante (min 200x200)")
    print("   • Visages bien éclairés et face à la caméra")
    print("   • Format image valide (PNG, JPG, etc.)")
    if not use_dlib:
        print("   • Installer dlib pour meilleure détection :")
        print("     pip install face_recognition")
    sys.exit(1)

log_ok(f"Diagnostic OK : {total_images} image(s), {total_faces} visage(s)")
print(f"\n   → Prêt pour l'entraînement !")
print(f"\n   Pour entraîner, appelez :")
print(f"   POST /api/face/train/")
