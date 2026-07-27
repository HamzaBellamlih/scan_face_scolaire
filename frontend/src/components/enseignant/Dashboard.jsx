import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./css/enseignant.css";

export default function DashboardEnseignant() {
  const [darkMode,   setDarkMode]   = useState(true);
  const [enseignant, setEnseignant] = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const loadData = async () => {
      const enseignantId = localStorage.getItem("enseignant_id");
      if (!enseignantId || enseignantId === "null") {
        navigate("/login/enseignant");
        return;
      }
      try {
        const res  = await fetch(`http://127.0.0.1:8008/api/enseignant/${enseignantId}/`);
        const text = await res.text();
        let data;
        try { data = JSON.parse(text); }
        catch { setError(`Réponse invalide : ${text.slice(0, 100)}`); return; }
        if (!res.ok) { setError(data.message || `Erreur ${res.status}`); return; }
        setEnseignant(data);
      } catch (err) {
        setError(`Erreur réseau : ${err.message}`);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [navigate]);

  const handleLogout = () => { localStorage.clear(); navigate("/"); };

  const s = enseignant?.stats || {};
  const moyennes = s.moyennes_par_classe || [];

  const moyenneColor = (val) => {
    if (val === null || val === undefined) return "#94a3b8";
    return val >= 10 ? "#10b981" : "#ef4444";
  };

  if (loading)
    return (
      <div className={`ens-page ${darkMode ? "dark" : "light"}`}>
        <div className="ens-loading"><div className="ens-spinner" />Chargement...</div>
      </div>
    );

  if (error)
    return (
      <div className={`ens-page ${darkMode ? "dark" : "light"}`}>
        <div className="ens-wrapper">
          <div style={{ textAlign:"center", padding:"40px" }}>
            <p style={{ fontSize:"18px", marginBottom:"12px", color:"#ef4444" }}>⚠️ {error}</p>
            <div style={{ background:"rgba(0,0,0,0.2)", borderRadius:"12px", padding:"16px",
              marginBottom:"20px", fontSize:"13px", color:"#94a3b8", textAlign:"left" }}>
              <p><strong>enseignant_id :</strong> {localStorage.getItem("enseignant_id") ?? "—"}</p>
              <p><strong>nom :</strong> {localStorage.getItem("enseignant_nom") ?? "—"}</p>
              <p><strong>prenom :</strong> {localStorage.getItem("enseignant_prenom") ?? "—"}</p>
              <p><strong>matiere :</strong> {localStorage.getItem("enseignant_matiere") ?? "—"}</p>
            </div>
            <button onClick={handleLogout} style={{ padding:"12px 28px", borderRadius:"12px",
              background:"linear-gradient(135deg,#6366f1,#8b5cf6)",
              border:"none", color:"#fff", cursor:"pointer", fontSize:"14px" }}>
              Se reconnecter
            </button>
          </div>
        </div>
      </div>
    );

  return (
    <div className={`ens-page ${darkMode ? "dark" : "light"}`}>
      <div className="ens-wrapper">

        {/* ── HEADER ── */}
        <div className="ens-header">
          <div className="ens-header-icon">👨‍🏫</div>
          <div className="ens-header-info">
            <h1 className="ens-header-title">
              Bienvenue, {enseignant?.prenom} {enseignant?.nom}
            </h1>
            <p className="ens-header-sub">
              {enseignant?.matiere} • {enseignant?.email}
            </p>
          </div>
          <div style={{ display:"flex", gap:"8px" }}>
            <button className="ens-toggle" onClick={() => setDarkMode(!darkMode)}>
              {darkMode ? "☀️" : "🌙"}
            </button>
            <button className="ens-toggle" onClick={handleLogout} title="Déconnexion">🚪</button>
          </div>
        </div>

        {/* ── STATS RAPIDES ── */}
        <div className="ens-stats">
          <div className="ens-stat-card">
            <div className="ens-stat-icon">📋</div>
            <div className="ens-stat-content">
              <div className="ens-stat-value">{s.presences_saisies ?? 0}</div>
              <div className="ens-stat-label">Présences saisies</div>
            </div>
          </div>
          <div className="ens-stat-card">
            <div className="ens-stat-icon">👥</div>
            <div className="ens-stat-content">
              <div className="ens-stat-value">{s.etudiants_du_niveau ?? 0}</div>
              <div className="ens-stat-label">Étudiants du niveau suivi</div>
            </div>
          </div>
        </div>

        {/* ── MOYENNES PAR CLASSE ── */}
        {moyennes.length > 0 && (
          <>
            <p className="ens-section-label">📊 Moyennes par classe — {enseignant?.matiere}</p>
            <div className="ens-card">
              <div className="ens-table-container">
                <table className="ens-table">
                  <thead>
                    <tr>
                      <th>Classe</th>
                      <th>Étudiants</th>
                      <th>Semestre 1</th>
                      <th>Semestre 2</th>
                      <th>Moyenne générale</th>
                    </tr>
                  </thead>
                  <tbody>
                    {moyennes.map((m) => (
                      <tr key={m.classe}>
                        <td><strong>{m.classe}</strong></td>
                        <td>{m.nb_etudiants}</td>
                        <td>
                          <span style={{ color: moyenneColor(m.moyenne_s1), fontWeight: 700 }}>
                            {m.moyenne_s1 ?? "—"}
                          </span>
                        </td>
                        <td>
                          <span style={{ color: moyenneColor(m.moyenne_s2), fontWeight: 700 }}>
                            {m.moyenne_s2 ?? "—"}
                          </span>
                        </td>
                        <td>
                          <span style={{
                            color: moyenneColor(m.moyenne_generale),
                            fontWeight: 700,
                            fontSize: "16px"
                          }}>
                            {m.moyenne_generale ?? "—"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* ── ACTIONS ── */}
        <div className="ens-actions">
          <button className="ens-action-btn" onClick={() => navigate("/enseignant/notes")}>
            <span className="ens-action-icon">📝</span>
            <span className="ens-action-text">Gestion des Notes</span>
          </button>
          <button className="ens-action-btn" onClick={() => navigate("/enseignant/presences")}>
            <span className="ens-action-icon">✅</span>
            <span className="ens-action-text">Présences</span>
          </button>
          <button className="ens-action-btn" onClick={() => navigate("/enseignant/classes")}>
            <span className="ens-action-icon">🏫</span>
            <span className="ens-action-text">Mes Classes</span>
          </button>
        </div>
      </div>
    </div>
  );
}