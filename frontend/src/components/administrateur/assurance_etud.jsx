import React, { useState, useEffect } from "react";
import "./css/assurance_etud.css";

export default function AssuranceEtud() {
  const [darkMode, setDarkMode] = useState(true);
  const [etudiants, setEtudiants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedEtudiant, setSelectedEtudiant] = useState(null);

  const [montantsTotaux, setMontantsTotaux] = useState({});
  const [montantsRestants, setMontantsRestants] = useState({});
  const [montantPaye, setMontantPaye] = useState("");
  const [montantRestant, setMontantRestant] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8008/api/lister_etudiants/");
        if (!res.ok) throw new Error("Erreur lors du chargement des étudiants");
        const data = await res.json();
        setEtudiants(data);

        const resPaiements = await fetch("http://127.0.0.1:8008/api/assurance_etudiant/");
        if (resPaiements.ok) {
          const paiements = await resPaiements.json();
          const totaux = {};
          const restants = {};
          paiements.forEach((p) => {
            totaux[p.etudiant_id] = p.montant_total.toString();
            restants[p.etudiant_id] = p.montant_restant;
          });
          setMontantsTotaux(totaux);
          setMontantsRestants(restants);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    if (!selectedEtudiant) return;
    const baseRestant =
      montantsRestants[selectedEtudiant.id] !== undefined
        ? parseFloat(montantsRestants[selectedEtudiant.id])
        : parseFloat(montantsTotaux[selectedEtudiant.id]) || 0;
    const paye = parseFloat(montantPaye) || 0;
    setMontantRestant(baseRestant - paye);
  }, [montantPaye, selectedEtudiant, montantsTotaux, montantsRestants]);

  const handleMontantTotalChange = (id, value) => {
    setMontantsTotaux((prev) => ({ ...prev, [id]: value }));
    setMontantsRestants((prev) => {
      if (prev[id] === undefined) return prev;
      return { ...prev, [id]: undefined };
    });
  };

  const handleSelectEtudiant = (etud) => {
    if (!montantsTotaux[etud.id] || montantsTotaux[etud.id] === "") {
      setError("Veuillez d'abord saisir le montant total pour cet étudiant.");
      return;
    }
    setSelectedEtudiant(etud);
    setMontantPaye("");
    const restantExistant = montantsRestants[etud.id];
    setMontantRestant(
      restantExistant !== undefined
        ? parseFloat(restantExistant)
        : parseFloat(montantsTotaux[etud.id]) || 0
    );
    setError("");
  };

  const handleCancel = () => {
    setSelectedEtudiant(null);
    setMontantPaye("");
    setMontantRestant(0);
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!montantPaye) {
      setError("Veuillez remplir le montant payé");
      return;
    }

    const total = parseFloat(montantsTotaux[selectedEtudiant.id]) || 0;
    const baseRestant =
      montantsRestants[selectedEtudiant.id] !== undefined
        ? parseFloat(montantsRestants[selectedEtudiant.id])
        : total;

    if (parseFloat(montantPaye) > baseRestant) {
      setError("Le montant payé ne peut pas dépasser le montant restant");
      return;
    }

    try {
      const payload = {
        etudiant_id: selectedEtudiant.id,
        montant_total: total,
        montant_paye: parseFloat(montantPaye),
        montant_restant: montantRestant,
      };

      const res = await fetch("http://127.0.0.1:8008/api/assurance_etudiant/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.message || "Erreur lors de l'enregistrement");
      }

      alert("✅ Paiement enregistré avec succès!");

      setMontantsRestants((prev) => ({
        ...prev,
        [selectedEtudiant.id]: montantRestant,
      }));

      handleCancel();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading)
    return (
      <div className={`aet-page ${darkMode ? "dark" : "light"}`}>
        <div className="aet-loading">
          <div className="aet-spinner" />
          Chargement des étudiants...
        </div>
      </div>
    );

  return (
    <div className={`aet-page ${darkMode ? "dark" : "light"}`}>
      <div className="aet-wrapper">

        <div className="aet-header">
          <div className="aet-header-icon">🎓</div>
          <div className="aet-header-info">
            <h1 className="aet-header-title">Assurance Étudiants</h1>
            <p className="aet-header-sub">Gestion des paiements d'assurance</p>
          </div>
          <button type="button" className="aet-toggle" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>

        <div className="aet-card">

          {!selectedEtudiant ? (
            <>
              <div className="aet-section-title">
                <span className="aet-section-icon">👨‍🎓</span>
                Liste des étudiants ({etudiants.length})
              </div>

              {error && <div className="aet-alert aet-alert--error">⚠️ {error}</div>}

              <div className="aet-table-container">
                <table className="aet-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Nom</th>
                      <th>Prénom</th>
                      <th>Classe</th>
                      <th>Niveau</th>
                      <th>Email</th>
                      <th>Montant total (DH)</th>
                      <th>Montant restant (DH)</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {etudiants.map((etud) => {
                      const total = parseFloat(montantsTotaux[etud.id]) || 0;
                      const restant =
                        montantsRestants[etud.id] !== undefined
                          ? parseFloat(montantsRestants[etud.id])
                          : total;

                      return (
                        <tr key={etud.id}>
                          <td>{etud.id}</td>
                          <td>{etud.nom}</td>
                          <td>{etud.prenom}</td>
                          <td>{etud.classe}</td>
                          <td>{etud.niveau_etude}</td>
                          <td>{etud.email}</td>

                          <td>
                            <input
                              type="number"
                              className="aet-input-inline"
                              value={montantsTotaux[etud.id] || ""}
                              onChange={(e) => handleMontantTotalChange(etud.id, e.target.value)}
                              placeholder="Ex: 300"
                              min="0"
                              step="0.01"
                              onClick={(e) => e.stopPropagation()}
                            />
                          </td>

                          <td>
                            {total > 0 ? (
                              <span className={`aet-badge ${restant === 0 ? "aet-badge--ok" : "aet-badge--pending"}`}>
                                {restant.toFixed(2)} DH
                              </span>
                            ) : (
                              <span className="aet-badge aet-badge--empty">—</span>
                            )}
                          </td>

                          <td>
                            <button
                              className="aet-btn aet-btn--select"
                              onClick={() => handleSelectEtudiant(etud)}
                            >
                              💰 Assurance
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <>
              <div className="aet-section-title">
                <span className="aet-section-icon">💳</span>
                Paiement assurance — {selectedEtudiant.prenom} {selectedEtudiant.nom}
              </div>

              <form onSubmit={handleSubmit}>
                <div className="aet-form-group">
                  <label className="aet-label">Montant total de l'assurance (DH)</label>
                  <div className="aet-montant-info">
                    {parseFloat(montantsTotaux[selectedEtudiant.id]).toFixed(2)} DH
                  </div>
                </div>

                <div className="aet-form-group">
                  <label className="aet-label">Montant restant avant ce paiement (DH)</label>
                  <div className="aet-montant-info">
                    {(
                      montantsRestants[selectedEtudiant.id] !== undefined
                        ? parseFloat(montantsRestants[selectedEtudiant.id])
                        : parseFloat(montantsTotaux[selectedEtudiant.id]) || 0
                    ).toFixed(2)} DH
                  </div>
                </div>

                <div className="aet-form-group">
                  <label className="aet-label">
                    Montant payé (DH) <span className="aet-req">*</span>
                  </label>
                  <input
                    type="number"
                    className="aet-input"
                    value={montantPaye}
                    onChange={(e) => setMontantPaye(e.target.value)}
                    placeholder="Ex: 300"
                    min="0"
                    step="0.01"
                    required
                    autoFocus
                  />
                </div>

                <div className="aet-form-group">
                  <label className="aet-label">Montant restant après ce paiement (DH)</label>
                  <div className={`aet-montant-restant ${montantRestant === 0 ? "aet-montant-ok" : "aet-montant-pending"}`}>
                    {montantRestant.toFixed(2)} DH
                    {montantRestant === 0 ? " ✅" : " ⚠️"}
                  </div>
                </div>

                {error && <div className="aet-alert aet-alert--error">⚠️ {error}</div>}

                <div className="aet-actions">
                  <button type="submit" className="aet-btn aet-btn--primary">
                    ✅ Enregistrer le paiement
                  </button>
                  <button type="button" className="aet-btn aet-btn--secondary" onClick={handleCancel}>
                    ✕ Annuler
                  </button>
                </div>
              </form>
            </>
          )}

          <div className="aet-divider" />

          <button type="button" className="aet-btn aet-btn--back" onClick={() => window.history.back()}>
            ← Retour
          </button>
        </div>
      </div>
    </div>
  );
}