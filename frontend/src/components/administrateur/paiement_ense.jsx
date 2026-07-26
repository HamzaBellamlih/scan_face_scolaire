import React, { useState, useEffect } from "react";
import "./css/paiement_ense.css";

export default function PaiementEnseignants() {
  const [darkMode, setDarkMode] = useState(true);
  const [enseignants, setEnseignants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedEnseignant, setSelectedEnseignant] = useState(null);

  const [salairesPrevus, setSalairesPrevus] = useState({});
  const [salairesRestants, setSalairesRestants] = useState({});

  const [mois, setMois] = useState("");
  const [annee, setAnnee] = useState(new Date().getFullYear().toString());
  const [salairePaye, setSalairePaye] = useState("");
  const [salaireRestant, setSalaireRestant] = useState(0);

  useEffect(() => {
    const fetchEnseignants = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8008/api/lister_enseignants/");
        if (!res.ok) throw new Error("Erreur lors du chargement des enseignants");
        const data = await res.json();
        setEnseignants(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    const fetchPaiements = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8008/api/paiement_enseignant/");
        if (!res.ok) return;
        const contentType = res.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) return;
        const paiements = await res.json();
        if (!Array.isArray(paiements)) return;
        const prevus = {};
        const restants = {};
        paiements.forEach((p) => {
          prevus[p.enseignant_id] = p.salaire_prevu.toString();
          restants[p.enseignant_id] = p.salaire_restant;
        });
        setSalairesPrevus(prevus);
        setSalairesRestants(restants);
      } catch (_) {}
    };

    fetchEnseignants();
    fetchPaiements();
  }, []);

  useEffect(() => {
    if (!selectedEnseignant) return;
    const baseRestant =
      salairesRestants[selectedEnseignant.id] !== undefined
        ? parseFloat(salairesRestants[selectedEnseignant.id])
        : parseFloat(salairesPrevus[selectedEnseignant.id]) || 0;
    const paye = parseFloat(salairePaye) || 0;
    setSalaireRestant(baseRestant - paye);
  }, [salairePaye, selectedEnseignant, salairesPrevus, salairesRestants]);

  const handleSalairesPrevusChange = (id, value) => {
    setSalairesPrevus((prev) => ({ ...prev, [id]: value }));
    setSalairesRestants((prev) => {
      if (prev[id] === undefined) return prev;
      return { ...prev, [id]: undefined };
    });
  };

  const handleSelectEnseignant = (ens) => {
    if (!salairesPrevus[ens.id] || salairesPrevus[ens.id] === "") {
      setError("Veuillez d'abord saisir le salaire prévu pour cet enseignant.");
      return;
    }
    setSelectedEnseignant(ens);
    setSalairePaye("");
    const currentMonth = new Date().getMonth() + 1;
    setMois(currentMonth.toString().padStart(2, "0"));
    setAnnee(new Date().getFullYear().toString());
    const restantExistant = salairesRestants[ens.id];
    setSalaireRestant(
      restantExistant !== undefined
        ? parseFloat(restantExistant)
        : parseFloat(salairesPrevus[ens.id]) || 0
    );
    setError("");
  };

  const handleCancel = () => {
    setSelectedEnseignant(null);
    setMois("");
    setAnnee(new Date().getFullYear().toString());
    setSalairePaye("");
    setSalaireRestant(0);
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!mois || !annee || !salairePaye) {
      setError("Veuillez remplir tous les champs");
      return;
    }

    const prevu = parseFloat(salairesPrevus[selectedEnseignant.id]) || 0;
    const baseRestant =
      salairesRestants[selectedEnseignant.id] !== undefined
        ? parseFloat(salairesRestants[selectedEnseignant.id])
        : prevu;

    if (parseFloat(salairePaye) > baseRestant) {
      setError("Le salaire payé ne peut pas dépasser le salaire restant");
      return;
    }

    try {
      const payload = {
        enseignant_id: selectedEnseignant.id,
        mois: parseInt(mois),
        annee: parseInt(annee),
        salaire_prevu: prevu,
        salaire_paye: parseFloat(salairePaye),
        salaire_restant: salaireRestant,
      };

      const res = await fetch("http://127.0.0.1:8008/api/paiement_enseignant/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        let msg = "Erreur lors de l'enregistrement";
        try {
          const errData = await res.json();
          msg = errData.message || msg;
        } catch (_) {}
        throw new Error(msg);
      }

      alert("✅ Paiement enregistré avec succès!");

      setSalairesRestants((prev) => ({
        ...prev,
        [selectedEnseignant.id]: salaireRestant,
      }));

      handleCancel();
    } catch (err) {
      setError(err.message);
    }
  };

  const moisOptions = [
    { value: "01", label: "Janvier" },
    { value: "02", label: "Février" },
    { value: "03", label: "Mars" },
    { value: "04", label: "Avril" },
    { value: "05", label: "Mai" },
    { value: "06", label: "Juin" },
    { value: "07", label: "Juillet" },
    { value: "08", label: "Août" },
    { value: "09", label: "Septembre" },
    { value: "10", label: "Octobre" },
    { value: "11", label: "Novembre" },
    { value: "12", label: "Décembre" },
  ];

  if (loading)
    return (
      <div className={`pe-page ${darkMode ? "dark" : "light"}`}>
        <div className="pe-loading">
          <div className="pe-spinner" />
          Chargement des enseignants...
        </div>
      </div>
    );

  return (
    <div className={`pe-page ${darkMode ? "dark" : "light"}`}>
      <div className="pe-wrapper">

        <div className="pe-header">
          <div className="pe-header-icon">💰</div>
          <div className="pe-header-info">
            <h1 className="pe-header-title">Paiement Enseignants</h1>
            <p className="pe-header-sub">Gestion des salaires mensuels</p>
          </div>
          <button type="button" className="pe-toggle" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>

        <div className="pe-card">

          {!selectedEnseignant ? (
            <>
              <div className="pe-section-title">
                <span className="pe-section-icon">👨‍🏫</span>
                Liste des enseignants ({enseignants.length})
              </div>

              {error && <div className="pe-alert pe-alert--error">⚠️ {error}</div>}

              <div className="pe-table-container">
                <table className="pe-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Nom</th>
                      <th>Prénom</th>
                      <th>Matière</th>
                      <th>Email</th>
                      <th>Téléphone</th>
                      <th>Salaire prévu (DH)</th>
                      <th>Salaire restant (DH)</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {enseignants.map((ens) => {
                      const prevu = parseFloat(salairesPrevus[ens.id]) || 0;
                      const restant =
                        salairesRestants[ens.id] !== undefined
                          ? parseFloat(salairesRestants[ens.id])
                          : prevu;

                      return (
                        <tr key={ens.id}>
                          <td>{ens.id}</td>
                          <td>{ens.nom}</td>
                          <td>{ens.prenom}</td>
                          <td>{ens.matiere}</td>
                          <td>{ens.email}</td>
                          <td>{ens.telephone}</td>

                          <td>
                            <input
                              type="number"
                              className="pe-input-inline"
                              value={salairesPrevus[ens.id] || ""}
                              onChange={(e) => handleSalairesPrevusChange(ens.id, e.target.value)}
                              placeholder="Ex: 8000"
                              min="0"
                              step="0.01"
                              onClick={(e) => e.stopPropagation()}
                            />
                          </td>

                          <td>
                            {prevu > 0 ? (
                              <span className={`pe-badge ${restant === 0 ? "pe-badge--ok" : "pe-badge--pending"}`}>
                                {restant.toFixed(2)} DH
                              </span>
                            ) : (
                              <span className="pe-badge pe-badge--empty">—</span>
                            )}
                          </td>

                          <td>
                            <button
                              className="pe-btn pe-btn--select"
                              onClick={() => handleSelectEnseignant(ens)}
                            >
                              💵 Payer
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
              <div className="pe-section-title">
                <span className="pe-section-icon">💳</span>
                Paiement salaire — {selectedEnseignant.prenom} {selectedEnseignant.nom}
              </div>

              <form onSubmit={handleSubmit}>
                <div className="pe-grid">
                  <div className="pe-form-group">
                    <label className="pe-label">Mois <span className="pe-req">*</span></label>
                    <select className="pe-input" value={mois} onChange={(e) => setMois(e.target.value)} required>
                      <option value="">Sélectionner un mois</option>
                      {moisOptions.map((m) => (
                        <option key={m.value} value={m.value}>{m.label}</option>
                      ))}
                    </select>
                  </div>

                  <div className="pe-form-group">
                    <label className="pe-label">Année <span className="pe-req">*</span></label>
                    <input
                      type="number"
                      className="pe-input"
                      value={annee}
                      onChange={(e) => setAnnee(e.target.value)}
                      placeholder="Ex: 2024"
                      min="2020"
                      max="2050"
                      required
                    />
                  </div>
                </div>

                <div className="pe-form-group">
                  <label className="pe-label">Salaire prévu (DH)</label>
                  <div className="pe-montant-info">
                    {parseFloat(salairesPrevus[selectedEnseignant.id]).toFixed(2)} DH
                  </div>
                </div>

                <div className="pe-form-group">
                  <label className="pe-label">Salaire restant avant ce paiement (DH)</label>
                  <div className="pe-montant-info">
                    {(
                      salairesRestants[selectedEnseignant.id] !== undefined
                        ? parseFloat(salairesRestants[selectedEnseignant.id])
                        : parseFloat(salairesPrevus[selectedEnseignant.id]) || 0
                    ).toFixed(2)} DH
                  </div>
                </div>

                <div className="pe-form-group">
                  <label className="pe-label">Salaire payé (DH) <span className="pe-req">*</span></label>
                  <input
                    type="number"
                    className="pe-input"
                    value={salairePaye}
                    onChange={(e) => setSalairePaye(e.target.value)}
                    placeholder="Ex: 8000"
                    min="0"
                    step="0.01"
                    required
                    autoFocus
                  />
                </div>

                <div className="pe-form-group">
                  <label className="pe-label">Salaire restant après ce paiement (DH)</label>
                  <div className={`pe-montant-restant ${salaireRestant === 0 ? "pe-montant-ok" : "pe-montant-pending"}`}>
                    {salaireRestant.toFixed(2)} DH
                    {salaireRestant === 0 ? " ✅" : " ⚠️"}
                  </div>
                </div>

                {error && <div className="pe-alert pe-alert--error">⚠️ {error}</div>}

                <div className="pe-actions">
                  <button type="submit" className="pe-btn pe-btn--primary">
                    ✅ Enregistrer le paiement
                  </button>
                  <button type="button" className="pe-btn pe-btn--secondary" onClick={handleCancel}>
                    ✕ Annuler
                  </button>
                </div>
              </form>
            </>
          )}

          <div className="pe-divider" />

          <button type="button" className="pe-btn pe-btn--back" onClick={() => window.history.back()}>
            ← Retour
          </button>
        </div>
      </div>
    </div>
  );
}