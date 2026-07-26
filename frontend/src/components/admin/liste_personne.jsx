import React, { useState, useEffect } from "react";
import "./css/liste_personne.css";
import { useNavigate } from "react-router-dom";

function Liste_Personnes() {
  const [personnes, setPersonnes] = useState([]);
  const navigate = useNavigate();

  const API_BASE_URL = "http://127.0.0.1:8008";

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/lister_personnes`)
      .then((res) => res.json())
      .then((data) => {
        console.log("Données reçues :", data); // Vérifiez ici le format de 'photo'
        setPersonnes(data);
      })
      .catch((err) => console.error("Erreur API:", err));
  }, []);

  const getPhotoSource = (photoPath) => {
    const PLACEHOLDER = "https://via.placeholder.com/50?text=No+Photo";
    if (!photoPath) return PLACEHOLDER;
    if (photoPath.startsWith("http")) return photoPath;
    return `${API_BASE_URL}${photoPath.startsWith("/") ? "" : "/"}${photoPath}`;
  };

  return (
    <div className="list-container">
      <h2 className="page-title">Liste des Personnes</h2>

      <div className="table-wrapper">
        <table className="personnes-table">
          <thead>
            <tr>
              <th className="col-id">Id</th>
              <th className="col-photo">Photo</th>
              <th className="col-nom">Nom</th>
              <th className="col-prenom">Prénom</th>
              <th className="col-email">Email</th>
              <th className="col-date">Date de naissance</th>
              <th className="col-lieu">Lieu de naissance</th>
              <th className="col-telephone">Téléphone</th>
              <th className="col-actions">Action</th>
            </tr>
          </thead>

          <tbody>
            {personnes.map((p) => (
              <tr className="personne-row" key={p.id}>
                <td className="cell-id">{p.id}</td>

                <td className="cell-photo">
                  {p.photo ? (
                    <img
                      src={getPhotoSource(p.photo)}
                      alt={`${p.nom} ${p.prenom}`}
                      className="student-photo"
                      onError={(ev) => {
                        ev.target.src = "https://via.placeholder.com/50";
                      }}
                    />
                  ) : (
                    <span className="no-photo-placeholder">👤</span>
                  )}
                </td>

                <td className="cell-nom">{p.nom}</td>
                <td className="cell-prenom">{p.prenom}</td>
                <td className="cell-email">{p.email}</td>
                <td className="cell-date">{p.date_naissance}</td>
                <td className="cell-lieu">{p.lieu_naissance}</td>
                <td className="cell-telephone">{p.telephone}</td>

                <td className="cell-actions">
                  <button
                    className="btn-action btn-edit"
                    onClick={() => navigate(`/modification_personne/${p.id}`)}
                  >
                    Modifier
                  </button>

                  <button
                    className="btn-action btn-delete"
                    onClick={() => navigate(`/supression_personne/${p.id}`)}
                  >
                    Supprimer
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        className="back-button"
        onClick={() => navigate("/Acceuil")}
      >
        Retour
      </button>
    </div>
  );
}

export default Liste_Personnes;