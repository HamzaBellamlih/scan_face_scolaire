import React, { useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import "./css/suppression_personne.css";

export default function SupprimerPersonne({onDeleted }) {
  const { personne_id } = useParams();
  const personneId = Number(personne_id);
  const [personne, setPersonne] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // 🔄 Charger la personne
  useEffect(() => {
    if (!personneId) return;

    axios
      .get(`http://127.0.0.1:8008/api/chercher_personne/${personneId}/`)
      .then((res) => setPersonne(res.data))
      .catch(() =>
        setError("❌ Erreur lors de la récupération de la personne")
      );
  }, [personneId]);
  // 🗑️ Supprimer
  const handleDelete = async () => {
    try {
      await axios.delete(
        `http://127.0.0.1:8008/api/supprimer_personne/${personneId}/`
      );

      setMessage("✅ Personne supprimé avec succès");
      if (onDeleted) onDeleted();
    } catch (err) {
      setError("❌ Erreur lors de la suppression");
    }
    window.history.back();
  };

  return (
    <div>
      <h2>Supprimer Personne</h2>

      {message && <p style={{ color: "green" }}>{message}</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {personne && (
        <p>
          Voulez-vous supprimer l'personne{" "}
          <strong>
            {personne.nom} {personne.prenom}
          </strong>{" "}
          ?
        </p>
      )}

      <button onClick={handleDelete} >
        Supprimer
      </button>

      <button
        onClick={() => window.history.back()}
      >
        Retour
      </button>
    </div>
  );
}