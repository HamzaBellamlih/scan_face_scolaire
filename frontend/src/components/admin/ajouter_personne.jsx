import React, { useState, useRef } from "react";
import axios from "axios";
import "./css/ajouter_personne.css";

export default function AjouterPersonne() {
  const [form, setForm] = useState({
    nom: "",
    prenom: "",
    date_naissance: "",
    lieu_naissance: "",
    telephone: "",
    email: "",
    photo: ""
  });

  const [photoPreview, setPhotoPreview] = useState("");
  const [cameraOn, setCameraOn] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [darkMode, setDarkMode] = useState(true);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // 🔹 Mise à jour des champs du formulaire
  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  // 🔹 Ouvrir la caméra
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setCameraOn(true);
    } catch (err) {
      console.error(err);
      alert("Impossible d'accéder à la caméra !");
    }
  };

  // 🔹 Capturer la photo
  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current || !videoRef.current.srcObject) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const base64 = canvas.toDataURL("image/png");
    setForm({ ...form, photo: base64 });
    setPhotoPreview(base64);

    // Arrêter la caméra
    video.srcObject.getTracks().forEach(track => track.stop());
    setCameraOn(false);
  };

  // 🔹 Soumettre le formulaire
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!form.photo) {
      setError("La photo est obligatoire");
      return;
    }

    try {
      await axios.post(
        "http://127.0.0.1:8008/api/ajouter_personne/",
        JSON.stringify(form),
        { headers: { "Content-Type": "application/json" } }
      );

      setForm({
        nom: "",
        prenom: "",
        date_naissance: "",
        lieu_naissance: "",
        telephone: "",
        email: "",
        photo: "",
      });
      setPhotoPreview("");
      setSuccess("Personne ajoutée avec succès !");
      window.history.back();

    } catch (err) {
      setError(err.response?.data?.message || err.response?.data?.error || err.message);
    }
  };

  const FIELD_LABELS = {
    nom:            "Nom",
    prenom:         "Prénom",
    date_naissance: "Date de naissance",
    lieu_naissance: "Lieu de naissance",
    telephone:      "Téléphone",
    email:          "Email",
  };

  return (
    <div className={`ap-page ${darkMode ? "dark" : "light"}`}>
      <div className="ap-wrapper">

        {/* ── HEADER ── */}
        <div className="ap-header">
          <div className="ap-header-icon">👤</div>
          <div className="ap-header-info">
            <h1 className="ap-header-title">Ajouter une <span>Personne</span></h1>
            <p className="ap-header-sub">Remplissez le formulaire et prenez une photo</p>
          </div>
          <button
            type="button"
            className="ap-toggle"
            onClick={() => setDarkMode(!darkMode)}
          >
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>

        {/* ── CARD ── */}
        <div className="ap-card">
          <form onSubmit={handleSubmit}>

            {/* ── SECTION INFORMATIONS ── */}
            <div className="ap-section-title">
              <span className="ap-section-num">1</span>
              Informations personnelles
            </div>

            <div className="ap-grid">
              {Object.keys(FIELD_LABELS).map((field) => (
                <div
                  key={field}
                  className={`ap-field${field === "email" ? " ap-field--full" : ""}`}
                >
                  <label className="ap-label" htmlFor={field}>
                    {FIELD_LABELS[field]} <span className="ap-req">*</span>
                  </label>
                  <input
                    id={field}
                    className="ap-input"
                    type={field === "date_naissance" ? "date" : field === "email" ? "email" : "text"}
                    name={field}
                    value={form[field]}
                    onChange={handleChange}
                    required
                  />
                </div>
              ))}
            </div>

            <div className="ap-divider" />

            {/* ── SECTION PHOTO ── */}
            <div className="ap-section-title">
              <span className="ap-section-num">2</span>
              Photo d'identité
            </div>

            <div className="ap-camera-zone">
              {!cameraOn && !photoPreview && (
                <div className="ap-camera-idle">
                  <span className="ap-camera-icon">📷</span>
                  <p className="ap-camera-hint">Activez la caméra pour prendre une photo</p>
                  <button type="button" className="ap-btn ap-btn--camera" onClick={startCamera}>
                    📷&nbsp; Ouvrir la caméra
                  </button>
                </div>
              )}

              <video
                ref={videoRef}
                className="ap-video"
                autoPlay
                playsInline
                style={{ display: cameraOn ? "block" : "none" }}
              />

              {cameraOn && (
                <div className="ap-camera-actions">
                  <button type="button" className="ap-btn ap-btn--capture" onClick={capturePhoto}>
                    📸&nbsp; Capturer
                  </button>
                </div>
              )}

              <canvas ref={canvasRef} style={{ display: "none" }} />

              {photoPreview && !cameraOn && (
                <div className="ap-preview">
                  <img src={photoPreview} alt="Aperçu" className="ap-preview-img" />
                  <span className="ap-preview-badge">✅&nbsp; Photo capturée</span>
                </div>
              )}
            </div>

            {/* ── ALERTES ── */}
            {error   && <div className="ap-alert ap-alert--error">⚠️&nbsp; {error}</div>}
            {success && <div className="ap-alert ap-alert--success">✅&nbsp; {success}</div>}

            {/* ── ACTIONS ── */}
            <div className="ap-actions">
              <button type="submit" className="ap-btn ap-btn--primary">
                ✅&nbsp; Ajouter la personne
              </button>
              <button type="button" className="ap-btn ap-btn--back" onClick={() => window.history.back()}>
                ← Retour
              </button>
            </div>

          </form>
        </div>

      </div>
    </div>
  );
}