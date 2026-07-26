import React from 'react';
import './App.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Acceuil from './components/acceuil';
import Login from './components/admin/login';
import AjoutEtudiant from './components/admin/ajouter_etudiant';
import AjoutEnseignant from './components/admin/ajouter_enseignant';
import AjoutPersonne from './components/admin/ajouter_personne';
import ModificationEtudiant from './components/admin/modification_etudiant';
import ModificationEnseignant from './components/admin/modification_enseignant';
import ModificationPersonne from './components/admin/modification_personne';
import SuppresionEtudiant from './components/admin/suppression_etudiant';
import SuppresionEnseignant from './components/admin/suppression_enseignant';
import SuppresionPersonne from './components/admin/suppression_personne';
import ListeEtudiant from './components/admin/liste_etudiant';
import ListeEnseignant from './components/admin/liste_enseignant';
import ListePersonne from './components/admin/liste_personne';
import Acceuiladmin from './components/admin/acceuil';
import Search from './components/users/search';
import Face from './components/users/face_recherche';
import Acceuilclient from './components/users/acceuil';
import AcceuilAd from './components/administrateur/acceuil_ad';
import AssuranceEtud from './components/administrateur/assurance_etud';
import AssuranceEnse from './components/administrateur/assurance_ense';
import PaiementEnse from './components/administrateur/paiement_ense';
import DashboardEnseignant from './components/enseignant/Dashboard';
import DashboardEtudiant from './components/etudiant/Dashboard';
import Presences from './components/enseignant/Presences';
import Classes from './components/enseignant/MesClasses';
import NotesEnse from './components/enseignant/GestionNotes';
import NotesEtud from './components/etudiant/MesNotes';
import MesAbsences from './components/etudiant/MesAbsences';
import LoginEnseignant from './components/enseignant/LoginEnse';
import LoginEtudiant from './components/etudiant/LoginEtud';

function App() {
  return (
    <Router>
      <Routes>
        {/* Routes publiques */}
        <Route path="/" element={<Acceuil />} />
        <Route path="/login" element={<Login />} />
        <Route path="/acceuil" element={<Acceuiladmin/>} />
        <Route path="/ajout_etudiant" element={<AjoutEtudiant />} />
        <Route path="/ajout_enseignant" element={<AjoutEnseignant />} />
        <Route path="/ajout_personne" element={<AjoutPersonne />} />
        <Route path="/modification_etudiant/:etudiant_id" element={<ModificationEtudiant />} />
        <Route path="/modification_enseignant/:enseignant_id" element={<ModificationEnseignant />}/>
        <Route path="/modification_personne/:personne_id" element={<ModificationPersonne />} />
        <Route path="/supression_etudiant/:etudiant_id" element={<SuppresionEtudiant />} />
        <Route path="/supression_enseignant/:enseignant_id" element={<SuppresionEnseignant />} />
        <Route path="/supression_personne/:personne_id" element={<SuppresionPersonne />} />
        <Route path="/liste_etudiant" element={<ListeEtudiant />} />
        <Route path="/liste_enseignant" element={<ListeEnseignant />} />
        <Route path="/liste_personne" element={<ListePersonne />} />
        <Route path="/search" element={<Search />} />
        <Route path="/face_recherche" element={<Face />} />
        <Route path="/acceuil_client" element={<Acceuilclient />} />
        <Route path="/acceuil_ad" element={<AcceuilAd />} />
        <Route path="/assurance_etud" element={<AssuranceEtud />} />
        <Route path="/assurance_ense" element={<AssuranceEnse />} />
        <Route path="/paiement_ense" element={<PaiementEnse />} />
        <Route path="/DashboardEnseignant" element={<DashboardEnseignant />} />
        <Route path="/enseignant/classes" element={<Classes />} />
        <Route path="/enseignant/presences" element={<Presences />} />
        <Route path="/enseignant/notes" element={<NotesEnse />} />
        <Route path="/DashboardEtudiant" element={<DashboardEtudiant />} />
        <Route path="/etudiant/notes" element={<NotesEtud />} />
        <Route path="/etudiant/absences" element={<MesAbsences />} />
        <Route path="/login_enseignant" element={<LoginEnseignant />} />
        <Route path="/login_etudiant" element={<LoginEtudiant />} />
      </Routes>
    </Router>
  );
}

export default App;