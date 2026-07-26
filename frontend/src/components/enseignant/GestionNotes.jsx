import React, { useState, useEffect } from "react";
import "./css/enseignant.css";

export default function GestionNotes() {
  const [darkMode, setDarkMode]         = useState(true);
  const [etudiants, setEtudiants]       = useState([]);
  const [enseignants, setEnseignants]   = useState([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState("");
  const [success, setSuccess]           = useState("");

  const [classeFiltre, setClasseFiltre] = useState("");
  const [classes, setClasses]           = useState([]);

  const [enseignantId, setEnseignantId] = useState(
    localStorage.getItem("enseignant_id") || ""
  );
  const [matiere,     setMatiere]       = useState("");
  const [typeExamen,  setTypeExamen]    = useState("devoir");
  const [semestre,    setSemestre]      = useState("1");
  const [coefficient, setCoefficient]  = useState("1");

  const [notes, setNotes] = useState({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [resEtud, resEns] = await Promise.all([
          fetch("http://127.0.0.1:8008/api/lister_etudiants/"),
          fetch("http://127.0.0.1:8008/api/lister_enseignants/"),
        ]);

        if (!resEtud.ok) throw new Error("Erreur chargement étudiants");
        if (!resEns.ok)  throw new Error("Erreur chargement enseignants");

        const dataEtud = await resEtud.json();
        const dataEns  = await resEns.json();

        setEtudiants(dataEtud);
        setEnseignants(dataEns);

        const cls = [...new Set(dataEtud.map((e) => e.classe))].sort();
        setClasses(cls);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const etudiantsFiltres = classeFiltre
    ? etudiants.filter((e) => e.classe === classeFiltre)
    : etudiants;

  const handleNoteChange = (etudiantId, value) => {
    setNotes((prev) => ({ ...prev, [etudiantId]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!enseignantId) {
      setError("Veuillez sélectionner un enseignant.");
      return;
    }
    if (!matiere.trim()) {
      setError("Veuillez saisir la matière.");
      return;
    }

    const notesASauvegarder = etudiantsFiltres.filter(
      (etud) => notes[etud.id] !== undefined && notes[etud.id] !== ""
    );

    if (notesASauvegarder.length === 0) {
      setError("Aucune note saisie.");
      return;
    }

    for (const etud of notesASauvegarder) {
      const val = parseFloat(notes[etud.id]);
      if (isNaN(val) || val < 0 || val > 20) {
        setError(`Note invalide pour ${etud.prenom} ${etud.nom} (doit être entre 0 et 20).`);
        return;
      }
    }

    try {
      const errors = [];

      for (const etud of notesASauvegarder) {
        const payload = {
          enseignant_id: parseInt(enseignantId),
          etudiant_id:   etud.id,
          matiere:       matiere.trim(),
          note:          parseFloat(notes[etud.id]),
          coefficient:   parseFloat(coefficient) || 1,
          type_examen:   typeExamen,
          semestre:      parseInt(semestre),
        };

        const res = await fetch("http://127.0.0.1:8008/api/notes_enseignant/", {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify(payload),
        });

        if (!res.ok) {
          try {
            const errData = await res.json();
            errors.push(`${etud.prenom} ${etud.nom} : ${errData.message || `erreur ${res.status}`}`);
          } catch (_) {
            errors.push(`${etud.prenom} ${etud.nom} : erreur ${res.status} ${error.message}`);
          }
        }
      }

      if (errors.length > 0) {
        setError(errors.join(" | "));
        return;
      }

      setSuccess(`✅ ${notesASauvegarder.length} note(s) enregistrée(s) avec succès !`);
      setNotes({});
    } catch (err) {
      setError(`Erreur réseau : ${err.message}`);
    }
  };

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
          <div className="ens-header-icon">📝</div>
          <div className="ens-header-info">
            <h1 className="ens-header-title">Gestion des Notes</h1>
            <p className="ens-header-sub">Saisie et modification des notes</p>
          </div>
          <button className="ens-toggle" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>

        <div className="ens-card">
          <form onSubmit={handleSubmit}>
            <div className="ens-grid">

              {/* ── Sélecteur enseignant ── */}
              <div className="ens-form-group">
                <label className="ens-label">Enseignant <span style={{ color: "#ef4444" }}>*</span></label>
                <select
                  className="ens-input"
                  value={enseignantId}
                  onChange={(e) => {
                    setEnseignantId(e.target.value);
                    localStorage.setItem("enseignant_id", e.target.value);
                  }}
                >
                  <option value="">Sélectionner un enseignant</option>
                  {enseignants.map((ens) => (
                    <option key={ens.id} value={ens.id}>
                      {ens.prenom} {ens.nom} — {ens.matiere}
                    </option>
                  ))}
                </select>
              </div>

              {/* ── Filtre classe ── */}
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
                <label className="ens-label">Type d'examen</label>
                <select
                  className="ens-input"
                  value={typeExamen}
                  onChange={(e) => setTypeExamen(e.target.value)}
                >
                  <option value="devoir">Devoir</option>
                  <option value="examen">Examen</option>
                  <option value="rattrapage">Rattrapage</option>
                  <option value="tp">TP</option>
                </select>
              </div>

              <div className="ens-form-group">
                <label className="ens-label">Semestre</label>
                <select
                  className="ens-input"
                  value={semestre}
                  onChange={(e) => setSemestre(e.target.value)}
                >
                  <option value="1">Semestre 1</option>
                  <option value="2">Semestre 2</option>
                </select>
              </div>

              <div className="ens-form-group">
                <label className="ens-label">Coefficient</label>
                <input
                  type="number"
                  className="ens-input"
                  value={coefficient}
                  onChange={(e) => setCoefficient(e.target.value)}
                  min="0.5"
                  max="10"
                  step="0.5"
                />
              </div>
            </div>

            {/* ── Tableau étudiants ── */}
            <div className="ens-table-container">
              <table className="ens-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nom</th>
                    <th>Prénom</th>
                    <th>Classe</th>
                    <th>Note (/20)</th>
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
                          <input
                            type="number"
                            className="ens-input-inline"
                            value={notes[etud.id] || ""}
                            onChange={(e) => handleNoteChange(etud.id, e.target.value)}
                            min="0"
                            max="20"
                            step="0.25"
                            placeholder="—"
                          />
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {error && (
              <div style={{ marginTop: "16px", padding: "12px", borderRadius: "10px", background: "#fef2f2", color: "#ef4444", fontSize: "13px" }}>
                ⚠️ {error}
              </div>
            )}
            {success && (
              <div style={{ marginTop: "16px", padding: "12px", borderRadius: "10px", background: "#f0fdf4", color: "#10b981", fontSize: "13px" }}>
                {success}
              </div>
            )}

            <button
              type="submit"
              className="ens-btn ens-btn--primary"
              style={{ marginTop: "24px" }}
            >
              ✅ Enregistrer les notes
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