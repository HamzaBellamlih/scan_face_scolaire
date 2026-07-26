import React, { useState } from "react";
import "./css/acceuil.css";

export default function Acceuil() {  // Majuscule ici !
  const [isDark, setIsDark] = useState(true);
  
  const toggleTheme = () => {
    setIsDark(!isDark);
  };

  return (
    <div className={isDark ? "page-container dark" : "page-container light"}>
      {/* Toggle Switch */}
      <div className="toggle-container">
        <label className="toggle-label">{isDark ? 'Mode Sombre' : 'Mode Clair'}</label>
        <label className="toggle-switch">
          <input type="checkbox" checked={isDark} onChange={toggleTheme} />
          <span className="toggle-slider"></span>
        </label>
      </div>

      {/* Page Title */}
      <h1 className="page-title">Gestion des Étudiants et Enseignants</h1>

      {/* Actions Grid */}
      <div className="actions-grid">
        {/* Search by Face Card */}
        <div className="action-card" onClick={() => window.location.href = "/face_recherche"}>
          <h2>Search by face</h2>
        </div>

        {/* Search by Write Card */}
        <div className="action-card" onClick={() => window.location.href = "/search"}>
          <h2>Search by id</h2>
        </div>
      </div>

      {/* Return Button */}
      <div className="retour-card" onClick={() => window.location.href = "/"}>
        <h2>Retour</h2>
      </div>
    </div>
  );
}