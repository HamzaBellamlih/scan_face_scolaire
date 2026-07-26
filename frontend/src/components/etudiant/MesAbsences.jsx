import React, { useState, useEffect } from "react";
import "./css/etudiant.css";

export default function MesAbsences() {
  const [darkMode,  setDarkMode]  = useState(true);
  const [absences,  setAbsences]  = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState("");
  const [filtre,    setFiltre]    = useState("tous");

  const etudiantId = localStorage.getItem("etudiant_id");

  useEffect(() => {
    const loadAbsences = async () => {
      if (!etudiantId) {
        setError("Session expirée. Veuillez vous reconnecter.");
        setLoading(false);
        return;
      }
      try {
        const res  = await fetch(
          `http://127.0.0.1:8008/api/absences_etudiant/?etudiant_id=${etudiantId}`
        );
        const text = await res.text();
        let data;
        try { data = JSON.parse(text); }
        catch { setError(`Réponse invalide : ${text.slice(0, 100)}`); return; }
        if (!res.ok) { setError(data.message || `Erreur ${res.status}`); return; }

        // La route retourne { absences: [...], ... }
        setAbsences(Array.isArray(data) ? data : (data.absences || []));
      } catch (err) {
        setError(`Erreur réseau : ${err.message}`);
      } finally {
        setLoading(false);
      }
    };
    loadAbsences();
  }, [etudiantId]);

  const totalAbsences = absences.filter((a) => a.type_absence === "absence").length;
  const totalRetards  = absences.filter((a) => a.type_absence === "retard").length;
  const totalPresents = absences.filter((a) => a.type_absence === "present").length;

  const absencesFiltrees = filtre === "tous"
    ? absences
    : absences.filter((a) => a.type_absence === filtre);

  const badgeStyle = (type) => {
    if (type === "absence") return { background:"rgba(239,68,68,0.15)",  color:"#ef4444", padding:"4px 12px", borderRadius:"20px", fontSize:"12px", fontWeight:700 };
    if (type === "retard")  return { background:"rgba(245,158,11,0.15)", color:"#f59e0b", padding:"4px 12px", borderRadius:"20px", fontSize:"12px", fontWeight:700 };
    return                         { background:"rgba(16,185,129,0.15)", color:"#10b981", padding:"4px 12px", borderRadius:"20px", fontSize:"12px", fontWeight:700 };
  };

  const labelType = (type) => {
    if (type === "absence") return "❌ Absence";
    if (type === "retard")  return "⏰ Retard";
    return "✅ Présent";
  };

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
          <div className="etud-header-icon">📅</div>
          <div className="etud-header-info">
            <h1 className="etud-header-title">Mes Absences</h1>
            <p className="etud-header-sub">
              {totalAbsences} absence{totalAbsences > 1 ? "s" : ""} •{" "}
              {totalRetards} retard{totalRetards > 1 ? "s" : ""} •{" "}
              {totalPresents} présence{totalPresents > 1 ? "s" : ""}
            </p>
          </div>
          <button className="etud-toggle" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>

        {error && (
          <div style={{ padding:"12px", borderRadius:"10px",
            background:"rgba(239,68,68,0.1)", color:"#ef4444", marginBottom:"16px" }}>
            ⚠️ {error}
          </div>
        )}

        <div className="etud-card">
          {/* ── Filtres ── */}
          <div style={{ display:"flex", gap:"8px", marginBottom:"16px", flexWrap:"wrap" }}>
            {[
              { val:"tous",    label:`Tous (${absences.length})` },
              { val:"absence", label:`❌ Absences (${totalAbsences})` },
              { val:"retard",  label:`⏰ Retards (${totalRetards})` },
              { val:"present", label:`✅ Présents (${totalPresents})` },
            ].map((f) => (
              <button
                key={f.val}
                type="button"
                onClick={() => setFiltre(f.val)}
                style={{
                  padding:"6px 14px", borderRadius:"20px", cursor:"pointer",
                  border: filtre === f.val ? "none" : "1px solid rgba(255,255,255,0.15)",
                  background: filtre === f.val
                    ? "linear-gradient(135deg,#10b981,#059669)" : "transparent",
                  color: filtre === f.val ? "#fff" : "inherit",
                  fontSize:"13px", fontWeight:600,
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* ── Tableau ── */}
          <div className="etud-table-container">
            <table className="etud-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Matière</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {absencesFiltrees.length === 0 ? (
                  <tr>
                    <td colSpan={3} style={{ textAlign:"center", padding:"32px", opacity:0.5 }}>
                      Aucun enregistrement
                    </td>
                  </tr>
                ) : (
                  absencesFiltrees.map((a) => (
                    <tr key={a.id}>
                      <td>{a.date}</td>
                      <td>{a.matiere}</td>
                      <td>
                        <span style={badgeStyle(a.type_absence)}>
                          {labelType(a.type_absence)}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <button className="etud-back-btn" onClick={() => window.history.back()}>
          ← Retour
        </button>

      </div>
    </div>
  );
}