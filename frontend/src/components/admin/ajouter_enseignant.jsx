import React, { useState, useRef } from "react";
import axios from "axios";
import "./css/ajouter_enseignant.css";

export default function AjouterEnseignant() {

  const [form, setForm] = useState({
    nom: "", prenom: "", date_naissance: "",
    matiere: "", lieu_naissance: "", telephone: "", email: "", photo: "",
  });

  const [photoPreview, setPhotoPreview] = useState("");
  const [cameraOn,     setCameraOn]     = useState(false);
  const [error,        setError]        = useState("");
  const [success,      setSuccess]      = useState("");
  const [darkMode,     setDarkMode]     = useState(true);

  const videoRef  = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null); // ✅ garde la référence du stream

  // ── Handlers ──────────────────────────────────────────────
  const handleChange = (e) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  // ── Caméra ────────────────────────────────────────────────
  const startCamera = async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;           // ✅ on sauvegarde le stream
      videoRef.current.srcObject = stream;
      videoRef.current.play();
      setCameraOn(true);
    } catch (err) {
      setError("Impossible d'accéder à la caméra. Vérifiez les permissions.");
    }
  };

  // ✅ Fonction manquante ajoutée
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraOn(false);
  };

  const capturePhoto = () => {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !video.srcObject) return;

    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);

    const base64 = canvas.toDataURL("image/jpeg");
    setForm((prev) => ({ ...prev, photo: base64 }));
    setPhotoPreview(base64);
    stopCamera(); // ✅ utilise stopCamera au lieu de dupliquer le code
  };

  // ✅ Fonction manquante ajoutée
  const retakePhoto = () => {
    setPhotoPreview("");
    setForm((prev) => ({ ...prev, photo: "" }));
    startCamera();
  };

  // ── Submit ────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(""); setSuccess("");

    if (!form.photo) {
      setError("Veuillez capturer une photo avant de soumettre.");
      return;
    }

    try {
      await axios.post(
        "http://127.0.0.1:8008/api/ajouter_enseignant/",
        form,
        { headers: { "Content-Type": "application/json" } }
      );
      setSuccess("Enseignant ajouté avec succès !");
      setForm({
        nom: "", prenom: "", date_naissance: "", matiere: "",
        lieu_naissance: "", telephone: "", email: "", photo: "",
      });
      setPhotoPreview("");
      setTimeout(() => window.history.back(), 1500);
    } catch (err) {
      setError(err.response?.data?.message || err.message);
    }
  };

  // ── Render ────────────────────────────────────────────────
  return (
    <div className={`ens-page ${darkMode ? "dark" : "light"}`}>

      {/* ── Header ── */}
      <div className="ens-header">
        <div className="ens-header-icon">👨‍🏫</div>
        <div>
          <h2 className="ens-header-title">Ajouter un Enseignant</h2>
          <p className="ens-header-sub">
            Remplissez les informations pour enregistrer un nouvel enseignant
          </p>
        </div>

        {/* Toggle dark/light */}
        <button
          type="button"
          className="ens-toggle"
          onClick={() => setDarkMode((d) => !d)}
          title="Changer le thème"
        >
          {darkMode ? "☀️" : "🌙"}
        </button>
      </div>

      {/* ── Formulaire ── */}
      <form className="ens-card" onSubmit={handleSubmit}>

        {/* ─ Infos personnelles ─ */}
        <p className="ens-section-title">📋 Informations personnelles</p>

        <div className="ens-grid">
          {[
            { label: "Nom",               name: "nom",            type: "text",  placeholder: "Ex: Benali",         col: 1 },
            { label: "Prénom",            name: "prenom",         type: "text",  placeholder: "Ex: Mohammed",       col: 1 },
            { label: "Date de naissance", name: "date_naissance", type: "date",  placeholder: "",                   col: 1 },
            { label: "Lieu de naissance", name: "lieu_naissance", type: "text",  placeholder: "Ex: Alger",          col: 1 },
            { label: "Téléphone",         name: "telephone",      type: "tel",   placeholder: "Ex: 0550 123 456",   col: 1 },
            { label: "Email",             name: "email",          type: "email", placeholder: "Ex: prof@email.com", col: 1 },
            { label: "Matière enseignée", name: "matiere",        type: "text",  placeholder: "Ex: Mathématiques",  col: 2 },
          ].map(({ label, name, type, placeholder, col }) => (
            <div key={name} className={`ens-field ${col === 2 ? "ens-field--full" : ""}`}>
              <label className="ens-label">
                {label} <span className="ens-req">*</span>
              </label>
              <input
                className="ens-input"
                type={type}
                name={name}
                value={form[name]}
                placeholder={placeholder}
                onChange={handleChange}
                required
              />
            </div>
          ))}
        </div>

        <div className="ens-divider" />

        {/* ─ Photo ─ */}
        <p className="ens-section-title">📷 Photo de l'enseignant</p>

        <div className="ens-camera-zone">

          {/* Étape 1 – placeholder */}
          {!cameraOn && !photoPreview && (
            <div className="ens-camera-placeholder">
              <span className="ens-camera-emoji">📷</span>
              <p className="ens-camera-hint">Aucune photo capturée</p>
              <button type="button" className="ens-btn ens-btn--camera" onClick={startCamera}>
                📹 Ouvrir la caméra
              </button>
            </div>
          )}

          {/* Étape 2 – flux vidéo */}
          <video
            ref={videoRef}
            autoPlay
            className="ens-video"
            style={{ display: cameraOn ? "block" : "none" }}
          />

          {cameraOn && (
            <div className="ens-camera-actions">
              <button type="button" className="ens-btn ens-btn--capture" onClick={capturePhoto}>
                📸 Capturer
              </button>
              <button type="button" className="ens-btn ens-btn--ghost" onClick={stopCamera}>
                ✖ Annuler
              </button>
            </div>
          )}

          <canvas ref={canvasRef} style={{ display: "none" }} />

          {/* Étape 3 – aperçu */}
          {photoPreview && (
            <div className="ens-preview">
              <img src={photoPreview} alt="Aperçu enseignant" className="ens-preview-img" />
              <p className="ens-preview-label">✅ Photo capturée</p>
              <button type="button" className="ens-btn ens-btn--camera" onClick={retakePhoto}>
                🔄 Reprendre
              </button>
            </div>
          )}

        </div>

        {/* ─ Alertes ─ */}
        {error   && <div className="ens-alert ens-alert--error">⚠️ {error}</div>}
        {success && <div className="ens-alert ens-alert--success">✅ {success}</div>}

        <div className="ens-divider" />

        {/* ─ Actions ─ */}
        <div className="ens-actions">
          <button type="submit" className="ens-btn ens-btn--primary">
            ✅ Enregistrer l'enseignant
          </button>
          <button type="button" className="ens-btn ens-btn--back"
            onClick={() => window.history.back()}>
            ← Retour
          </button>
        </div>

      </form>
    </div>
  );
}