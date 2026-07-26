import React, { useState, useEffect } from "react";
import "./css/enseignant.css";

export default function MesClasses() {
  const [darkMode, setDarkMode] = useState(true);
  const [classes,  setClasses]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState("");

  useEffect(() => {
    const loadClasses = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8008/api/lister_etudiants/");
        if (!res.ok) throw new Error("Erreur chargement étudiants");
        const data = await res.json();

        // Grouper les étudiants par classe
        const groupes = {};
        data.forEach((etud) => {
          const cl = etud.classe;
          if (!groupes[cl]) {
            groupes[cl] = { nom: cl, niveau: etud.niveau_etude, etudiants: [] };
          }
          groupes[cl].etudiants.push(etud);
        });

        const liste = Object.values(groupes)
          .map((g) => ({
            nom:             g.nom,
            niveau:          g.niveau,
            nombreEtudiants: g.etudiants.length,
          }))
          .sort((a, b) => a.nom.localeCompare(b.nom));

        setClasses(liste);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    loadClasses();
  }, []);

  if (loading)
    return (
      <div className={`ens-page ${darkMode ? "dark" : "light"}`}>
        <div className="ens-loading">
          <div className="ens-spinner" />
          Chargement...
        </div>
      </div>
    );

  return (
    <div className={`ens-page ${darkMode ? "dark" : "light"}`}>
      <div className="ens-wrapper">

        {/* ── HEADER ── */}
        <div className="ens-header">
          <div className="ens-header-icon">📚</div>
          <div className="ens-header-info">
            <h1 className="ens-header-title">Mes Classes</h1>
            <p className="ens-header-sub">
              {classes.length} classe{classes.length > 1 ? "s" : ""} — {" "}
              {classes.reduce((acc, c) => acc + c.nombreEtudiants, 0)} étudiants au total
            </p>
          </div>
          <button className="ens-toggle" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>

        {/* ── CONTENU ── */}
        <div className="ens-card">
          {error && (
            <div style={{ padding:"12px", borderRadius:"10px",
              background:"#fef2f2", color:"#ef4444", marginBottom:"16px" }}>
              ⚠️ {error}
            </div>
          )}

          {classes.length === 0 && !error ? (
            <p style={{ textAlign:"center", padding:"32px", opacity:0.5 }}>
              Aucune classe trouvée.
            </p>
          ) : (
            <div className="ens-classes-grid">
              {classes.map((classe) => (
                <div key={classe.nom} className="ens-class-card">
                  <div className="ens-class-icon">🏫</div>
                  <div className="ens-class-name">{classe.nom}</div>
                  <div className="ens-class-niveau">{classe.niveau}</div>
                  <div className="ens-class-count">
                    👥 {classe.nombreEtudiants} étudiant{classe.nombreEtudiants > 1 ? "s" : ""}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── RETOUR ── */}
        <button className="ens-back-btn" onClick={() => window.history.back()}>
          ← Retour
        </button>

      </div>
    </div>
  );
}