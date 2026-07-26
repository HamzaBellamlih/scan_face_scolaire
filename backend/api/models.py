from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

class Etudiant(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    date_naissance = models.DateField()
    lieu_naissance = models.CharField(max_length=150)
    niveau_etude = models.CharField(max_length=100)
    classe = models.CharField(max_length=100)
    telephone = models.CharField(max_length=15)
    photo = models.ImageField(upload_to="etudiants/", null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            # Récupérer le dernier ID et ajouter 1
            last_etudiant = Etudiant.objects.all().order_by('id').last()
            self.id = (last_etudiant.id + 1) if last_etudiant else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"L'étudiant({self.id}) {self.photo} : {self.prenom} {self.nom}({self.date_naissance},{self.lieu_naissance}) Numero: {self.telephone} Email : {self.email} Niveau : {self.niveau_etude} Classe : {self.classe}"

class Enseignant(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    date_naissance = models.DateField()
    lieu_naissance = models.CharField(max_length=150)
    date_creation = models.DateTimeField(auto_now_add=True)
    matiere = models.CharField(max_length=100)
    telephone = models.CharField(max_length=15)
    photo = models.ImageField(upload_to="enseignants/", null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            # Récupérer le dernier ID et ajouter 1
            last_enseignant = Enseignant.objects.all().order_by('id').last()
            self.id = (last_enseignant.id + 1) if last_enseignant else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"L'enseignant({self.id}) {self.photo} : {self.prenom} {self.nom}({self.date_naissance},{self.lieu_naissance}) Numero: {self.telephone} Email : {self.email} Matière : {self.matiere}"

class Personne(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    date_naissance = models.DateField()
    lieu_naissance = models.CharField(max_length=150)
    telephone = models.CharField(max_length=15)
    photo = models.ImageField(upload_to="personnes/", null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            # Récupérer le dernier ID et ajouter 1
            last_personne = Personne.objects.all().order_by('id').last()
            self.id = (last_personne.id + 1) if last_personne else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"La personne({self.id}) {self.photo} : {self.prenom} {self.nom}({self.date_naissance},{self.lieu_naissance}) Numero: {self.telephone} Email : {self.email}"

class ScanHistory(models.Model):
    ROLE_CHOICES = (
        ("etudiant", "Étudiant"),
        ("enseignant", "Enseignant"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    personne_id = models.IntegerField()  # ID étudiant ou enseignant
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_scan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} - {self.nom} {self.prenom} - {self.date_scan}"

from django.db import models
from django.utils import timezone

class AssuranceEtudiant(models.Model):
    etudiant = models.ForeignKey(
        'Etudiant',
        on_delete=models.CASCADE,
        related_name='paiements_assurance'
    )
    montant_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Montant total de l'assurance"
    )
    montant_paye = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Montant déjà payé"
    )
    montant_restant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Montant restant à payer"
    )
    date_paiement = models.DateTimeField(
        default=timezone.now,
        help_text="Date du paiement"
    )
    statut = models.CharField(
        max_length=20,
        choices=[
            ('complet', 'Payé complètement'),
            ('partiel', 'Payé partiellement'),
            ('impaye', 'Non payé')
        ],
        default='impaye'
    )

    class Meta:
        verbose_name = "Assurance Étudiant"
        verbose_name_plural = "Assurances Étudiants"
        ordering = ['-date_paiement']

    def __str__(self):
        return f"Assurance {self.etudiant.prenom} {self.etudiant.nom} - {self.date_paiement.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        # Calculer automatiquement le statut
        if self.montant_restant == 0:
            self.statut = 'complet'
        elif self.montant_paye > 0:
            self.statut = 'partiel'
        else:
            self.statut = 'impaye'
        super().save(*args, **kwargs)

class AssuranceEnseignant(models.Model):
    enseignant = models.ForeignKey(
        'Enseignant',
        on_delete=models.CASCADE,
        related_name='paiements_assurance'
    )
    montant_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Montant total de l'assurance"
    )
    montant_paye = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Montant déjà payé"
    )
    montant_restant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Montant restant à payer"
    )
    date_paiement = models.DateTimeField(
        default=timezone.now,
        help_text="Date du paiement"
    )
    statut = models.CharField(
        max_length=20,
        choices=[
            ('complet', 'Payé complètement'),
            ('partiel', 'Payé partiellement'),
            ('impaye', 'Non payé')
        ],
        default='impaye'
    )

    class Meta:
        verbose_name = "Assurance Enseignant"
        verbose_name_plural = "Assurances Enseignants"
        ordering = ['-date_paiement']

    def __str__(self):
        return f"Assurance {self.enseignant.prenom} {self.enseignant.nom} - {self.date_paiement.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        # Calculer automatiquement le statut
        if self.montant_restant == 0:
            self.statut = 'complet'
        elif self.montant_paye > 0:
            self.statut = 'partiel'
        else:
            self.statut = 'impaye'
        super().save(*args, **kwargs)

class PaiementEnseignant(models.Model):
    enseignant = models.ForeignKey(
        'Enseignant',
        on_delete=models.CASCADE,
        related_name='paiements_salaire'
    )
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Montant payé"
    )
    salaire_prevu = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Salaire prévu"
    )
    salaire_restant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Salaire restant après paiement"
    )
    mois = models.IntegerField(
        null=True, blank=True,
        help_text="Mois du paiement (1-12)"
    )
    annee = models.IntegerField(
        null=True, blank=True,
        help_text="Année du paiement"
    )
    date_paiement = models.DateTimeField(
        default=timezone.now,
        help_text="Date du paiement"
    )

    class Meta:
        verbose_name = "Paiement Enseignant"
        verbose_name_plural = "Paiements Enseignants"
        ordering = ['-date_paiement']

    def __str__(self):
        return f"Paiement {self.enseignant.prenom} {self.enseignant.nom} - {self.date_paiement.strftime('%Y-%m-%d')} - Montant: {self.montant}"

class Absence(models.Model):
    etudiant = models.ForeignKey(
        'Etudiant',
        on_delete=models.CASCADE,
        related_name='absences'
    )
    date = models.DateField()
    matiere = models.CharField(max_length=100)
    type_absence = models.CharField(max_length=20, choices=[('absence', 'Absence'), ('retard', 'Retard'), ('present', 'Présent')])

class Note(models.Model):
    TYPE_EXAMEN_CHOICES = [
        ('devoir',     'Devoir'),
        ('examen',     'Examen'),
        ('rattrapage', 'Rattrapage'),
        ('tp',         'TP'),
    ]
    SEMESTRE_CHOICES = [(1, 'Semestre 1'), (2, 'Semestre 2')]

    enseignant  = models.ForeignKey(
        Enseignant, on_delete=models.CASCADE,
        related_name='notes_saisies'
    )
    etudiant    = models.ForeignKey(
        Etudiant, on_delete=models.CASCADE,
        related_name='notes'
    )
    matiere     = models.CharField(max_length=100)
    note        = models.DecimalField(max_digits=5, decimal_places=2)
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    type_examen = models.CharField(max_length=20, choices=TYPE_EXAMEN_CHOICES, default='devoir')
    semestre    = models.IntegerField(choices=SEMESTRE_CHOICES, default=1)
    date_saisie = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        ordering = ['-date_saisie']

    def __str__(self):
        return f"{self.etudiant.prenom} {self.etudiant.nom} — {self.matiere} — {self.note}/20"