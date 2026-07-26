import React, { useState, useEffect } from "react";
import "./css/liste_enseignant.css";
import { useNavigate } from "react-router-dom";

function Liste_Enseignants() {
  const [enseignants, setEnseignants] = useState([]);
  const navigate = useNavigate();

  // URL de ton backend Django
  const API_BASE_URL = "http://127.0.0.1:8008";

  useEffect(() => {
      fetch(`${API_BASE_URL}/api/lister_enseignants`)
        .then((res) => res.json())
        .then((data) => {
          console.log("Données reçues :", data); // Vérifiez ici le format de 'photo'
          setEnseignants(data);
        })
        .catch((err) => console.error("Erreur API:", err));
    }, []);

  // Fonction qui détecte le type de photo
  const getPhotoSource = (photoPath) => {
    const PLACEHOLDER = "https://via.placeholder.com/50?text=No+Photo";
    if (!photoPath) return PLACEHOLDER;
    if (photoPath.startsWith("http")) return photoPath;
    return `${API_BASE_URL}${photoPath.startsWith("/") ? "" : "/"}${photoPath}`;
  };

  return (
    <div className="list-container">
      <h2>Liste des Enseignants</h2>
      <div className="table-wrapper">
        <table className="students-table">
          <thead>
            <tr>
              <th>Id</th>
              <th>Photo</th>
              <th>Nom</th>
              <th>Prénom</th>
              <th>Matière</th>
              <th>Email</th>
              <th>Date de naissance</th>
              <th>Lieu de naissance</th>
              <th>Téléphone</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {enseignants.map((e) => {

              return (
                <tr key={e.id}>
                  <td>{e.id}</td>

                  <td className="cell-photo">
                    {e.photo ? (
                      <img
                        src={getPhotoSource(e.photo)}
                        alt={`${e.nom} ${e.prenom}`}
                        className="teacher-photo"
                        onError={(ev) => {
                          ev.target.src = "https://via.placeholder.com/50";
                        }}
                      />
                    ) : (
                      <span className="no-photo-placeholder">👤</span>
                    )}
                  </td>

                  <td>{e.nom}</td>
                  <td>{e.prenom}</td>
                  <td>{e.matiere}</td>
                  <td>{e.email}</td>
                  <td>{e.date_naissance}</td>
                  <td>{e.lieu_naissance}</td>
                  <td>{e.telephone}</td>
                  <td>
                    <div className="btn-action btn-edit" onClick={() => window.location.href = "/modification_enseignant/"+e.id}>
                      <h2>Modifier</h2>
                    </div>
                    <div className="btn-action btn-delete" onClick={() => window.location.href = "/supression_enseignant/"+e.id}>
                      <h2>Supprimer</h2>
                    </div>
                  </td>
                </tr>
              );
            })}
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

export default Liste_Enseignants;