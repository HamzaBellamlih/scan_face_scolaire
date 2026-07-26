import React, { useState, useEffect } from "react";
import "./css/enseignant.css";

export default function Presences() {
  const [darkMode,      setDarkMode]      = useState(true);
  const [etudiants,     setEtudiants]     = useState([]);
  const [classes,       setClasses]       = useState([]);
  const [classeFiltre,  setClasseFiltre]  = useState("");
  const [matiere,       setMatiere]       = useState("");
  const [date,          setDate]          = useState(new Date().toISOString().split("T")[0]);
  const [presences,     setPresences]     = useState({});
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState("");
  const [success,       setSuccess]       = useState("");
  const [submitting,    setSubmitting]    = useState(false);

  // ── Charger les étudiants ──
  useEffect(() => {
    const fetchEtudiants = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8008/api/lister_etudiants/");
        if (!res.ok) throw new Error("Erreur chargement étudiants");
        const data = await res.json();
        setEtudiants(data);
        const cls = [...new Set(data.map((e) => e.classe))].sort();
        setClasses(cls);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchEtudiants();
  }, []);

  const etudiantsFiltres = classeFiltre
    ? etudiants.filter((e) => e.classe === classeFiltre)
    : etudiants;

  const handlePresenceChange = (etudiantId, value) => {
    setPresences((prev) => ({ ...prev, [etudiantId]: value }));
  };

  // Tout marquer présent d'un coup
  const handleTousPresents = () => {
    const all = {};
    etudiantsFiltres.forEach((e) => { all[e.id] = "present"; });
    setPresences(all);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!matiere.trim()) {
      setError("Veuillez saisir la matière.");
      return;
    }

    if (!date) {
      setError("Veuillez sélectionner une date.");
      return;
    }

    const lignes = etudiantsFiltres.filter(
      (etud) => presences[etud.id] && presences[etud.id] !== ""
    );

    if (lignes.length === 0) {
      setError("Aucune présence saisie.");
      return;
    }

    setSubmitting(true);
    try {
      const errors = [];

      for (const etud of lignes) {
        const payload = {
          etudiant_id:   etud.id,
          date:          date,
          matiere:       matiere.trim(),
          type_absence:  presences[etud.id],
        };

        const res = await fetch("http://127.0.0.1:8008/api/absences_enseignant/", {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify(payload),
        });

        if (!res.ok) {
          try {
            const text = await res.text();
            let msg = `erreur ${res.status}`;
            try { msg = JSON.parse(text).message || msg; } catch(_) { msg = text.slice(0, 150); }
            errors.push(`${etud.prenom} ${etud.nom} : ${msg}`);
          } catch {
            errors.push(`${etud.prenom} ${etud.nom} : erreur ${res.status}`);
          }
        }
      }

      if (errors.length > 0) {
        setError(errors.join(" | "));
        return;
      }

      setSuccess(`✅ ${lignes.length} présence(s) enregistrée(s) avec succès !`);
      setPresences({});
    } catch (err) {
      setError(`Erreur réseau : ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading)
    return (
      <div className={`ens-page ${darkMode ? "dark" : "light"}`}>
        <div className="ens-loading">
          <div className="ens-spinner" />
          Chargement des étudiants...
        </div>
      </div>
    );

  return (
    <div className={`ens-page ${darkMode ? "dark" : "light"}`}>
      <div className="ens-wrapper">

        {/* ── HEADER ── */}
        <div className="ens-header">
          <div className="ens-header-icon">✅</div>
          <div className="ens-header-info">
            <h1 className="ens-header-title">Gestion des Présences</h1>
            <p className="ens-header-sub">Appel et suivi des présences</p>
          </div>
          <button className="ens-toggle" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>

        <div className="ens-card">
          <form onSubmit={handleSubmit}>

            {/* ── Filtres ── */}
            <div className="ens-grid">
              <div className="ens-form-group">
                <label className="ens-label">Classe</label>
                <select
                  className="ens-input"
                  value={classeFiltre}
                  onChange={(e) => setClasseFiltre(e.target.value)}
                >
                  <option value="">Toutes les classes</option>
                  {classes.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div className="ens-form-group">
                <label className="ens-label">Matière <span style={{ color: "#ef4444" }}>*</span></label>
                <input
                  type="text"
                  className="ens-input"
                  value={matiere}
                  onChange={(e) => setMatiere(e.target.value)}
                  placeholder="Ex: Mathématiques"
                />
              </div>

              <div className="ens-form-group">
                <label className="ens-label">Date</label>
                <input
                  type="date"
                  className="ens-input"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                />
              </div>
            </div>

            {/* ── Bouton tout présent ── */}
            <div style={{ marginBottom: "12px" }}>
              <button
                type="button"
                onClick={handleTousPresents}
                style={{
                  background: "rgba(16,185,129,0.15)",
                  border: "1px solid rgba(16,185,129,0.3)",
                  borderRadius: "10px",
                  padding: "8px 16px",
                  color: "#10b981",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: "600",
                }}
              >
                ✅ Tous présents
              </button>
            </div>

            {/* ── Tableau ── */}
            <div className="ens-table-container">
              <table className="ens-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nom</th>
                    <th>Prénom</th>
                    <th>Classe</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {etudiantsFiltres.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: "center", padding: "24px" }}>
                        Aucun étudiant trouvé
                      </td>
                    </tr>
                  ) : (
                    etudiantsFiltres.map((etud) => (
                      <tr key={etud.id}>
                        <td>{etud.id}</td>
                        <td>{etud.nom}</td>
                        <td>{etud.prenom}</td>
                        <td>{etud.classe}</td>
                        <td>
                          <select
                            className="ens-input-inline"
                            value={presences[etud.id] || ""}
                            onChange={(e) => handlePresenceChange(etud.id, e.target.value)}
                          >
                            <option value="">—</option>
                            <option value="present">✅ Présent</option>
                            <option value="absence">❌ Absent</option>
                            <option value="retard">⏰ Retard</option>
                          </select>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {error && (
              <div style={{ marginTop:"16px", padding:"12px", borderRadius:"10px",
                background:"#fef2f2", color:"#ef4444", fontSize:"13px" }}>
                ⚠️ {error}
              </div>
            )}
            {success && (
              <div style={{ marginTop:"16px", padding:"12px", borderRadius:"10px",
                background:"#f0fdf4", color:"#10b981", fontSize:"13px" }}>
                {success}
              </div>
            )}

            <button
              type="submit"
              className="ens-btn ens-btn--primary"
              disabled={submitting}
              style={{ marginTop: "24px" }}
            >
              {submitting ? "Enregistrement..." : "✅ Enregistrer les présences"}
            </button>
          </form>
        </div>

        <button className="ens-back-btn" onClick={() => window.history.back()}>
          ← Retour
        </button>

      </div>
    </div>
  );
}