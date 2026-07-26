"""
Script d'entraînement du modèle de reconnaissance faciale
Structure réelle :
  ai/media/etudiants/Nom_Prenom_UUID.png
  ai/media/enseignants/Nom_Prenom_UUID.png
  ai/media/personnes/Nom_Prenom_UUID.png
  ai/media/etudiants.json   (optionnel)
  ai/media/enseignants.json (optionnel)
"""

import os
import sys

# ── Chemins ──────────────────────────────────────────────────────
# Le script peut être lancé depuis backend/ai/ ou depuis un autre dossier.
# On détecte automatiquement le vrai répertoire contenant media/.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AI_DIR = BASE_DIR

candidates = [BASE_DIR, os.path.join(BASE_DIR, "ai")]
for candidate in candidates:
    if os.path.isdir(os.path.join(candidate, "media")):
        AI_DIR = candidate
        break

if AI_DIR not in sys.path:
    sys.path.insert(0, AI_DIR)

from face_service import face_service

print("=" * 60)
print("🎓 ENTRAÎNEMENT DU MODÈLE DE RECONNAISSANCE FACIALE")
print("=" * 60)

MEDIA_DIR       = os.path.join(AI_DIR, "media")
ETUDIANTS_DIR   = os.path.join(MEDIA_DIR, "etudiants")
ENSEIGNANTS_DIR = os.path.join(MEDIA_DIR, "enseignants")
PERSONNES_DIR   = os.path.join(MEDIA_DIR, "personnes")


def count_persons_and_images(folder):
    """
    Compte les personnes et images dans un dossier à plat.
    Format : Nom_Prenom_UUID.png  (les 2 premiers segments = Nom_Prenom)
    Plusieurs fichiers du même Nom_Prenom = une seule personne.
    ATTENTION : parts[0] = Nom, parts[1] = Prenom (ex: Bellamlih_Hamza_uuid.png)
    """
    if not os.path.exists(folder):
        return 0, 0, {}

    img_files = [
        f for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    persons = {}  # "Prenom_Nom" → [fichier1, fichier2, ...]
    for f in img_files:
        parts = os.path.splitext(f)[0].split("_")
        if len(parts) >= 2:
            key = f"{parts[0]}_{parts[1]}"
            persons.setdefault(key, []).append(f)

    total_images = sum(len(v) for v in persons.values())
    return len(persons), total_images, persons


# ── Vérification des dossiers ─────────────────────────────────────
print(f"\n1️⃣  Vérification des dossiers...")
print(f"    📁 AI_DIR   : {AI_DIR}")
print(f"    📁 Media    : {MEDIA_DIR}\n")

categories = [
    ("étudiants",   ETUDIANTS_DIR),
    ("enseignants", ENSEIGNANTS_DIR),
    ("personnes",   PERSONNES_DIR),
]

total_persons = 0
total_images  = 0

for label, path in categories:
    if not os.path.exists(path):
        print(f"    ❌ {label:12} : dossier introuvable — {path}")
        continue

    nb_p, nb_i, persons = count_persons_and_images(path)
    total_persons += nb_p
    total_images  += nb_i

    print(f"    ✅ {label:12} : {nb_p} personne(s) | {nb_i} image(s)")
    for key, files in sorted(persons.items())[:5]:
        print(f"         📄 {key}  ({len(files)} image(s))")
        for f in files[:2]:
            print(f"              → {f}")
    if len(persons) > 5:
        print(f"         ... et {len(persons)-5} autre(s)")

# ── Vérifications bloquantes ──────────────────────────────────────
print()
if total_persons == 0:
    print("❌ ERREUR : Aucune personne trouvée !")
    print("💡 Structure attendue :")
    print("   ai/media/etudiants/Nom_Prenom_UUID.png")
    print("   ex: Bellamlih_Hamza_17aa949c3d124b1e.png")
    sys.exit(1)

if total_images == 0:
    print("❌ ERREUR : Aucune image trouvée !")
    sys.exit(1)

print(f"📊 Total : {total_persons} personne(s) | {total_images} image(s)\n")

# ── Entraînement ──────────────────────────────────────────────────
print("2️⃣  Lancement de l'entraînement...")
print("⏳ Merci de patienter...\n")

try:
    success = face_service.train_model()
except Exception as e:
    print(f"\n❌ Erreur inattendue : {e}")
    import traceback; traceback.print_exc()
    success = False

# ── Résultats ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
if not success:
    print("❌ ÉCHEC DE L'ENTRAÎNEMENT")
    print("=" * 60)
    print("\n🔎 Causes possibles :")
    print("   1. Les images ne contiennent pas de visage détectable")
    print("      → Photo floue, de profil, trop sombre, ou visage masqué")
    print("   2. opencv-contrib-python non installé")
    print("      → pip install opencv-contrib-python")
    print("   3. Nom de fichier invalide (doit être Nom_Prenom_UUID.ext)")
    print("      → Format valide : Bellamlih_Hamza_abc123.png")
    sys.exit(1)

print("✅ ENTRAÎNEMENT RÉUSSI")
print("=" * 60)

stats = face_service.get_stats()
print(f"\n📊 Statistiques :")
print(f"   🎓 Étudiants    : {stats['etudiants']}")
print(f"   👨‍🏫 Enseignants : {stats['enseignants']}")
print(f"   👤 Personnes    : {stats['personnes']}")
print(f"   📦 Total        : {stats['total']}")

if stats["total"] == 0:
    print("\n⚠️  Modèle entraîné mais aucune personne en base !")
    print("   → Vérifiez que les fichiers sont nommés Nom_Prenom_UUID.png")
    sys.exit(1)

persons = face_service.get_all_persons()

# ── Étudiants ──
if persons["etudiants"]:
    print(f"\n🎓 ÉTUDIANTS ({len(persons['etudiants'])}) :")
    for p in persons["etudiants"]:
        print(f"   [{p['id']}] {p['prenom']} {p['nom']}")
        print(f"        📧 {p.get('email','—')}  📱 {p.get('telephone','—')}")
        print(f"        🏫 Classe : {p.get('classe','—')}  |  Niveau : {p.get('niveau_etude','—')}")
        a = p.get("assurance")
        if a:
            print(f"        🛡️  Assurance : payé={a['montant_paye']} DH"
                  f" / restant={a['montant_restant']} DH ({a['statut']})")
        else:
            print(f"        🛡️  Assurance : —")
        print()

# ── Enseignants ──
if persons["enseignants"]:
    print(f"👨‍🏫 ENSEIGNANTS ({len(persons['enseignants'])}) :")
    for p in persons["enseignants"]:
        print(f"   [{p['id']}] {p['prenom']} {p['nom']}")
        print(f"        📧 {p.get('email','—')}  📱 {p.get('telephone','—')}")
        print(f"        ✏️  Matière : {p.get('matiere','—')}")
        a = p.get("assurance")
        if a:
            print(f"        🛡️  Assurance : payé={a['montant_paye']} DH"
                  f" / restant={a['montant_restant']} DH ({a['statut']})")
        else:
            print(f"        🛡️  Assurance : —")
        pa = p.get("paiements")
        if pa:
            print(f"        💵 Salaire   : payé={pa['total_paye']} DH"
                  f" / restant={pa['salaire_restant']} DH"
                  f" ({pa['nb_paiements']} paiement(s))")
        else:
            print(f"        💵 Salaire   : —")
        print(f"        📅 Depuis    : {p.get('date_creation','—')}")
        print()

# ── Personnes ──
if persons["personnes"]:
    print(f"👤 PERSONNES ({len(persons['personnes'])}) :")
    for p in persons["personnes"]:
        print(f"   [{p['id']}] {p['prenom']} {p['nom']}")
        print(f"        📧 {p.get('email','—')}  📱 {p.get('telephone','—')}")
        print()

# ── Résumé enrichissement Django ──
e_ok = sum(1 for p in persons["etudiants"]   if p.get("email") or p.get("classe"))
n_ok = sum(1 for p in persons["enseignants"] if p.get("email") or p.get("matiere"))
p_ok = sum(1 for p in persons["personnes"]   if p.get("email"))
tot  = e_ok + n_ok + p_ok

print(f"{'✅' if tot > 0 else '⚠️ '} Enrichissement Django :")
print(f"   Étudiants   : {e_ok}/{stats['etudiants']}")
print(f"   Enseignants : {n_ok}/{stats['enseignants']}")
print(f"   Personnes   : {p_ok}/{stats['personnes']}")

if tot == 0:
    print("\n⚠️  Aucune donnée Django enrichie.")
    print("   → Les noms dans les fichiers doivent correspondre aux noms en base Django.")
    print("   → Exemple : fichier 'Ahmed_Benali_uuid.png'")
    print("     → Etudiant(prenom='Ahmed', nom='Benali') doit exister en DB")

print(f"\n📁 Modèle : {os.path.join(AI_DIR, 'trained_model.yml')}")
print("\n🚀 Le modèle est prêt !")
print("\n" + "=" * 60)