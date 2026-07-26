import React, { useState, useEffect } from "react";
import "./css/liste_etudiant.css";
import { useNavigate } from "react-router-dom";

function Liste_Etudiants() {
  const [etudiants, setEtudiants] = useState([]);
  const navigate = useNavigate();

  const API_BASE_URL = "http://127.0.0.1:8008";

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/lister_etudiants`)
      .then((res) => res.json())
      .then((data) => {
        console.log("Données reçues :", data); // Vérifiez ici le format de 'photo'
        setEtudiants(data);
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
      <h2 className="page-title">Liste des Étudiants</h2>

      <div className="table-wrapper">
        <table className="students-table">
          <thead>
            <tr>
              <th className="col-id">Id</th>
              <th className="col-photo">Photo</th>
              <th className="col-nom">Nom</th>
              <th className="col-prenom">Prénom</th>
              <th className="col-niveau">Niveau</th>
              <th className="col-classe">Classe</th>
              <th className="col-email">Email</th>
              <th className="col-date">Date de naissance</th>
              <th className="col-lieu">Lieu de naissance</th>
              <th className="col-telephone">Téléphone</th>
              <th className="col-actions">Action</th>
            </tr>
          </thead>

          <tbody>
            {etudiants.map((e) => (
              <tr className="student-row" key={e.id}>
                <td className="cell-id">{e.id}</td>

                <td className="cell-photo">
                  {e.photo ? (
                    <img
                      src={getPhotoSource(e.photo)}
                      alt={`${e.nom} ${e.prenom}`}
                      className="student-photo"
                      onError={(ev) => {
                        ev.target.src = "https://via.placeholder.com/50";
                      }}
                    />
                  ) : (
                    <span className="no-photo-placeholder">👤</span>
                  )}
                </td>

                <td className="cell-nom">{e.nom}</td>
                <td className="cell-prenom">{e.prenom}</td>
                <td className="cell-niveau">{e.niveau_etude}</td>
                <td className="cell-classe">{e.classe}</td>
                <td className="cell-email">{e.email}</td>
                <td className="cell-date">{e.date_naissance}</td>
                <td className="cell-lieu">{e.lieu_naissance}</td>
                <td className="cell-telephone">{e.telephone}</td>

                <td className="cell-actions">
                  <button
                    className="btn-action btn-edit"
                    onClick={() => navigate(`/modification_etudiant/${e.id}`)}
                  >
                    Modifier
                  </button>

                  <button
                    className="btn-action btn-delete"
                    onClick={() => navigate(`/supression_etudiant/${e.id}`)}
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

export default Liste_Etudiants;