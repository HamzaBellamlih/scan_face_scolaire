import React, { useEffect, useState, useRef } from "react";
import "./css/modification_enseignant.css";
import { useParams, useNavigate } from "react-router-dom";
import { authenticatedFetch, getToken } from "../../utils/auth";

export default function ModificationEnseignant() {
  const { enseignant_id } = useParams();
  const enseignantId = Number(enseignant_id);
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [darkMode, setDarkMode] = useState(true);
  const [err, setErr] = useState("");

  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [email, setEmail] = useState("");
  const [date_naissance, setDateNaissance] = useState("");
  const [lieu_naissance, setLieuNaissance] = useState("");
  const [matiere, setMatiere] = useState("");
  const [telephone, setTelephone] = useState("");
  const [photo, setPhoto] = useState(null);

  const [cameraOn, setCameraOn] = useState(false);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // 🔄 Charger enseignant
  useEffect(() => {
    if (!enseignantId) {
      setErr("ID enseignant invalide");
      setLoading(false);
      return;
    }

    (async () => {
      try {
        const enseignants = await authenticatedFetch(
          "http://localhost:8000/api/lister_enseignants/",
          { method: "GET" }
        );

        const ens = enseignants.find(e => Number(e.id) === enseignantId);
        if (!ens) throw new Error("Enseignant introuvable");

        setNom(ens.nom || "");
        setPrenom(ens.prenom || "");
        setEmail(ens.email || "");
        setDateNaissance(ens.date_naissance || "");
        setLieuNaissance(ens.lieu_naissance || "");
        setMatiere(ens.matiere || "");
        setTelephone(ens.telephone || "");
        setPhoto(ens.photo || null);
      } catch (e) {
        setErr(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [enseignantId]);

  // 🎥 Activer webcam
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;
      videoRef.current.play();
      setCameraOn(true);
    } catch (err) {
      console.error(err);
      alert("Impossible d'accéder à la caméra !");
    }
  };

  // 📸 Capturer photo
  const capturePhoto = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    setPhoto(canvas.toDataURL("image/png")); // base64

    video.srcObject.getTracks().forEach(track => track.stop());
    setCameraOn(false);
  };

  // ✏️ Modifier
  const handleModifier = async (e) => {
    e.preventDefault();

    try {
      const payload = {
        nom,
        prenom,
        email,
        date_naissance,
        lieu_naissance,
        matiere,
        telephone,
        photo, // base64
      };

      const token = getToken();
      const res = await fetch(
        `http://localhost:8000/api/modifier_enseignant/${enseignantId}/`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        }
      );

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText);
      }

      const data = await res.json();
      alert("✅ " + data.message);
      window.history.back();
    } catch (err) {
      console.error(err);
      setErr("❌ Erreur modification : " + err.message);
    }
  };

  if (loading) return <p>Chargement...</p>;
  if (err) return <p style={{ color: "red" }}>{err}</p>;

  return (
    <div className={`me-page ${darkMode ? "dark" : "light"}`}>
      <div className="me-wrapper">

        {/* ── HEADER ── */}
        <div className="me-header">
          <div className="me-header-icon">👨‍🏫</div>
          <div className="me-header-info">
            <h1 className="me-header-title">Modifier un Enseignant</h1>
            <p className="me-header-sub">Modifiez les informations de l'enseignant</p>
          </div>
          <button type="button" className="me-toggle" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>

        {/* ── CARD ── */}
        <div className="me-card">
          <form onSubmit={handleModifier}>

            <div className="me-section-title">
              <span className="me-section-icon">📋</span>
              Informations personnelles
            </div>

            <div className="me-grid">
              <div className="me-field">
                <label className="me-label">Nom <span className="me-req">*</span></label>
                <input className="me-input" value={nom} onChange={e => setNom(e.target.value)} placeholder="Nom" />
              </div>

              <div className="me-field">
                <label className="me-label">Prénom <span className="me-req">*</span></label>
                <input className="me-input" value={prenom} onChange={e => setPrenom(e.target.value)} placeholder="Prénom" />
              </div>

              <div className="me-field">
                <label className="me-label">Date de naissance <span className="me-req">*</span></label>
                <input className="me-input" type="date" value={date_naissance} onChange={e => setDateNaissance(e.target.value)} />
              </div>

              <div className="me-field">
                <label className="me-label">Lieu de naissance <span className="me-req">*</span></label>
                <input className="me-input" value={lieu_naissance} onChange={e => setLieuNaissance(e.target.value)} placeholder="Lieu naissance" />
              </div>

              <div className="me-field">
                <label className="me-label">Téléphone <span className="me-req">*</span></label>
                <input className="me-input" value={telephone} onChange={e => setTelephone(e.target.value)} placeholder="Téléphone" />
              </div>

              <div className="me-field">
                <label className="me-label">Matière <span className="me-req">*</span></label>
                <input className="me-input" value={matiere} onChange={e => setMatiere(e.target.value)} placeholder="Matière" />
              </div>

              <div className="me-field me-field--full">
                <label className="me-label">Email <span className="me-req">*</span></label>
                <input className="me-input" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" />
              </div>
            </div>

            <div className="me-divider" />

            <div className="me-section-title">
              <span className="me-section-icon">📷</span>
              Photo d'enseignant
            </div>

            <div className="me-camera-zone">
              {!cameraOn && !photo && (
                <div className="me-camera-idle">
                  <span className="me-camera-icon">📷</span>
                  <p className="me-camera-hint">Activez la caméra pour prendre une photo</p>
                  <button type="button" className="me-btn me-btn--camera" onClick={startCamera}>
                    📷 Ouvrir la caméra
                  </button>
                </div>
              )}

              <video
                ref={videoRef}
                className="me-video"
                autoPlay
                style={{ display: cameraOn ? "block" : "none" }}
              />

              {cameraOn && (
                <div className="me-camera-actions">
                  <button type="button" className="me-btn me-btn--capture" onClick={capturePhoto}>
                    📸 Capturer
                  </button>
                </div>
              )}

              <canvas ref={canvasRef} style={{ display: "none" }} />

              {photo && !cameraOn && (
                <div className="me-preview">
                  <img src={photo} alt="capture" className="me-preview-img" />
                  <span className="me-preview-badge">✅ Photo sélectionnée</span>
                </div>
              )}
            </div>

            {err && <div className="me-alert me-alert--error">⚠️ {err}</div>}

            <div className="me-actions">
              <button type="submit" className="me-btn me-btn--primary">
                ✏️ Modifier
              </button>
              <button type="button" className="me-btn me-btn--secondary" onClick={() => navigate("/liste_enseignant")}>
                ✕ Annuler
              </button>
            </div>

          </form>
        </div>

      </div>
    </div>
  );
}