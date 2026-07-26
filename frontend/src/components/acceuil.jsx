import React from "react";
import { useNavigate } from "react-router-dom";
import "./acceuil.css";

function Acceuil() {
  const navigate = useNavigate();
  const [isDark, setIsDark] = React.useState(true);

  const toggleTheme = () => {
    setIsDark(!isDark);
  };

  return (
    <div className={isDark ? "choix-container dark" : "choix-container light"}>
      <div className="toggle-container">
        <label className="toggle-switch">
          <input type="checkbox" checked={isDark} onChange={toggleTheme} />
          <span className="toggle-slider"></span>
        </label>
      </div>
      <h1>Choisissez votre espace</h1>

      <div className="btn-group">
        <button
          className="btn client-btn"
          onClick={() => navigate("/acceuil_client")}
        >
          Espace Client
        </button>

        <button
          className="btn admin-btn"
          onClick={() => navigate("/login")}
        >
          Espace Admin
        </button>
        <button
          className="btn administrateur-btn"
          onClick={() => navigate("/login")}
        >
          Espace Administrateur
        </button>
        <button
          className="btn enseignant-btn"
          onClick={() => navigate("/login_enseignant")}
        >
          Espace Enseignant
        </button>
        <button
          className="btn etudiant-btn"
          onClick={() => navigate("/login_etudiant")}
        >
          Espace Etudiant
        </button>
      </div>
    </div>
  );
}

export default Acceuil;