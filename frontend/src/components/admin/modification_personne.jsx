import React, { useEffect, useState, useRef } from "react";
import "./css/modification_personne.css";
import { useParams, useNavigate } from "react-router-dom";
import { authenticatedFetch, getToken } from "../../utils/auth";

export default function ModificationPersonne() {
  const { personne_id } = useParams();
  const personneId = Number(personne_id);
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [email, setEmail] = useState("");
  const [date_naissance, setDateNaissance] = useState("");
  const [lieu_naissance, setLieuNaissance] = useState("");
  const [telephone, setTelephone] = useState("");
  const [photo, setPhoto] = useState(null);

  const [cameraOn, setCameraOn] = useState(false);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [darkMode, setDarkMode] = useState(true);



  // 🔄 Charger personne
  useEffect(() => {
    if (!personneId) {
      setErr("ID personne invalide");
      setLoading(false);
      return;
    }

    (async () => {
      try {
        const personnes = await authenticatedFetch(
          "http://localhost:8000/api/lister_personnes/",
          { method: "GET" }
        );

        const e = personnes.find(e => Number(e.id) === personneId);
        if (!e) throw new Error("Personne introuvable");

        setNom(e.nom || "");
        setPrenom(e.prenom || "");
        setEmail(e.email || "");
        setDateNaissance(e.date_naissance || "");
        setLieuNaissance(e.lieu_naissance || "");
        setTelephone(e.telephone || "");
        setPhoto(e.photo || null);
      } catch (e) {
        setErr(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [personneId]);

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
        telephone,
        photo, // base64
      };

      const token = getToken();
      const res = await fetch(
        `http://localhost:8000/api/modifier_personne/${personneId}/`,
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
    <div className={`form-container page ${darkMode ? 'dark' : 'light'}`}>
      <div className="mode-toggle" style={{ position: 'absolute', top: '20px', right: '20px' }}>
        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={darkMode}
            onChange={() => setDarkMode(!darkMode)}
          />
          <span className="toggle-slider"></span>
        </label>
        <span style={{ marginLeft: '10px', color: darkMode ? '#fff' : '#333' }}>
          {darkMode ? '🌙 Dark' : '☀️ Light'}
        </span>
      </div>
      <h2 className="form-title">Modifier Personne</h2>

      <form className="form-card" onSubmit={handleModifier}>

        <div className="form-grid">
          <input
            className="form-input"
            value={nom}
            onChange={e => setNom(e.target.value)}
            placeholder="Nom"
          />

          <input
            className="form-input"
            value={prenom}
            onChange={e => setPrenom(e.target.value)}
            placeholder="Prénom"
          />

          <input
            className="form-input"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="Email"
          />

          <input
            className="form-input"
            type="date"
            value={date_naissance}
            onChange={e => setDateNaissance(e.target.value)}
          />

          <input
            className="form-input"
            value={lieu_naissance}
            onChange={e => setLieuNaissance(e.target.value)}
            placeholder="Lieu de naissance"
          />

          <input
            className="form-input"
            value={telephone}
            onChange={e => setTelephone(e.target.value)}
            placeholder="Téléphone"
          />
        </div>

        {/* ===== PHOTO ===== */}
        <h3 className="section-title">Photo de la personne</h3>

        {!cameraOn && (
          <button
            type="button"
            className="btn btn-camera"
            onClick={startCamera}
          >
            📷 Ouvrir la caméra
          </button>
        )}

        <div className="camera-container">
          <video ref={videoRef} autoPlay />
          <canvas ref={canvasRef} className="hidden-canvas" />
        </div>

        <button
          type="button"
          className="btn btn-capture"
          onClick={capturePhoto}
        >
          📸 Capturer
        </button>

        {photo && (
          <img
            src={photo}
            alt="capture"
            className="photo-preview"
          />
        )}

        {/* ===== ACTIONS ===== */}
        <div className="form-actions">
          <button type="submit" className="btn btn-primary">
            Modifier
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => navigate("/liste_personnes")}
          >
            Annuler
          </button>
        </div>
      </form>

      {err && <p className="form-error">{err}</p>}
    </div>
  );
}