"""Sonde CHRS1–4 des bancs de copie. Jamais un jeu public de démonstration."""
from datetime import date
from io import StringIO
from django.core.management import call_command
from personnes import models as m


def preparer(compte):
    personne = m.Personne.objects.get()
    debut = date(2026, 1, 1)
    menage = m.Menage.objects.create(libelle="Ménage fictif technique", cree_par=compte)
    m.Appartenance.objects.create(menage=menage, personne=personne, debut=debut)
    suivi = m.Accompagnement.objects.create(menage=menage, debut=debut, cree_par=compte)
    suivi.beneficiaires.add(personne)
    repas = m.AccordRepas.objects.create(accompagnement=suivi, debut=debut, service="dejeuner", cree_par=compte)
    repas.beneficiaires.add(personne)
    m.RepasDistribue.objects.create(accord=repas, beneficiaire=personne, date=debut, quantite=1, cree_par=compte)
    accord = m.AccordHebergement.objects.create(accompagnement=suivi, debut=debut, cree_par=compte)
    accord.beneficiaires.add(personne)
    sejour = m.Sejour.objects.create(accord=accord, debut=debut, cree_par=compte)
    sejour.beneficiaires.add(personne)
    lieu = m.LieuHebergement.objects.create(libelle="Lieu fictif technique", cree_par=compte)
    m.Affectation.objects.create(sejour=sejour, lieu=lieu, debut=debut)
    m.SituationSociale.objects.create(accompagnement=suivi, beneficiaire=personne, debut=debut,
        dimension="logement", valeur="hebergement", source="Sonde fictive", cree_par=compte)
    m.BilanSocial.objects.create(accompagnement=suivi, date_effet=debut, texte="Bilan fictif technique", cree_par=compte)


def signature():
    """PK, UUID, FK, M2M, mots de passe et permissions ; aucune session."""
    sortie = StringIO()
    call_command("dumpdata", "personnes", "identites.Utilisateur", indent=2, stdout=sortie)
    return sortie.getvalue()
