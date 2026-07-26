from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views

urlpatterns = [
    path("ajouter_etudiant/", views.ajouter_etudiant, name="ajouter_etudiant"),
    path('ajouter_enseignant/', views.ajouter_enseignant, name='ajouter_enseignant'),
    path('ajouter_personne/', views.ajouter_personne, name='ajouter_personne'),
    path('modifier_etudiant/<int:etudiant_id>/', views.modifier_etudiant, name='modifier_etudiant'),
    path('modifier_enseignant/<int:enseignant_id>/', views.modifier_enseignant, name='modifier_enseignant'),
    path('modifier_personne/<int:personne_id>/', views.modifier_personne, name='modifier_personne'),
    path('supprimer_etudiant/<int:etudiant_id>/', views.supprimer_etudiant, name='supprimer_etudiant'),
    path('supprimer_enseignant/<int:enseignant_id>/', views.supprimer_enseignant, name='supprimer_enseignant'),
    path('supprimer_personne/<int:personne_id>/', views.supprimer_personne, name='supprimer_personne'),
    path('chercher_etudiant/<int:etudiant_id>/', views.chercher_etudiant, name='chercher_etudiant'),
    path('chercher_enseignant/<int:enseignant_id>/', views.chercher_enseignant, name='chercher_enseignant'),
    path('chercher_personne/<int:personne_id>/', views.chercher_personne, name='chercher_personne'),
    path('lister_etudiants/', views.lister_etudiants, name='lister_etudiants'),
    path('lister_enseignants/', views.lister_enseignants, name='lister_enseignants'),
    path('lister_personnes/', views.lister_personnes, name='lister_personnes'),
    path("face/health/",  views.face_health,       name="face_health"),
    path("face/stats/",  views.face_stats,        name="face_stats"),
    path("face/persons/",  views.face_persons,      name="face_persons"),
    path("face/train/",  views.train_face_model,  name="face_train"),
    path("face/train/status/", views.training_status,   name="face_train_status"),
    path("face/reload/",  views.face_reload,       name="face_reload"),
    path("face/identify/",  views.scanner_face,      name="face_identify"),
    path("face/identify/etudiants/", views.scanner_face, name="face_identify_etu"),
    path("face/identify/enseignants/", views.scanner_face, name="face_identify_ens"),
    path("scanner-face/", views.scanner_face,      name="scanner_face_legacy"),
    path("face/diagnostic/", views.diagnostic_face,   name="face_diagnostic"),
    # ── ASSURANCE & PAIEMENT ──
    path('assurance_etudiant/config/', views.assurance_etudiant_config, name='assurance_etudiant_config'),
    path('assurance_enseignant/config/', views.assurance_enseignant_config, name='assurance_enseignant_config'),
    # ── AUTH ──
    path('login_enseignant/',              views.login_enseignant,    name='login_enseignant'),
    path('login_etudiant/',                views.login_etudiant,      name='login_etudiant'),

    # ── ENSEIGNANT ──
    path('enseignant/<int:enseignant_id>/', views.enseignant_detail,   name='enseignant_detail'),
    path('lister_enseignants/',            views.lister_enseignants,  name='lister_enseignants'),
    path('absences_enseignant/',           views.absences_enseignant, name='absences_enseignant'),
    path('notes_enseignant/',              views.notes_enseignant,    name='notes_enseignant'),
    path('paiement_enseignant/',           views.paiement_enseignant, name='paiement_enseignant'),
    path('assurance_enseignant/',          views.assurance_enseignant,name='assurance_enseignant'),

    # ── ETUDIANT ──
    path('etudiant/<int:etudiant_id>/',    views.etudiant_detail,        name='etudiant_detail'),
    path('lister_etudiants/',              views.lister_etudiants,    name='lister_etudiants'),
    path('notes_etudiant/',                views.notes_etudiant,      name='notes_etudiant'),
    path('absences_etudiant/',             views.absences_etudiant,   name='absences_etudiant'),
    path('assurance_etudiant/',            views.assurance_etudiant,  name='assurance_etudiant'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)