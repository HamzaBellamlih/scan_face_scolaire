import React, { useState } from "react";
import "./css/acceuil.css";

export default function Acceuil() {
  const [isDark, setIsDark] = useState(true);

  const toggleTheme = () => {
    setIsDark(!isDark);
  };

  return (
    <div className={isDark ? "page-container dark" : "page-container light"}>
      {/* Toggle Switch */}
      <div className="toggle-container">
        <label className="toggle-switch">
          <input 
            type="checkbox" 
            checked={isDark} 
            onChange={toggleTheme}
          />
          <span className="toggle-slider"></span>
        </label>
      </div>

      <h1 className="page-title">Gestion des Étudiants et Enseignants</h1>

      <div className="actions-grid">
        {/* ---- ÉTUDIANTS ---- */}
        <div className="action-card" onClick={() => window.location.href = "/liste_etudiant"}>
          <h2>Lister Étudiants</h2>
        </div>

        <div className="action-card" onClick={() => window.location.href = "/ajout_etudiant"}>
          <h2>Ajouter Étudiant</h2>
        </div>

        {/* ---- ENSEIGNANTS ---- */}
        <div className="action-card" onClick={() => window.location.href = "/liste_enseignant"}>
          <h2>Lister Enseignants</h2>
        </div>

        <div className="action-card" onClick={() => window.location.href = "/ajout_enseignant"}>
          <h2>Ajouter Enseignant</h2>
        </div>

        {/* ---- PERSONNES ---- */}
        <div className="action-card" onClick={() => window.location.href = "/liste_personne"}>
          <h2>Lister Personnes</h2>
        </div>

        <div className="action-card" onClick={() => window.location.href = "/ajout_personne"}>
          <h2>Ajouter Personne</h2>
        </div>
      </div>

      <div className="retour-card" onClick={() => window.location.href = "/"}>
        <h2>Retour</h2>
      </div>
    </div>
  );
}