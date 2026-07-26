import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./css/login_etudiant.css";

export default function LoginEtudiant() {
  const [nom,         setNom]         = useState("");
  const [prenom,      setPrenom]      = useState("");
  const [classe,      setClasse]      = useState("");
  const [niveauEtude, setNiveauEtude] = useState("");
  const [classes,     setClasses]     = useState([]);
  const [error,       setError]       = useState("");
  const [loading,     setLoading]     = useState(false);
  const navigate = useNavigate();

  const niveaux = [
    { value: "bac",      label: "Baccalauréat" },
    { value: "licence",  label: "Licence" },
    { value: "master",   label: "Master" },
    { value: "doctorat", label: "Doctorat" },
  ];

  useEffect(() => {
    const fetchClasses = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8008/api/lister_etudiants/");
        if (res.ok) {
          const data = await res.json();
          const unique = [...new Set(data.map((e) => e.classe))].sort();
          setClasses(unique);
        }
      } catch (_) {}
    };
    fetchClasses();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!nom.trim() || !prenom.trim() || !classe.trim() || !niveauEtude) {
      setError("Veuillez remplir tous les champs.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8008/api/login_etudiant/", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({
          nom: nom.trim(), prenom: prenom.trim(),
          classe: classe.trim(), niveau_etude: niveauEtude,
        }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.message || "Identifiants incorrects."); return; }
      localStorage.setItem("etudiant_id",          data.id);
      localStorage.setItem("etudiant_nom",          data.nom);
      localStorage.setItem("etudiant_prenom",       data.prenom);
      localStorage.setItem("etudiant_classe",       data.classe);
      localStorage.setItem("etudiant_niveau_etude", data.niveau_etude);
      navigate("/DashboardEtudiant");
    } catch (err) {
      setError("Erreur réseau. Vérifiez votre connexion.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="letud-page">
      <div className="letud-bg">
        {[...Array(12)].map((_, i) => (
          <div key={i} className={`letud-orb letud-orb--${i + 1}`} />
        ))}
      </div>

      <div className="letud-container">

        <div className="letud-brand">
          <div className="letud-brand-icon">🎓</div>
          <h1 className="letud-brand-title">Espace Étudiant</h1>
          <p className="letud-brand-sub">Connectez-vous avec vos informations</p>
        </div>

        <div className="letud-card">
          <form onSubmit={handleSubmit} className="letud-form">

            {/* ── 4 champs côte à côte ── */}
            <div className="letud-fields-row">

              <div className="letud-field">
                <label className="letud-label">Prénom</label>
                <div className="letud-input-wrap">
                  <span className="letud-input-icon">👤</span>
                  <input
                    type="text"
                    className="letud-input"
                    value={prenom}
                    onChange={(e) => setPrenom(e.target.value)}
                    placeholder="Votre prénom"
                    autoFocus
                  />
                </div>
              </div>

              <div className="letud-field">
                <label className="letud-label">Nom</label>
                <div className="letud-input-wrap">
                  <span className="letud-input-icon">👤</span>
                  <input
                    type="text"
                    className="letud-input"
                    value={nom}
                    onChange={(e) => setNom(e.target.value)}
                    placeholder="Votre nom de famille"
                  />
                </div>
              </div>

              <div className="letud-field">
                <label className="letud-label">Classe</label>
                <div className="letud-input-wrap">
                  <span className="letud-input-icon">🏫</span>
                  {classes.length > 0 ? (
                    <select
                      className="letud-input letud-select"
                      value={classe}
                      onChange={(e) => setClasse(e.target.value)}
                    >
                      <option value="">Sélectionner une classe</option>
                      {classes.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      className="letud-input"
                      value={classe}
                      onChange={(e) => setClasse(e.target.value)}
                      placeholder="Ex: L2 Informatique"
                    />
                  )}
                </div>
              </div>

              <div className="letud-field">
                <label className="letud-label">Niveau d'étude</label>
                <div className="letud-input-wrap">
                  <span className="letud-input-icon">📚</span>
                  <select
                    className="letud-input letud-select"
                    value={niveauEtude}
                    onChange={(e) => setNiveauEtude(e.target.value)}
                  >
                    <option value="">Sélectionner un niveau</option>
                    {niveaux.map((n) => (
                      <option key={n.value} value={n.value}>{n.label}</option>
                    ))}
                  </select>
                </div>
              </div>

            </div>

            {error && (
              <div className="letud-error"><span>⚠️</span> {error}</div>
            )}

            <button type="submit" className="letud-btn" disabled={loading}>
              {loading ? <span className="letud-spinner" /> : "Se connecter →"}
            </button>

          </form>
        </div>

        <button type="button" className="letud-back" onClick={() => navigate("/")}>
          ← Retour à l'accueil
        </button>

      </div>
    </div>
  );
}