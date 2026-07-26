import React, { useState, useEffect } from "react";
import axios from "axios";
import "./css/search.css";

export default function Search() {
  const [isDark, setIsDark] = useState(true);
  const [searchType, setSearchType] = useState("etudiant");
  const [searchId, setSearchId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Smooth scroll au montage
  useEffect(() => {
    document.documentElement.style.scrollBehavior = 'smooth';
    return () => {
      document.documentElement.style.scrollBehavior = 'auto';
    };
  }, []);

  const handleSearch = async () => {
    if (!searchId) {
      setError("Veuillez entrer un ID");
      return;
    }

    setError("");
    setResult(null);
    setLoading(true);

    try {
      let endpoint;
      if (searchType === "etudiant") {
        endpoint = `http://127.0.0.1:8008/api/chercher_etudiant/${searchId}/`;
      } else if (searchType === "enseignant") {
        endpoint = `http://127.0.0.1:8008/api/chercher_enseignant/${searchId}/`;
      } else {
        endpoint = `http://127.0.0.1:8008/api/chercher_personne/${searchId}/`;
      }

      const res = await axios.get(endpoint);
      console.log("✅ Résultat:", res.data);
      setResult(res.data);
      
      // Scroll vers les résultats
      setTimeout(() => {
        const resultCard = document.querySelector('.result-card');
        if (resultCard) {
          resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }, 100);
    } catch (err) {
      console.error("❌ Erreur:", err);
      setError(err.response?.data?.message || "Personne non trouvée");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleRetour = () => window.history.back();

  const typeBtnStyle = (val) => ({
    padding: "12px 24px",
    borderRadius: "16px",
    border: searchType === val ? "none" : "1px solid rgba(255,255,255,0.2)",
    background: searchType === val
      ? (val === "etudiant" ? "linear-gradient(135deg,#10b981,#059669)"
       : val === "enseignant" ? "linear-gradient(135deg,#6366f1,#8b5cf6)"
       : "linear-gradient(135deg,#f59e0b,#d97706)")
      : "transparent",
    color: "#fff",
    fontWeight: 700,
    fontSize: "14px",
    cursor: "pointer",
    transition: "all 0.2s",
  });

  return (
    <div className={`search-page ${isDark ? "dark" : "light"}`}>
      <div className="toggle-container">
        <label className="toggle-switch">
          <input type="checkbox" checked={isDark} onChange={() => setIsDark(!isDark)} />
          <span className="toggle-slider" />
        </label>
      </div>

      <div className="search-container">
        <h2 className="search-title">🔍 Rechercher une Personne</h2>

        {/* Type Selection */}
        <div className="search-type-buttons">
          <button style={typeBtnStyle("etudiant")} onClick={() => {
            setSearchType("etudiant");
            setResult(null);
            setError("");
          }}>
            🎓 Étudiant
          </button>
          <button style={typeBtnStyle("enseignant")} onClick={() => {
            setSearchType("enseignant");
            setResult(null);
            setError("");
          }}>
            👨‍🏫 Enseignant
          </button>
          <button style={typeBtnStyle("personne")} onClick={() => {
            setSearchType("personne");
            setResult(null);
            setError("");
          }}>
            👤 Personne
          </button>
        </div>

        {/* Search Input */}
        <div className="search-input-group">
          <input
            type="number"
            placeholder="Entrez l'ID..."
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
            onKeyPress={handleKeyPress}
            className="search-input"
          />
          <button onClick={handleSearch} className="btn-search" disabled={loading}>
            {loading ? "⏳ Recherche..." : "🔍 Rechercher"}
          </button>
        </div>

        {/* Error Message */}
        {error && <div className="error-message">⚠️ {error}</div>}

        {/* Result Card */}
        {result && (
          <div className="result-card">
            {/* Nom complet */}
            <h3 className="result-name">
              {result.prenom} {result.nom}
            </h3>

            {/* Type */}
            <p className="result-type">
              {searchType === "etudiant" ? "🎓 Étudiant"
             : searchType === "enseignant" ? "👨‍🏫 Enseignant"
             : "👤 Personne"}
            </p>

            {/* Onglet Informations */}
            {(
              <table className="result-table">
                <tbody>
                  <tr>
                    <td><strong>🆔 ID</strong></td>
                    <td>{result.id}</td>
                  </tr>
                  <tr>
                    <td><strong>📧 Email</strong></td>
                    <td>{result.email || "—"}</td>
                  </tr>
                  <tr>
                    <td><strong>📱 Téléphone</strong></td>
                    <td>{result.telephone || "—"}</td>
                  </tr>
                  <tr>
                    <td><strong>🎂 Date de naissance</strong></td>
                    <td>{result.date_naissance || "—"}</td>
                  </tr>
                  <tr>
                    <td><strong>📍 Lieu de naissance</strong></td>
                    <td>{result.lieu_naissance || "—"}</td>
                  </tr>
                  {searchType === "etudiant" && (
                    <>
                      <tr>
                        <td><strong>📚 Niveau d'étude</strong></td>
                        <td>{result.niveau_etude || "—"}</td>
                      </tr>
                      <tr>
                        <td><strong>🏫 Classe</strong></td>
                        <td>{result.classe || "—"}</td>
                      </tr>
                    </>
                  )}
                  {searchType === "enseignant" && (
                    <tr>
                      <td><strong>✏️ Matière</strong></td>
                      <td>{result.matiere || "—"}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Bouton Retour */}
        <button type="button" className="btn-retour" onClick={handleRetour}>
          ↩ Retour
        </button>
      </div>
    </div>
  );
}