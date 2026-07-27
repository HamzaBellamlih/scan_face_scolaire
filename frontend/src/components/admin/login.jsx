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
        {isDarkMode ? "🌙" : "☀️"}
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