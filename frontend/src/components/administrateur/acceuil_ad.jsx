import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './css/acceuil_ad.css';

const AcceuilAd = () => {
  const navigate = useNavigate();
  const [isDark, setIsDark] = useState(true);

  const buttons = [
    { label: 'Assurance Étudiant',  path: '/assurance_etud', icon: '🎓' },
    { label: 'Assurance Enseignant', path: '/assurance_ense', icon: '👨‍🏫' },
    { label: 'Paiement',             path: '/paiement_ense',  icon: '💳' },
  ];

  return (
    <div className={isDark ? "admin-page dark" : "admin-page light"}>

      {/* ── Toggle ☀️/🌙 ── */}
      <button
        type="button"
        className="theme-toggle-btn"
        onClick={() => setIsDark(!isDark)}
      >
        {isDark ? "☀️" : "🌙"}
      </button>

      <h2 className="page-title">Espace Administrateur</h2>

      <div className="buttons-grid">
        {buttons.map((btn, index) => (
          <button
            key={index}
            className="action-btn"
            onClick={() => navigate(btn.path)}
          >
            <span className="btn-icon">{btn.icon}</span>
            <span className="btn-label">{btn.label}</span>
          </button>
        ))}
      </div>

      <button className="back-btn" onClick={() => navigate('/')}>
        ← Retour
      </button>
    </div>
  );
};

export default AcceuilAd;