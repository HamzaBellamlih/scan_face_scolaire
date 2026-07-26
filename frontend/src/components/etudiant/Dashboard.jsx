import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./css/etudiant.css";

export default function DashboardEtudiant() {
  const [darkMode, setDarkMode] = useState(true);
  const [etudiant, setEtudiant] = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const loadData = async () => {
      const etudiantId = localStorage.getItem("etudiant_id");
      if (!etudiantId || etudiantId === "null") {
        navigate("/login_etudiant");
        return;
      }
      try {
        const res  = await fetch(`http://127.0.0.1:8008/api/etudiant/${etudiantId}/`);
        const text = await res.text();
        let data;
        try { data = JSON.parse(text); }
        catch { setError(`Réponse invalide : ${text.slice(0, 100)}`); return; }
        if (!res.ok) { setError(data.message || `Erreur ${res.status}`); return; }
        setEtudiant(data);
      } catch (err) {
        setError(`Erreur réseau : ${err.message}`);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [navigate]);

  const handleLogout = () => { localStorage.clear(); navigate("/"); };
  const s = etudiant?.stats || {};

  if (loading)
    return (
      <div className={`etud-page ${darkMode ? "dark" : "light"}`}>
        <div className="etud-loading"><div className="etud-spinner" />Chargement...</div>
      </div>
    );

  if (error)
    return (
      <div className={`etud-page ${darkMode ? "dark" : "light"}`}>
        <div className="etud-wrapper">
          <div style={{ textAlign:"center", padding:"40px" }}>
            <p style={{ fontSize:"18px", marginBottom:"12px", color:"#ef4444" }}>⚠️ {error}</p>
            <div style={{ background:"rgba(0,0,0,0.2)", borderRadius:"12px", padding:"16px",
              marginBottom:"20px", fontSize:"13px", color:"#94a3b8", textAlign:"left" }}>
              <p><strong>etudiant_id :</strong> {localStorage.getItem("etudiant_id") ?? "—"}</p>
              <p><strong>nom :</strong> {localStorage.getItem("etudiant_nom") ?? "—"}</p>
              <p><strong>prenom :</strong> {localStorage.getItem("etudiant_prenom") ?? "—"}</p>
            </div>
            <button onClick={handleLogout} style={{ padding:"12px 28px", borderRadius:"12px",
              background:"linear-gradient(135deg,#10b981,#059669)",
              border:"none", color:"#fff", cursor:"pointer", fontSize:"14px" }}>
              Se reconnecter
            </button>
          </div>
        </div>
      </div>
    );

  return (
    <div className={`etud-page ${darkMode ? "dark" : "light"}`}>
      <div className="etud-wrapper">

        {/* ── HEADER ── */}
        <div className="etud-header">
          <div className="etud-header-icon">🎓</div>
          <div className="etud-header-info">
            <h1 className="etud-header-title">
              Bienvenue, {etudiant?.prenom} {etudiant?.nom}
            </h1>
            <p className="etud-header-sub">
              {etudiant?.classe} • {etudiant?.niveau_etude} • {etudiant?.email}
            </p>
          </div>
          <div style={{ display:"flex", gap:"8px" }}>
            <button className="etud-toggle" onClick={() => setDarkMode(!darkMode)}>
              {darkMode ? "☀️" : "🌙"}
            </button>
            <button className="etud-toggle" onClick={handleLogout} title="Déconnexion">🚪</button>
          </div>
        </div>

        {/* ── STATS ── */}
        <div className="etud-stats">
          <div className="etud-stat-card">
            <div className="etud-stat-icon">❌</div>
            <div className="etud-stat-content">
              <div className="etud-stat-value" style={{ color: s.absences > 0 ? "#ef4444" : "#10b981" }}>
                {s.absences ?? 0}
              </div>
              <div className="etud-stat-label">Absences</div>
            </div>
          </div>

          <div className="etud-stat-card">
            <div className="etud-stat-icon">👥</div>
            <div className="etud-stat-content">
              <div className="etud-stat-value">{s.etudiants_en_classe ?? 0}</div>
              <div className="etud-stat-label">Étudiants dans ma classe</div>
            </div>
          </div>
        </div>

        {/* ── ACTIONS ── */}
        <div className="etud-actions">
          <button className="etud-action-btn" onClick={() => navigate("/etudiant/notes")}>
            <span className="etud-action-icon">📝</span>
            <span className="etud-action-text">Mes Notes</span>
          </button>
          <button className="etud-action-btn" onClick={() => navigate("/etudiant/absences")}>
            <span className="etud-action-icon">📅</span>
            <span className="etud-action-text">Mes Absences</span>
          </button>
        </div>
      </div>
    </div>
  );
}