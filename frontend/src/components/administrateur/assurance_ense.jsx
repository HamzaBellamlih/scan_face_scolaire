import React, { useState, useEffect } from "react";
import "./css/assurance_ense.css";

export default function AssuranceEnse() {
  const [darkMode, setDarkMode] = useState(true);
  const [enseignants, setEnseignants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedEnseignant, setSelectedEnseignant] = useState(null);

  // montantTotal par enseignant : { [id]: string }
  const [montantsTotaux, setMontantsTotaux] = useState({});

  // montantRestant réel par enseignant après paiement : { [id]: number }
  const [montantsRestants, setMontantsRestants] = useState({});

  // Formulaire paiement
  const [montantPaye, setMontantPaye] = useState("");
  const [montantRestant, setMontantRestant] = useState(0);

  // ── Charger enseignants + paiements existants ──
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 1. Charger les enseignants
        const res = await fetch("http://127.0.0.1:8008/api/lister_enseignants/");
        if (!res.ok) throw new Error("Erreur lors du chargement des enseignants");
        const data = await res.json();
        setEnseignants(data);

        // 2. Charger les paiements existants pour pré-remplir le tableau
        const resPaiements = await fetch("http://127.0.0.1:8008/api/assurance_enseignant/");
        if (resPaiements.ok) {
          const paiements = await resPaiements.json();
          const totaux = {};
          const restants = {};
          paiements.forEach((p) => {
            totaux[p.enseignant_id] = p.montant_total.toString();
            restants[p.enseignant_id] = p.montant_restant;
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

  // Recalculer montant restant quand montant payé change
  useEffect(() => {
    if (!selectedEnseignant) return;
    const baseRestant =
      montantsRestants[selectedEnseignant.id] !== undefined
        ? parseFloat(montantsRestants[selectedEnseignant.id])
        : parseFloat(montantsTotaux[selectedEnseignant.id]) || 0;
    const paye = parseFloat(montantPaye) || 0;
    setMontantRestant(baseRestant - paye);
  }, [montantPaye, selectedEnseignant, montantsTotaux, montantsRestants]);

  const handleMontantTotalChange = (id, value) => {
    setMontantsTotaux((prev) => ({ ...prev, [id]: value }));
    setMontantsRestants((prev) => {
      if (prev[id] === undefined) return prev;
      return { ...prev, [id]: undefined };
    });
  };

  const handleSelectEnseignant = (ens) => {
    if (!montantsTotaux[ens.id] || montantsTotaux[ens.id] === "") {
      setError("Veuillez d'abord saisir le montant total pour cet enseignant.");
      return;
    }
    setSelectedEnseignant(ens);
    setMontantPaye("");
    const restantExistant = montantsRestants[ens.id];
    setMontantRestant(
      restantExistant !== undefined
        ? parseFloat(restantExistant)
        : parseFloat(montantsTotaux[ens.id]) || 0
    );
    setError("");
  };

  const handleCancel = () => {
    setSelectedEnseignant(null);
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

    const total = parseFloat(montantsTotaux[selectedEnseignant.id]) || 0;
    const baseRestant =
      montantsRestants[selectedEnseignant.id] !== undefined
        ? parseFloat(montantsRestants[selectedEnseignant.id])
        : total;

    if (parseFloat(montantPaye) > baseRestant) {
      setError("Le montant payé ne peut pas dépasser le montant restant");
      return;
    }

    try {
      const payload = {
        enseignant_id: selectedEnseignant.id,
        montant_total: total,
        montant_paye: parseFloat(montantPaye),
        montant_restant: montantRestant,
      };

      const res = await fetch("http://127.0.0.1:8008/api/assurance_enseignant/", {
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
        [selectedEnseignant.id]: montantRestant,
      }));

      handleCancel();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading)
    return (
      <div className={`ae-page ${darkMode ? "dark" : "light"}`}>
        <div className="ae-loading">
          <div className="ae-spinner" />
          Chargement des enseignants...
        </div>
      </div>
    );

  return (
    <div className={`ae-page ${darkMode ? "dark" : "light"}`}>
      <div className="ae-wrapper">

        {/* ── HEADER ── */}
        <div className="ae-header">
          <div className="ae-header-icon">💼</div>
          <div className="ae-header-info">
            <h1 className="ae-header-title">Assurance Enseignants</h1>
            <p className="ae-header-sub">Gestion des paiements d'assurance</p>
          </div>
          <button
            type="button"
            className="ae-toggle"
            onClick={() => setDarkMode(!darkMode)}
          >
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>

        {/* ── CARD ── */}
        <div className="ae-card">

          {!selectedEnseignant ? (
            <>
              <div className="ae-section-title">
                <span className="ae-section-icon">👨‍🏫</span>
                Liste des enseignants ({enseignants.length})
              </div>

              {error && <div className="ae-alert ae-alert--error">⚠️ {error}</div>}

              <div className="ae-table-container">
                <table className="ae-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Nom</th>
                      <th>Prénom</th>
                      <th>Matière</th>
                      <th>Email</th>
                      <th>Montant total (DH)</th>
                      <th>Montant restant (DH)</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {enseignants.map((ens) => {
                      const total = parseFloat(montantsTotaux[ens.id]) || 0;
                      const restant =
                        montantsRestants[ens.id] !== undefined
                          ? parseFloat(montantsRestants[ens.id])
                          : total;

                      return (
                        <tr key={ens.id}>
                          <td>{ens.id}</td>
                          <td>{ens.nom}</td>
                          <td>{ens.prenom}</td>
                          <td>{ens.matiere}</td>
                          <td>{ens.email}</td>

                          <td>
                            <input
                              type="number"
                              className="ae-input-inline"
                              value={montantsTotaux[ens.id] || ""}
                              onChange={(e) =>
                                handleMontantTotalChange(ens.id, e.target.value)
                              }
                              placeholder="Ex: 5000"
                              min="0"
                              step="0.01"
                              onClick={(e) => e.stopPropagation()}
                            />
                          </td>

                          <td>
                            {total > 0 ? (
                              <span
                                className={`ae-badge ${
                                  restant === 0 ? "ae-badge--ok" : "ae-badge--pending"
                                }`}
                              >
                                {restant.toFixed(2)} DH
                              </span>
                            ) : (
                              <span className="ae-badge ae-badge--empty">—</span>
                            )}
                          </td>

                          <td>
                            <button
                              className="ae-btn ae-btn--select"
                              onClick={() => handleSelectEnseignant(ens)}
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
              <div className="ae-section-title">
                <span className="ae-section-icon">💳</span>
                Paiement assurance — {selectedEnseignant.prenom} {selectedEnseignant.nom}
              </div>

              <form onSubmit={handleSubmit}>
                <div className="ae-form-group">
                  <label className="ae-label">Montant total de l'assurance (DH)</label>
                  <div className="ae-montant-info">
                    {parseFloat(montantsTotaux[selectedEnseignant.id]).toFixed(2)} DH
                  </div>
                </div>

                <div className="ae-form-group">
                  <label className="ae-label">Montant restant avant ce paiement (DH)</label>
                  <div className="ae-montant-info">
                    {(
                      montantsRestants[selectedEnseignant.id] !== undefined
                        ? parseFloat(montantsRestants[selectedEnseignant.id])
                        : parseFloat(montantsTotaux[selectedEnseignant.id]) || 0
                    ).toFixed(2)} DH
                  </div>
                </div>

                <div className="ae-form-group">
                  <label className="ae-label">
                    Montant payé (DH) <span className="ae-req">*</span>
                  </label>
                  <input
                    type="number"
                    className="ae-input"
                    value={montantPaye}
                    onChange={(e) => setMontantPaye(e.target.value)}
                    placeholder="Ex: 2000"
                    min="0"
                    step="0.01"
                    required
                    autoFocus
                  />
                </div>

                <div className="ae-form-group">
                  <label className="ae-label">Montant restant après ce paiement (DH)</label>
                  <div
                    className={`ae-montant-restant ${
                      montantRestant === 0 ? "ae-montant-ok" : "ae-montant-pending"
                    }`}
                  >
                    {montantRestant.toFixed(2)} DH
                    {montantRestant === 0 ? " ✅" : " ⚠️"}
                  </div>
                </div>

                {error && (
                  <div className="ae-alert ae-alert--error">⚠️ {error}</div>
                )}

                <div className="ae-actions">
                  <button type="submit" className="ae-btn ae-btn--primary">
                    ✅ Enregistrer le paiement
                  </button>
                  <button
                    type="button"
                    className="ae-btn ae-btn--secondary"
                    onClick={handleCancel}
                  >
                    ✕ Annuler
                  </button>
                </div>
              </form>
            </>
          )}

          <div className="ae-divider" />

          <button
            type="button"
            className="ae-btn ae-btn--back"
            onClick={() => window.history.back()}
          >
            ← Retour
          </button>
        </div>
      </div>
    </div>
  );
}