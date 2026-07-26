"""
FaceRecognitionSimple — dlib direct (shape_predictor + resnet)
Intègre la technique du code Anis/Defend Intelligence :
  - dlib.get_frontal_face_detector()
  - shape_predictor_68_face_landmarks.dat
  - dlib_face_recognition_resnet_model_v1.dat
  - compute_face_descriptor avec num_jitters
  - np.linalg.norm pour la distance euclidienne
"""

import cv2
import numpy as np
import os
import json
import pickle


class FaceRecognitionSimple:

    # Chemins des modèles dlib préentraînés
    # Télécharger depuis : http://dlib.net/files/
    SHAPE_68   = "pretrained_model/shape_predictor_68_face_landmarks.dat"
    SHAPE_5    = "pretrained_model/shape_predictor_5_face_landmarks.dat"
    RESNET_DAT = "pretrained_model/dlib_face_recognition_resnet_model_v1.dat"

    def __init__(self, base_path="media"):
        self.base_path  = base_path
        self.database   = {"etudiants": {}, "enseignants": {}, "personnes": {}}
        self.trained    = False
        self._encodings = []   # liste de vecteurs 128D
        self._labels    = []   # IDs correspondants

        cascade_path      = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        # ── Essayer dlib direct (méthode Anis) ───────────────────
        self._use_dlib_direct = False
        self._use_dlib        = False

        try:
            import dlib
            if (os.path.exists(self.SHAPE_68) and
                os.path.exists(self.RESNET_DAT)):

                self._pose_predictor = dlib.shape_predictor(self.SHAPE_68)
                self._face_encoder   = dlib.face_recognition_model_v1(self.RESNET_DAT)
                self._face_detector  = dlib.get_frontal_face_detector()
                self._use_dlib_direct = True
                self._use_dlib        = True
                print("✅ Moteur : dlib direct (resnet + shape_predictor_68)")
                print(f"   shape_68   : {self.SHAPE_68}")
                print(f"   resnet_dat : {self.RESNET_DAT}")
            else:
                raise FileNotFoundError("Modèles .dat manquants")

        except Exception as e:
            print(f"⚠️  dlib direct indisponible : {e}")

            # Fallback 1 — face_recognition (wrapper dlib)
            try:
                import face_recognition as fr  # noqa
                self._use_dlib = True
                print("✅ Moteur : face_recognition (dlib wrapper)")
            except ImportError:
                # Fallback 2 — OpenCV LBPH
                self._use_dlib  = False
                self.recognizer = cv2.face.LBPHFaceRecognizer_create()
                print("⚠️  Moteur : OpenCV LBPH (précision limitée)")

    # ── Encodage dlib direct (méthode Anis) ─────────────────────
    def _encode_face_dlib(self, image_rgb, num_jitters=1):
        """
        Encode un visage avec dlib resnet — retourne liste de vecteurs 128D.
        Même logique que le code Anis : face_detector + shape_predictor + compute_face_descriptor
        """
        import dlib
        face_locations = self._face_detector(image_rgb, 1)
        encodings = []
        for face_loc in face_locations:
            shape    = self._pose_predictor(image_rgb, face_loc)
            encoding = np.array(
                self._face_encoder.compute_face_descriptor(image_rgb, shape, num_jitters=num_jitters)
            )
            encodings.append(encoding)
        return encodings

    # ── Détection OpenCV (fallback LBPH) ────────────────────────
    def detect_face(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return None, None, None
        h, w = img.shape[:2]
        if w < 200 or h < 200:
            scale = 400 / min(w, h)
            img   = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
        gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray  = cv2.fastNlMeansDenoising(gray, h=7, templateWindowSize=7, searchWindowSize=21)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray  = clahe.apply(gray)
        for params in [
            {"scaleFactor": 1.1,  "minNeighbors": 5, "minSize": (30, 30)},
            {"scaleFactor": 1.05, "minNeighbors": 3, "minSize": (20, 20)},
            {"scaleFactor": 1.03, "minNeighbors": 2, "minSize": (15, 15)},
            {"scaleFactor": 1.01, "minNeighbors": 1, "minSize": (10, 10)},
        ]:
            faces = self.face_cascade.detectMultiScale(gray, **params)
            if len(faces) > 0:
                x, y, w2, h2 = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
                margin = int(min(w2, h2) * 0.1)
                y1 = max(0, y-margin); y2 = min(gray.shape[0], y+h2+margin)
                x1 = max(0, x-margin); x2 = min(gray.shape[1], x+w2+margin)
                return cv2.resize(gray[y1:y2, x1:x2], (200, 200), interpolation=cv2.INTER_CUBIC), img, (x, y, w2, h2)
        return None, None, None

    def _parse_filename(self, filename):
        name_no_ext = os.path.splitext(filename)[0]
        parts = name_no_ext.split('_')
        if len(parts) < 3:
            return None, None
        nom    = parts[0].strip()
        prenom = parts[1].strip()
        if not nom or not prenom:
            return None, None
        return nom, prenom

    # ── Chargement ──────────────────────────────────────────────
    def _load_category(self, category, faces, labels, current_id):
        folder = os.path.join(self.base_path, category)
        if not os.path.exists(folder):
            return current_id

        image_files = sorted([
            f for f in os.listdir(folder)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
        if not image_files:
            return current_id

        print(f"   📄 {len(image_files)} fichier(s)")

        person_groups = {}
        for img_file in image_files:
            nom, prenom = self._parse_filename(img_file)
            if nom is None:
                continue
            person_groups.setdefault(f"{nom}_{prenom}", []).append(img_file)

        print(f"   👥 {len(person_groups)} personne(s)")

        for key, images in sorted(person_groups.items()):
            nom, prenom = key.split('_', 1)
            print(f"\n   🔄 {prenom} {nom} ({len(images)} image(s))")

            temp_encodings = []
            temp_faces     = []
            first_photo    = ""

            for img_file in images:
                img_path = os.path.join(folder, img_file)

                if self._use_dlib_direct:
                    # ── Méthode Anis — dlib direct ────────────────
                    try:
                        import PIL.Image
                        img_pil = PIL.Image.open(img_path)
                        img_rgb = np.array(img_pil)
                        if img_rgb.ndim == 2:
                            img_rgb = cv2.cvtColor(img_rgb, cv2.COLOR_GRAY2RGB)
                        elif img_rgb.shape[2] == 4:
                            img_rgb = cv2.cvtColor(img_rgb, cv2.COLOR_RGBA2RGB)

                        # num_jitters=1 à l'entraînement (rapide)
                        encs = self._encode_face_dlib(img_rgb, num_jitters=1)
                        if encs:
                            temp_encodings.extend(encs)
                            if not first_photo:
                                first_photo = f"{category}/{img_file}"
                            print(f"      ✅ {img_file} ({len(encs)} enc.)")
                        else:
                            print(f"      ❌ Aucun visage (dlib) : {img_file}")
                    except Exception as e:
                        print(f"      ❌ {e}")

                elif self._use_dlib:
                    # ── face_recognition wrapper ──────────────────
                    try:
                        import face_recognition as fr
                        img_rgb   = fr.load_image_file(img_path)
                        locations = fr.face_locations(img_rgb, model="hog")
                        if not locations:
                            locations = fr.face_locations(img_rgb, model="cnn")
                        if not locations:
                            print(f"      ❌ Aucun visage : {img_file}")
                            continue
                        enc = fr.face_encodings(img_rgb, locations)
                        if enc:
                            temp_encodings.append(enc[0])
                            if not first_photo:
                                first_photo = f"{category}/{img_file}"
                            print(f"      ✅ {img_file}")
                    except Exception as e:
                        print(f"      ❌ {e}")

                else:
                    # ── LBPH ─────────────────────────────────────
                    face, _, _ = self.detect_face(img_path)
                    if face is not None:
                        temp_faces.append(face)
                        if not first_photo:
                            first_photo = f"{category}/{img_file}"

            valid_data = temp_encodings if self._use_dlib else temp_faces
            if not valid_data:
                continue

            if self._use_dlib:
                for enc in temp_encodings:
                    self._encodings.append(enc)
                    self._labels.append(current_id)
            else:
                for face in temp_faces:
                    faces.append(face)
                    labels.append(current_id)

            entry = {
                "nom":            nom,
                "prenom":         prenom,
                "nom_complet":    f"{prenom} {nom}",
                "type": (
                    "etudiant"   if category == "etudiants"   else
                    "enseignant" if category == "enseignants" else
                    "personne"
                ),
                "email":          "",
                "telephone":      "",
                "photo":          first_photo,
                "image_file":     first_photo,
                "date_naissance": "",
                "lieu_naissance": "",
            }
            if category == "etudiants":
                entry.update({"niveau_etude": "", "niveau": "", "classe": "", "assurance": None})
            elif category == "enseignants":
                entry.update({"matiere": "", "assurance": None, "paiements": None, "date_creation": ""})

            self.database[category][current_id] = entry
            print(f"      ✅ ID={current_id} | '{first_photo}'")
            current_id += 1

        return current_id

    # ── Entraînement ────────────────────────────────────────────
    def train_from_folders(self):
        self.database   = {"etudiants": {}, "enseignants": {}, "personnes": {}}
        self._encodings = []
        self._labels    = []
        self.trained    = False
        faces, labels   = [], []

        moteur = "dlib direct (resnet)" if self._use_dlib_direct else \
                 "face_recognition"     if self._use_dlib         else \
                 "OpenCV LBPH"
        print(f"\n{'='*60}")
        print(f"🎓 ENTRAÎNEMENT — Moteur : {moteur}")
        print(f"{'='*60}")

        current_id = 0
        for cat in ("etudiants", "enseignants", "personnes"):
            print(f"\n📂 {cat.upper()}")
            current_id = self._load_category(cat, faces, labels, current_id)

        total = sum(len(v) for v in self.database.values())

        if self._use_dlib:
            if not self._encodings:
                print("❌ Aucun encodage")
                return False
            self.trained = True
            print(f"\n✅ {len(self._encodings)} encodage(s) — {total} personne(s)")
        else:
            if not faces:
                return False
            self.recognizer.train(faces, np.array(labels))
            self.trained = True
        return True

    # ── Reconnaissance ──────────────────────────────────────────
    def recognize(self, image_path, threshold=40):
        if not self.trained:
            return {"success": False, "identified": False, "error": "Modèle non entraîné"}
        if self._use_dlib:
            return self._recognize_dlib(image_path, threshold)
        else:
            return self._recognize_lbph(image_path, threshold)

    def _build_versions(self, img_bgr):
        """6 versions de l'image pour maximiser la détection."""
        versions = [("original", img_bgr)]
        gray    = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        clahe   = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        versions.append(("clahe",   cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)))
        versions.append(("bright1", cv2.convertScaleAbs(img_bgr, alpha=1.2, beta=20)))
        versions.append(("bright2", cv2.convertScaleAbs(img_bgr, alpha=1.4, beta=40)))
        versions.append(("flip",    cv2.flip(img_bgr, 1)))
        h, w = img_bgr.shape[:2]
        if w != 640 or h != 480:
            versions.append(("640x480", cv2.resize(img_bgr, (640, 480))))
        return versions

    def _recognize_dlib(self, image_path, threshold=40):
        try:
            img_bgr = cv2.imread(image_path)
            if img_bgr is None:
                return {"success": False, "identified": False, "error": f"Impossible de lire : {image_path}"}

            versions   = self._build_versions(img_bgr)
            best_dist  = float("inf")
            best_label = None

            for version_name, img_ver in versions:
                # BGR → RGB
                img_rgb = cv2.cvtColor(img_ver, cv2.COLOR_BGR2RGB)

                if self._use_dlib_direct:
                    # ── Méthode Anis — distance euclidienne directe ──
                    # vectors = np.linalg.norm(known_encodings - face_encoding, axis=1)
                    encs = self._encode_face_dlib(img_rgb, num_jitters=1)
                    if not encs:
                        continue
                    encoding  = encs[0]
                    known_arr = np.array(self._encodings)
                    vectors   = np.linalg.norm(known_arr - encoding, axis=1)
                    min_dist  = float(np.min(vectors))
                    min_idx   = int(np.argmin(vectors))

                else:
                    # ── face_recognition wrapper ─────────────────────
                    import face_recognition as fr
                    locations = fr.face_locations(img_rgb, model="hog")
                    if not locations:
                        locations = fr.face_locations(img_rgb, model="cnn")
                    if not locations:
                        continue
                    encodings = fr.face_encodings(img_rgb, locations)
                    if not encodings:
                        continue
                    encoding  = encodings[0]
                    distances = fr.face_distance(self._encodings, encoding)
                    min_dist  = float(np.min(distances))
                    min_idx   = int(np.argmin(distances))

                print(f"      🔍 '{version_name}' : dist={min_dist:.4f}")

                if min_dist < best_dist:
                    best_dist  = min_dist
                    best_label = self._labels[min_idx]

            if best_label is None:
                return {"success": False, "identified": False, "error": "Aucun visage détecté"}

            # ── Distance → Confiance ─────────────────────────────
            # Tolérance 0.6 (même que code Anis)
            TOLERANCE      = 0.6
            MAX_DIST       = 0.8
            DIST_THRESHOLD = 0.70

            confidence_percent = max(0.0, round((1 - best_dist / MAX_DIST) * 100, 1))

            print(f"\n   📊 dist={best_dist:.4f} | conf={confidence_percent}% | seuil={DIST_THRESHOLD}")

            person = None; person_type = None
            for cat in ("etudiants", "enseignants", "personnes"):
                if best_label in self.database[cat]:
                    person      = self.database[cat][best_label].copy()
                    person_type = person.get("type", cat[:-1])
                    break

            if person and best_dist < DIST_THRESHOLD:
                result = {
                    "success":        True,
                    "identified":     True,
                    "id":             int(best_label),
                    "type":           person_type,
                    "nom":            person.get("nom",            ""),
                    "prenom":         person.get("prenom",         ""),
                    "nom_complet":    person.get("nom_complet",    ""),
                    "email":          person.get("email",          ""),
                    "telephone":      person.get("telephone",      ""),
                    "photo":          person.get("photo",          ""),
                    "image_file":     person.get("image_file",     ""),
                    "date_naissance": person.get("date_naissance", ""),
                    "lieu_naissance": person.get("lieu_naissance", ""),
                    "confidence":     confidence_percent,
                    "distance":       round(best_dist, 4),
                    "assurance":      person.get("assurance",  None),
                    "paiements":      person.get("paiements",  None),
                    "date_creation":  person.get("date_creation", ""),
                }
                if person_type == "etudiant":
                    result["classe"]       = person.get("classe",       "")
                    result["niveau"]       = person.get("niveau",       "")
                    result["niveau_etude"] = person.get("niveau_etude", "")
                elif person_type == "enseignant":
                    result["matiere"] = person.get("matiere", "")

                print(f"   ✅ {result['nom_complet']} | {confidence_percent}%")
                return result

            return {
                "success":     True,
                "identified":  False,
                "confidence":  confidence_percent,
                "distance":    round(best_dist, 4),
                "error":       f"Confiance insuffisante : {confidence_percent}%",
                "nom":         person.get("nom",        "") if person else "",
                "prenom":      person.get("prenom",     "") if person else "",
                "nom_complet": person.get("nom_complet","") if person else "",
                "type":        person_type or "",
            }

        except Exception as e:
            import traceback; traceback.print_exc()
            return {"success": False, "identified": False, "error": str(e)}

    def _recognize_lbph(self, image_path, threshold=85):
        face, _, _ = self.detect_face(image_path)
        if face is None:
            return {"success": False, "identified": False, "error": "Aucun visage détecté"}
        label, confidence  = self.recognizer.predict(face)
        confidence_percent = max(0, round(100 - confidence, 1))
        lbph_threshold     = 100 - threshold
        person = None; person_type = None
        for cat in ("etudiants", "enseignants", "personnes"):
            if label in self.database[cat]:
                person      = self.database[cat][label].copy()
                person_type = person.get("type", cat[:-1])
                break
        if person and confidence < lbph_threshold:
            result = {
                "success":        True,
                "identified":     True,
                "id":             int(label),
                "type":           person_type,
                "nom":            person.get("nom",            ""),
                "prenom":         person.get("prenom",         ""),
                "nom_complet":    person.get("nom_complet",    ""),
                "email":          person.get("email",          ""),
                "telephone":      person.get("telephone",      ""),
                "photo":          person.get("photo",          ""),
                "image_file":     person.get("image_file",     ""),
                "date_naissance": person.get("date_naissance", ""),
                "lieu_naissance": person.get("lieu_naissance", ""),
                "confidence":     confidence_percent,
                "assurance":      person.get("assurance",  None),
                "paiements":      person.get("paiements",  None),
                "date_creation":  person.get("date_creation", ""),
            }
            if person_type == "etudiant":
                result["classe"]       = person.get("classe",       "")
                result["niveau"]       = person.get("niveau",       "")
                result["niveau_etude"] = person.get("niveau_etude", "")
            elif person_type == "enseignant":
                result["matiere"] = person.get("matiere", "")
            return result
        return {"success": True, "identified": False, "confidence": confidence_percent,
                "error": f"Confiance insuffisante : {confidence_percent}%"}

    # ── Sauvegarde ──────────────────────────────────────────────
    def save_model(self, filepath="trained_model.yml"):
        if not self.trained:
            return False
        if self._use_dlib:
            pkl_path = filepath.replace(".yml", "_dlib.pkl")
            with open(pkl_path, "wb") as f:
                pickle.dump({"encodings": self._encodings, "labels": self._labels}, f)
            print(f"💾 {pkl_path}")
        else:
            self.recognizer.save(filepath)
        db_path   = filepath.replace(".yml", "_db.json")
        db_serial = {cat: {str(k): v for k, v in entries.items()} for cat, entries in self.database.items()}
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db_serial, f, ensure_ascii=False, indent=2)
        print(f"💾 {db_path}")
        return True

    # ── Chargement modèle ────────────────────────────────────────
    def load_model(self, filepath="trained_model.yml"):
        db_path = filepath.replace(".yml", "_db.json")
        if self._use_dlib:
            pkl_path = filepath.replace(".yml", "_dlib.pkl")
            if not os.path.exists(pkl_path):
                return False
            with open(pkl_path, "rb") as f:
                data = pickle.load(f)
            self._encodings = data["encodings"]
            self._labels    = data["labels"]
            print(f"✅ {len(self._encodings)} encodage(s)")
        else:
            if not os.path.exists(filepath):
                return False
            self.recognizer.read(filepath)
        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.database = {cat: {int(k): v for k, v in entries.items()} for cat, entries in raw.items()}
            total = sum(len(v) for v in self.database.values())
            print(f"✅ {total} personne(s)")
        self.trained = True
        return True


if __name__ == "__main__":
    print("✅ FaceRecognitionSimple — dlib direct + resnet + shape_predictor_68")