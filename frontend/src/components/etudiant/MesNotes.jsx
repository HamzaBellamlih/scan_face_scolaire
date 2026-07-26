import React, { useState, useEffect, useCallback } from "react";
import "./css/etudiant.css";

export default function MesNotes() {
  const [darkMode,  setDarkMode]  = useState(true);
  const [data,      setData]      = useState(null);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState("");
  const [semestre,  setSemestre]  = useState(""); // "" | "1" | "2"
  const [expanded,  setExpanded]  = useState({});  // matiere -> bool

  const etudiantId = localStorage.getItem("etudiant_id");

  const fetchNotes = useCallback(async (sem) => {
    setLoading(true);
    setError("");
    try {
      let url = `http://127.0.0.1:8008/api/notes_etudiant/?etudiant_id=${etudiantId}`;
      if (sem) url += `&semestre=${sem}`;

      const res  = await fetch(url);
      const text = await res.text();
      let json;
      try { json = JSON.parse(text); }
      catch { setError(`Réponse invalide : ${text.slice(0, 100)}`); return; }
      if (!res.ok) { setError(json.message || `Erreur ${res.status}`); return; }
      setData(json);
      // Ouvrir toutes les matières par défaut
      const init = {};
      json.matieres.forEach((m) => { init[m.matiere] = true; });
      setExpanded(init);
    } catch (err) {
      setError(`Erreur réseau : ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [etudiantId]);

  useEffect(() => {
    if (!etudiantId) return;
    fetchNotes(semestre);
  }, [semestre, etudiantId, fetchNotes]);

  const toggle = (matiere) =>
    setExpanded((prev) => ({ ...prev, [matiere]: !prev[matiere] }));

  const noteColor = (note) => note >= 10 ? "#10b981" : "#ef4444";

  const badgeStyle = (note) => ({
    background: note >= 10 ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)",
    color:      note >= 10 ? "#10b981" : "#ef4444",
    padding:    "3px 10px",
    borderRadius: "20px",
    fontWeight: 700,
    fontSize:   "13px",
  });

  const typeLabel = (t) => ({
    devoir: "📋 Devoir", examen: "📄 Examen",
    tp: "🔬 TP", rattrapage: "🔄 Rattrapage",
  }[t] || t);

  if (loading)
    return (
      <div className={`etud-page ${darkMode ? "dark" : "light"}`}>
        <div className="etud-loading"><div className="etud-spinner" />Chargement...</div>
      </div>
    );

  return (
    <div className={`etud-page ${darkMode ? "dark" : "light"}`}>
      <div className="etud-wrapper">

        {/* ── HEADER ── */}
        <div className="etud-header">
          <div className="etud-header-icon">📝</div>
          <div className="etud-header-info">
            <h1 className="etud-header-title">Mes Notes</h1>
            <p className="etud-header-sub">
              Moyenne générale :
              <strong style={{ color: noteColor(data?.moyenne_generale), marginLeft: 6 }}>
                {data?.moyenne_generale ?? "—"}/20
              </strong>
            </p>
          </div>
          <button className="etud-toggle" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>

        {/* ── FILTRE SEMESTRE ── */}
        <div style={{ display:"flex", gap:"8px", marginBottom:"16px" }}>
          {[
            { val:"",  label:"Tous" },
            { val:"1", label:"Semestre 1" },
            { val:"2", label:"Semestre 2" },
          ].map((f) => (
            <button
              key={f.val}
              onClick={() => setSemestre(f.val)}
              style={{
                padding:"7px 18px", borderRadius:"20px", cursor:"pointer",
                border: semestre === f.val ? "none" : "1px solid rgba(255,255,255,0.15)",
                background: semestre === f.val
                  ? "linear-gradient(135deg,#10b981,#059669)" : "transparent",
                color: semestre === f.val ? "#fff" : "inherit",
                fontWeight: 600, fontSize:"13px",
              }}
            >
              {f.label}
            </button>
          ))}
        </div>

        {error && (
          <div style={{ padding:"12px", borderRadius:"10px",
            background:"#fef2f2", color:"#ef4444", marginBottom:"16px" }}>
            ⚠️ {error}
          </div>
        )}

        {/* ── MATIÈRES ── */}
        {!data || data.matieres.length === 0 ? (
          <div className="etud-card" style={{ textAlign:"center", padding:"40px", opacity:0.5 }}>
            Aucune note disponible
          </div>
        ) : (
          data.matieres.map((mat) => (
            <div key={mat.matiere} className="etud-card" style={{ marginBottom:"16px" }}>

              {/* ── En-tête matière ── */}
              <div
                onClick={() => toggle(mat.matiere)}
                style={{ display:"flex", justifyContent:"space-between",
                  alignItems:"center", cursor:"pointer", padding:"4px 0" }}
              >
                <div style={{ display:"flex", alignItems:"center", gap:"12px" }}>
                  <span style={{ fontSize:"18px", fontWeight:700 }}>{mat.matiere}</span>
                  <span style={badgeStyle(mat.moyenne)}>
                    Moy: {mat.moyenne}/20
                  </span>
                </div>
                <span style={{ opacity:0.5, fontSize:"12px" }}>
                  {expanded[mat.matiere] ? "▲ Réduire" : "▼ Détails"}
                </span>
              </div>

              {/* ── Détail notes ── */}
              {expanded[mat.matiere] && (
                <div className="etud-table-container" style={{ marginTop:"12px" }}>
                  <table className="etud-table">
                    <thead>
                      <tr>
                        <th>Note</th>
                        <th>Coef.</th>
                        <th>Type</th>
                        <th>Semestre</th>
                        <th>Enseignant</th>
                        <th>Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mat.notes.map((n) => (
                        <tr key={n.id}>
                          <td>
                            <span style={badgeStyle(n.note)}>{n.note}/20</span>
                          </td>
                          <td>{n.coefficient}</td>
                          <td>{typeLabel(n.type_examen)}</td>
                          <td>S{n.semestre}</td>
                          <td>{n.enseignant}</td>
                          <td>{n.date_saisie}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))
        )}

        <button className="etud-back-btn" onClick={() => window.history.back()}>
          ← Retour
        </button>

      </div>
    </div>
  );
}