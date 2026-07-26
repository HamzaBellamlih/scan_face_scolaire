import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./css/login.css";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [isDarkMode, setIsDarkMode] = useState(true);

  const navigate = useNavigate();

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
  };

  const handleLogin = (e) => {
    e.preventDefault();
    setMessage("");

    // Trim pour supprimer les espaces
    const user = username.trim();
    const pass = password.trim();

    console.log("Username:", user, "Password:", pass); // Debug

    // Premier compte : admin / 1234
    if (user === "admin" && pass === "1234") {
      localStorage.setItem("token", "fake-jwt-token-admin");
      navigate("/acceuil");
      return;
    }
    
    // Deuxième compte : administrateur / 2345
    if (user === "administrateur" && pass === "2345") {
      localStorage.setItem("token", "fake-jwt-token-administrateur");
      navigate("/acceuil_ad");
      return;
    }

    // Si aucun ne correspond
    setMessage("Nom d'utilisateur ou mot de passe incorrect");
  };
  
  return (
    <div className={`login-container ${isDarkMode ? "dark-mode" : "light-mode"}`}>
      <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
        {isDarkMode ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="5"/>
            <line x1="12" y1="1" x2="12" y2="3"/>
            <line x1="12" y1="21" x2="12" y2="23"/>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
            <line x1="1" y1="12" x2="3" y2="12"/>
            <line x1="21" y1="12" x2="23" y2="12"/>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
          </svg>
        )}
      </button>

      <form className="login-box" onSubmit={handleLogin}>
        <h2>Connexion</h2>

        <div className="input-group">
          <input
            type="text"
            placeholder=" "
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
          <label>Nom d'utilisateur</label>
        </div>

        <div className="input-group">
          <input
            type="password"
            placeholder=" "
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          <label>Mot de passe</label>
        </div>

        <button type="submit" className="submit-btn">Se connecter</button>
        
        {message && <p className="message error">{message}</p>}
        
        <button 
          type="button" 
          className="back-button" 
          onClick={() => navigate("/")}
        >
          Retour
        </button>
      </form>
    </div>
  );
}