import React, { useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import "./css/suppression_enseignant.css";

export default function SupprimerEnseignant({onDeleted }) {
  const { enseignant_id } = useParams();
  const enseignantId = Number(enseignant_id);
  const [enseignant, setEnseignant] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // 🔄 Charger l'enseignant
  useEffect(() => {
    if (!enseignantId) return;

    axios
      .get(`http://127.0.0.1:8008/api/chercher_enseignant/${enseignantId}/`)
      .then((res) => setEnseignant(res.data))
      .catch(() =>
        setError("❌ Erreur lors de la récupération de l'enseignant")
      );
  }, [enseignantId]);

  // 🗑️ Supprimer
  const handleDelete = async () => {
    try {
      await axios.delete(
        `http://127.0.0.1:8008/api/supprimer_enseignant/${enseignantId}/`
      );

      setMessage("✅ Enseignant supprimé avec succès");
      if (onDeleted) onDeleted();
    } catch (err) {
      setError("❌ Erreur lors de la suppression");
    }
    window.history.back();
  };

  return (
    <div className="supprimer-enseignant">
      <h2>Supprimer Enseignant</h2>

      {message && <p style={{ color: "green" }}>{message}</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {enseignant && (
        <p>
          Voulez-vous supprimer l'enseignant{" "}
          <strong>
            {enseignant.nom} {enseignant.prenom}
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