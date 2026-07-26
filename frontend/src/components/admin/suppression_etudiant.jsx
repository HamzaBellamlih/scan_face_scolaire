import React, { useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import "./css/suppression_etudiant.css";

export default function SupprimerEtudiant({onDeleted }) {
  const { etudiant_id } = useParams();
  const etudiantId = Number(etudiant_id);
  const [etudiant, setEtudiant] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // 🔄 Charger l'etudiant
  useEffect(() => {
    if (!etudiantId) return;

    axios
      .get(`http://127.0.0.1:8008/api/chercher_etudiant/${etudiantId}/`)
      .then((res) => setEtudiant(res.data))
      .catch(() =>
        setError("❌ Erreur lors de la récupération de l'etudiant")
      );
  }, [etudiantId]);
  // 🗑️ Supprimer
  const handleDelete = async () => {
    try {
      await axios.delete(
        `http://127.0.0.1:8008/api/supprimer_etudiant/${etudiantId}/`
      );

      setMessage("✅ Etudiant supprimé avec succès");
      if (onDeleted) onDeleted();
    } catch (err) {
      setError("❌ Erreur lors de la suppression");
    }
    window.history.back();
  };

  return (
    <div className="supprimer-etudiant">
      <h2>Supprimer Etudiant</h2>

      {message && <p style={{ color: "green" }}>{message}</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {etudiant && (
        <p>
          Voulez-vous supprimer l'etudiant{" "}
          <strong>
            {etudiant.nom} {etudiant.prenom}
          </strong>{" "}
          ?
        </p>
      )}

      <button onClick={handleDelete} className="btn-danger">
        Supprimer
      </button>

      <button
        className="back-button"
        onClick={() => window.history.back()}
      >
        Retour
      </button>
    </div>
  );
}