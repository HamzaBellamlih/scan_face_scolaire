import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./css/login_enseignant.css";

export default function LoginEnseignant() {
  const [nom,      setNom]      = useState("");
  const [prenom,   setPrenom]   = useState("");
  const [matiere,  setMatiere]  = useState("");
  const [matieres, setMatieres] = useState([]);
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchMatieres = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8008/api/lister_enseignants/");
        if (res.ok) {
          const data = await res.json();
          const unique = [...new Set(data.map((e) => e.matiere))].sort();
          setMatieres(unique);
        }
      } catch (_) {
        setMatieres([
          "Mathématiques","Physique","Chimie","Informatique",
          "Français","Anglais","Histoire","Géographie",
          "Philosophie","SVT","Économie","Autre",
        ]);
      }
    };
    fetchMatieres();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!nom.trim() || !prenom.trim() || !matiere) {
      setError("Veuillez remplir tous les champs.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8008/api/login_enseignant/", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ nom: nom.trim(), prenom: prenom.trim(), matiere }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.message || "Identifiants incorrects."); return; }
      localStorage.setItem("enseignant_id",      data.id);
      localStorage.setItem("enseignant_nom",     data.nom);
      localStorage.setItem("enseignant_prenom",  data.prenom);
      localStorage.setItem("enseignant_matiere", data.matiere);
      navigate("/DashboardEnseignant");
    } catch (err) {
      setError("Erreur réseau. Vérifiez votre connexion.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-bg">
        {[...Array(12)].map((_, i) => (
          <div key={i} className={`login-orb login-orb--${i + 1}`} />
        ))}
      </div>

      <div className="login-container">

        <div className="login-brand">
          <div className="login-brand-icon">👨‍🏫</div>
          <h1 className="login-brand-title">Espace Enseignant</h1>
          <p className="login-brand-sub">Connectez-vous avec vos informations</p>
        </div>

        <div className="login-card">
          <form onSubmit={handleSubmit} className="login-form">

            {/* ── 3 champs côte à côte ── */}
            <div className="login-fields-row">

              <div className="login-field">
                <label className="login-label">Prénom</label>
                <div className="login-input-wrap">
                  <span className="login-input-icon">👤</span>
                  <input
                    type="text"
                    className="login-input"
                    value={prenom}
                    onChange={(e) => setPrenom(e.target.value)}
                    placeholder="Votre prénom"
                    autoFocus
                  />
                </div>
              </div>

              <div className="login-field">
                <label className="login-label">Nom</label>
                <div className="login-input-wrap">
                  <span className="login-input-icon">👤</span>
                  <input
                    type="text"
                    className="login-input"
                    value={nom}
                    onChange={(e) => setNom(e.target.value)}
                    placeholder="Votre nom de famille"
                  />
                </div>
              </div>

              <div className="login-field">
                <label className="login-label">Matière enseignée</label>
                <div className="login-input-wrap">
                  <span className="login-input-icon">📚</span>
                  <select
                    className="login-input login-select"
                    value={matiere}
                    onChange={(e) => setMatiere(e.target.value)}
                  >
                    <option value="">Sélectionner une matière</option>
                    {matieres.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>

            </div>

            {error && (
              <div className="login-error"><span>⚠️</span> {error}</div>
            )}

            <button type="submit" className="login-btn" disabled={loading}>
              {loading ? <span className="login-spinner" /> : "Se connecter →"}
            </button>

          </form>
        </div>

        <button type="button" className="login-back" onClick={() => navigate("/")}>
          ← Retour à l'accueil
        </button>
      </div>
    </div>
  );
}