# ai/augment_images.py
"""
Génère automatiquement des variations d'images pour
améliorer la précision du modèle de reconnaissance faciale.

Variations générées par image :
    1. Original redimensionné
    2. Luminosité +  (plus clair)
    3. Luminosité -  (plus sombre)
    4. Rotation +10°
    5. Rotation -10°
    6. Rotation +15°
    7. Rotation -15°
    8. Flip horizontal
    9. Zoom léger (crop 85%)
   10. Zoom fort  (crop 70%)
   11. Contraste fort
   12. Contraste faible
   13. Flou léger (simuler mouvement)
   14. Gamma clair
   15. Gamma sombre

Résultat : 1 image → 15 images = modèle beaucoup plus précis
"""

import cv2
import numpy as np
import os
import shutil

# ── Chemins ──────────────────────────────────────────────────
THIS_DIR  = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(THIS_DIR, "media")

# ── Marqueur pour identifier les images augmentées ───────────
# On ne re-augmente jamais une image déjà augmentée
AUGMENT_SUFFIXES = [
    "_bright", "_dark",
    "_rot10",  "_rot_10",
    "_rot15",  "_rot_15",
    "_flip",
    "_zoom85", "_zoom70",
    "_contrast_h", "_contrast_l",
    "_blur",
    "_gamma_h", "_gamma_l",
    "_original",
]


def is_augmented(filename):
    """
    Vérifie si un fichier est déjà une image augmentée.
    Retourne True si le fichier contient un suffixe d'augmentation.
    """
    name = os.path.splitext(filename)[0].lower()
    return any(suf in name for suf in AUGMENT_SUFFIXES)


def adjust_gamma(image, gamma):
    """
    Applique une correction gamma à une image.

    gamma > 1 → image plus claire
    gamma < 1 → image plus sombre

    Args:
        image (np.ndarray): Image BGR
        gamma (float)     : Valeur gamma (ex: 1.5 ou 0.7)

    Returns:
        np.ndarray: Image corrigée
    """
    inv_gamma = 1.0 / gamma
    table     = np.array([
        ((i / 255.0) ** inv_gamma) * 255
        for i in range(256)
    ]).astype("uint8")
    return cv2.LUT(image, table)


def rotate_image(image, angle):
    """
    Fait pivoter une image autour de son centre.
    Remplit les bords avec la couleur de bord (BORDER_REFLECT).

    Args:
        image (np.ndarray): Image BGR
        angle (float)     : Angle en degrés (positif = sens antihoraire)

    Returns:
        np.ndarray: Image pivotée
    """
    h, w = image.shape[:2]
    M    = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(
        image, M, (w, h),
        borderMode=cv2.BORDER_REFLECT
    )


def zoom_image(image, factor):
    """
    Zoom sur le centre de l'image (crop + resize).

    factor = 0.85 → garde 85% du centre
    factor = 0.70 → garde 70% du centre (zoom plus fort)

    Args:
        image  (np.ndarray): Image BGR
        factor (float)     : Facteur de crop (0 < factor < 1)

    Returns:
        np.ndarray: Image zoomée à la taille originale
    """
    h, w  = image.shape[:2]
    cy, cx = h // 2, w // 2

    crop_h = int(h * factor)
    crop_w = int(w * factor)

    y1 = cy - crop_h // 2
    y2 = cy + crop_h // 2
    x1 = cx - crop_w // 2
    x2 = cx + crop_w // 2

    # S'assurer qu'on reste dans les limites
    y1, y2 = max(0, y1), min(h, y2)
    x1, x2 = max(0, x1), min(w, x2)

    cropped = image[y1:y2, x1:x2]
    return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)


def generate_variations(image):
    """
    Génère toutes les variations d'une image.

    Args:
        image (np.ndarray): Image BGR originale

    Returns:
        list of tuple: [(nom_suffixe, image_variée), ...]
    """
    h, w   = image.shape[:2]
    result = []

    # 1. Original redimensionné à 400x400
    resized = cv2.resize(image, (400, 400))
    result.append(("_original", resized))

    # 2. Luminosité + (plus clair)
    bright = cv2.convertScaleAbs(image, alpha=1.3, beta=40)
    result.append(("_bright", bright))

    # 3. Luminosité - (plus sombre)
    dark = cv2.convertScaleAbs(image, alpha=0.7, beta=-30)
    result.append(("_dark", dark))

    # 4. Rotation +10°
    result.append(("_rot10", rotate_image(image,  10)))

    # 5. Rotation -10°
    result.append(("_rot_10", rotate_image(image, -10)))

    # 6. Rotation +15°
    result.append(("_rot15", rotate_image(image,  15)))

    # 7. Rotation -15°
    result.append(("_rot_15", rotate_image(image, -15)))

    # 8. Flip horizontal (miroir)
    result.append(("_flip", cv2.flip(image, 1)))

    # 9. Zoom léger (85% du centre)
    result.append(("_zoom85", zoom_image(image, 0.85)))

    # 10. Zoom fort (70% du centre)
    result.append(("_zoom70", zoom_image(image, 0.70)))

    # 11. Contraste élevé
    contrast_h = cv2.convertScaleAbs(image, alpha=1.5, beta=0)
    result.append(("_contrast_h", contrast_h))

    # 12. Contraste faible
    contrast_l = cv2.convertScaleAbs(image, alpha=0.6, beta=50)
    result.append(("_contrast_l", contrast_l))

    # 13. Flou léger (simuler un léger mouvement)
    blur = cv2.GaussianBlur(image, (3, 3), 0)
    result.append(("_blur", blur))

    # 14. Gamma clair (luminosité non linéaire)
    result.append(("_gamma_h", adjust_gamma(image, 1.5)))

    # 15. Gamma sombre
    result.append(("_gamma_l", adjust_gamma(image, 0.6)))

    return result


def augment_category(category):
    """
    Augmente toutes les images originales d'une catégorie.

    Args:
        category (str): "etudiants", "enseignants" ou "personnes"

    Returns:
        tuple: (nb_personnes, nb_images_créées)
    """
    folder = os.path.join(MEDIA_DIR, category)

    if not os.path.exists(folder):
        print(f"   ⚠️  Dossier manquant : {folder}")
        return 0, 0

    # Lister uniquement les images originales (pas les augmentées)
    originals = [
        f for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
        and not is_augmented(f)
    ]

    if not originals:
        print(f"   ⚠️  Aucune image originale dans : {folder}")
        return 0, 0

    print(f"   📄 {len(originals)} image(s) originale(s) trouvée(s)")

    total_created = 0
    persons_done  = set()

    for img_file in originals:
        img_path  = os.path.join(folder, img_file)
        base_name = os.path.splitext(img_file)[0]
        ext       = os.path.splitext(img_file)[1].lower()

        # Identifier la personne (Nom_Prenom depuis le nom de fichier)
        parts = base_name.split('_')
        if len(parts) >= 2:
            person_key = f"{parts[0]}_{parts[1]}"
            persons_done.add(person_key)

        print(f"\n   🔄 {img_file}")

        # Lire l'image
        img = cv2.imread(img_path)
        if img is None:
            print(f"      ❌ Impossible de lire l'image")
            continue

        h, w = img.shape[:2]
        print(f"      Taille : {w}x{h} pixels")

        # Générer toutes les variations
        variations = generate_variations(img)
        created    = 0

        for suffix, var_img in variations:
            # Nom du fichier augmenté
            out_name = f"{base_name}{suffix}.jpg"
            out_path = os.path.join(folder, out_name)

            # Ne pas écraser si déjà existant
            if os.path.exists(out_path):
                continue

            if cv2.imwrite(out_path, var_img):
                created += 1
            else:
                print(f"      ❌ Échec écriture : {out_name}")

        print(f"      ✅ {created} variation(s) créée(s)")
        total_created += created

    return len(persons_done), total_created


def clean_augmented(category):
    """
    Supprime toutes les images augmentées d'une catégorie.
    Garde uniquement les originaux.

    Utile pour repartir de zéro avant une nouvelle augmentation.

    Args:
        category (str): "etudiants", "enseignants" ou "personnes"
    """
    folder = os.path.join(MEDIA_DIR, category)
    if not os.path.exists(folder):
        return

    augmented = [
        f for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
        and is_augmented(f)
    ]

    for f in augmented:
        os.remove(os.path.join(folder, f))

    print(f"   🗑️  {len(augmented)} image(s) augmentée(s) supprimée(s)")


def main():
    print("=" * 60)
    print("🔧 AUGMENTATION DES IMAGES")
    print("=" * 60)
    print(f"   MEDIA_DIR : {MEDIA_DIR}\n")

    # Vérifier que le dossier media existe
    if not os.path.exists(MEDIA_DIR):
        print(f"❌ Dossier media introuvable : {MEDIA_DIR}")
        return

    total_persons = 0
    total_images  = 0

    for cat in ("etudiants", "enseignants", "personnes"):
        print(f"\n📂 {cat.upper()}")
        nb_p, nb_i = augment_category(cat)
        total_persons += nb_p
        total_images  += nb_i
        print(f"   → {nb_p} personne(s) | {nb_i} image(s) créée(s)")

    print("\n" + "=" * 60)
    print(f"✅ AUGMENTATION TERMINÉE")
    print(f"   Total personnes : {total_persons}")
    print(f"   Total nouvelles : {total_images}")
    print("=" * 60)
    print("\n🚀 Relancez maintenant :")
    print("   python train.py")


if __name__ == "__main__":
    import sys

    # Option --clean pour supprimer les augmentées
    if "--clean" in sys.argv:
        print("🗑️  Nettoyage des images augmentées...")
        for cat in ("etudiants", "enseignants", "personnes"):
            print(f"\n📂 {cat}")
            clean_augmented(cat)
        print("\n✅ Nettoyage terminé")
    else:
        main()