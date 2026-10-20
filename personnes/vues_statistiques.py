"""Consultation des statistiques agrégées CHRS10."""
from datetime import timedelta, date
import csv
from django import forms
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import QueryDict
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from .statistiques import bilan, evolution_mensuelle, ventilation_repas, exploration_repas, exploration_affectations, regrouper_exploration, REGROUPEMENTS_EXPLORATION
from .models import AccordRepas, LieuHebergement, ModeleRapport


RAPPORTS = {
    'synthese': 'Synthèse de l’activité',
    'hebergement': 'Hébergement et nuitées',
    'repas': 'Repas distribués',
    'mensuel': 'Évolution mensuelle',
    'exploration_repas': 'Explorer les repas par mois et service',
    'exploration_hebergement': 'Explorer les nuitées par mois et lieu',
}


PERIODES = {
    'mois': 'Mois en cours',
    'mois_precedent': 'Mois précédent',
    'annee': 'Année en cours',
    'annee_precedente': 'Année précédente',
}


def bornes_periode(code, aujourd_hui):
    """Bornes civiles [début, fin[, sans dépendance à la date du serveur SQL."""
    premier_mois = aujourd_hui.replace(day=1)
    if code == 'mois':
        return premier_mois, aujourd_hui + timedelta(days=1)
    if code == 'mois_precedent':
        dernier = premier_mois - timedelta(days=1)
        return dernier.replace(day=1), premier_mois
    if code == 'annee':
        return date(aujourd_hui.year, 1, 1), aujourd_hui + timedelta(days=1)
    if code == 'annee_precedente':
        return date(aujourd_hui.year - 1, 1, 1), date(aujourd_hui.year, 1, 1)
    raise ValueError('Période prédéfinie inconnue')


class PeriodeStatistiquesForm(forms.Form):
    debut = forms.DateField(label='Début inclus', widget=forms.DateInput(attrs={'type': 'date'}))
    fin = forms.DateField(label='Fin exclue', widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        valeurs = super().clean()
        if valeurs.get('debut') and valeurs.get('fin') and valeurs['fin'] <= valeurs['debut']:
            self.add_error('fin', 'La fin doit être postérieure au début.')
        return valeurs


# Seuls les paramètres publics et validés sont conservés ; ni données nominatives,
# ni export CSV, ni identifiants d'autres utilisateurs.
PARAMETRES_MODELE = ('rapport', 'debut', 'fin', 'service', 'lieu', 'regroupement', 'comparer')


def parametres_modele(donnees):
    periode = PeriodeStatistiquesForm(donnees)
    if not periode.is_valid():
        raise ValueError('Période invalide')
    rapport = donnees.get('rapport', 'synthese')
    if rapport not in RAPPORTS:
        raise ValueError('Rapport inconnu')
    service = donnees.get('service', '')
    if service not in dict(AccordRepas.SERVICES) and service:
        raise ValueError('Service inconnu')
    lieu = donnees.get('lieu', '')
    if lieu and (not lieu.isdigit() or not LieuHebergement.objects.filter(pk=lieu).exists()):
        raise ValueError('Lieu inconnu')
    regroupement = donnees.get('regroupement', 'mois_categorie')
    if regroupement not in dict(REGROUPEMENTS_EXPLORATION):
        raise ValueError('Regroupement inconnu')
    if rapport in ('exploration_repas', 'exploration_hebergement'):
        debut, fin = periode.cleaned_data['debut'], periode.cleaned_data['fin']
        dernier = fin - timedelta(days=1)
        mois = (dernier.year - debut.year) * 12 + dernier.month - debut.month + 1
        if mois > 24:
            raise ValueError('Période trop longue')
    return {
        'rapport': rapport,
        'debut': periode.cleaned_data['debut'].isoformat(),
        'fin': periode.cleaned_data['fin'].isoformat(),
        'service': service if rapport == 'exploration_repas' else '',
        'lieu': lieu if rapport == 'exploration_hebergement' else '',
        'regroupement': regroupement,
        'comparer': '1' if donnees.get('comparer') == '1' else '',
    }


@require_POST
@login_required
@permission_required(('personnes.view_accompagnement', 'personnes.view_sejour',
                      'personnes.view_repasdistribue'), raise_exception=True)
def enregistrer_modele_rapport(request):
    nom = request.POST.get('nom', '').strip()
    if not nom or len(nom) > 100:
        return HttpResponse('Nom de rapport invalide', status=400)
    if ModeleRapport.objects.filter(auteur=request.user).count() >= 30:
        return HttpResponse('Limite de 30 modèles atteinte', status=400)
    try:
        parametres = parametres_modele(request.POST)
    except (ValueError, TypeError):
        return HttpResponse('Configuration de rapport invalide', status=400)
    ModeleRapport.objects.create(auteur=request.user, nom=nom, parametres=parametres)
    return redirect('statistiques')


@require_POST
@login_required
@permission_required(('personnes.view_accompagnement', 'personnes.view_sejour',
                      'personnes.view_repasdistribue'), raise_exception=True)
def supprimer_modele_rapport(request, pk):
    modele = get_object_or_404(ModeleRapport, pk=pk, auteur=request.user)
    modele.delete()
    return redirect('statistiques')


@require_GET
@login_required
@permission_required(('personnes.view_accompagnement', 'personnes.view_sejour',
                      'personnes.view_repasdistribue'), raise_exception=True)
def statistiques(request):
    aujourd_hui = timezone.localdate()
    initial = {'debut': aujourd_hui.replace(day=1), 'fin': aujourd_hui + timedelta(days=1)}
    modele = None
    if request.GET.get('modele'):
        modele = get_object_or_404(ModeleRapport, pk=request.GET['modele'], auteur=request.user)
    selection = modele.parametres if modele else request.GET
    periode_choisie = selection.get('periode', '')
    if periode_choisie in PERIODES:
        debut, fin = bornes_periode(periode_choisie, aujourd_hui)
        formulaire = PeriodeStatistiquesForm({'debut': debut.isoformat(), 'fin': fin.isoformat()})
    else:
        formulaire = PeriodeStatistiquesForm(selection or None, initial=initial)

    rapport = selection.get('rapport', 'synthese')
    if rapport not in RAPPORTS:
        rapport = 'synthese'
    service_choisi = selection.get('service', '')
    if service_choisi not in dict(AccordRepas.SERVICES):
        service_choisi = ''
    resultats = bilan(**formulaire.cleaned_data) if formulaire.is_valid() else None
    lieu_choisi = selection.get('lieu', '')
    lieux_possibles = list(LieuHebergement.objects.order_by('libelle', 'pk'))
    if lieu_choisi and not any(str(l.pk) == lieu_choisi for l in lieux_possibles):
        lieu_choisi = ''
    regroupement = selection.get('regroupement', 'mois_categorie')
    if regroupement not in dict(REGROUPEMENTS_EXPLORATION):
        regroupement = 'mois_categorie'
    exploration_hebergement = []
    erreur_hebergement = ''
    if resultats is not None and rapport == 'exploration_hebergement':
        try:
            exploration_hebergement = regrouper_exploration(
                exploration_affectations(**formulaire.cleaned_data, lieu=lieu_choisi),
                regroupement=regroupement, categorie='lieu', mesure='nuitees')
        except ValueError as exc:
            erreur_hebergement = str(exc)
    exploration = []
    erreur_exploration = ''
    if resultats is not None and rapport == 'exploration_repas':
        try:
            exploration = regrouper_exploration(
                exploration_repas(**formulaire.cleaned_data, service=service_choisi),
                regroupement=regroupement, categorie='service', mesure='quantite')
        except ValueError as exc:
            erreur_exploration = str(exc)
    evolution = []
    services = {}
    erreur_evolution = ''
    if resultats is not None:
        services = ventilation_repas(**formulaire.cleaned_data)
        try:
            evolution = evolution_mensuelle(**formulaire.cleaned_data)
        except ValueError as exc:
            erreur_evolution = str(exc)
    if request.GET.get('format') == 'csv' and resultats is not None:
        reponse = HttpResponse(content_type='text/csv; charset=utf-8')
        reponse['Content-Disposition'] = 'attachment; filename="statistiques-chrs.csv"'
        writer = csv.writer(reponse)
        if rapport == 'exploration_hebergement':
            if erreur_hebergement:
                return HttpResponse(erreur_hebergement, status=400, content_type='text/plain; charset=utf-8')
            colonnes = (['mois', 'lieu'] if regroupement == 'mois_categorie' else
                        ['mois'] if regroupement == 'mois' else ['lieu'])
            writer.writerow([*colonnes, 'nuitees_affectation_theoriques'])
            for ligne in exploration_hebergement:
                writer.writerow([*[ligne[cle] for cle in colonnes], ligne['nuitees']])
        elif rapport == 'exploration_repas':
            if erreur_exploration:
                return HttpResponse(erreur_exploration, status=400, content_type='text/plain; charset=utf-8')
            colonnes = (['mois', 'service'] if regroupement == 'mois_categorie' else
                        ['mois'] if regroupement == 'mois' else ['service'])
            writer.writerow([*colonnes, 'quantite_distribuee'])
            for ligne in exploration:
                writer.writerow([*[ligne[cle] for cle in colonnes], ligne['quantite']])
        elif rapport == 'mensuel':
            if erreur_evolution:
                return HttpResponse(erreur_evolution, status=400, content_type='text/plain; charset=utf-8')
            colonnes = ('mois', 'debut', 'fin', 'admissions', 'sorties',
                        'nuitees_theoriques', 'repas_distribues')
            writer.writerow(colonnes)
            for ligne in evolution:
                writer.writerow([ligne[cle] for cle in colonnes])
        elif rapport == 'repas':
            writer.writerow(['debut_inclus', 'fin_exclue', 'service', 'quantite_distribuee'])
            for service, quantite in services.items():
                writer.writerow([formulaire.cleaned_data['debut'].isoformat(),
                                 formulaire.cleaned_data['fin'].isoformat(), service, quantite])
        else:
            writer.writerow(['debut_inclus', 'fin_exclue', 'indicateur', 'valeur'])
            indicateurs = resultats if rapport == 'synthese' else {
                cle: resultats[cle] for cle in (
                    'personnes_avec_sejour', 'sejours', 'admissions', 'sorties',
                    'nuitees_theoriques', 'nuits_distinctes',
                    'nuits_hors_absences_declarees')}
            for indicateur, valeur in indicateurs.items():
                writer.writerow([formulaire.cleaned_data['debut'].isoformat(),
                                 formulaire.cleaned_data['fin'].isoformat(), indicateur, valeur])
        return reponse
    comparaison = None
    if resultats is not None and selection.get('comparer') == '1':
        duree = formulaire.cleaned_data['fin'] - formulaire.cleaned_data['debut']
        comparaison = bilan(formulaire.cleaned_data['debut'] - duree,
                            formulaire.cleaned_data['debut'])
    periode = formulaire.cleaned_data if formulaire.is_valid() else {}
    return render(request, 'suivi/statistiques.html', {
        'formulaire': formulaire, 'resultats': resultats,
        'modeles_rapports': ModeleRapport.objects.filter(auteur=request.user),
        'regroupement': regroupement, 'regroupements': REGROUPEMENTS_EXPLORATION,
        'exploration_hebergement': exploration_hebergement,
        'erreur_hebergement': erreur_hebergement,
        'lieux_possibles': lieux_possibles, 'lieu_choisi': lieu_choisi,
        'exploration': exploration, 'erreur_exploration': erreur_exploration,
        'services_possibles': AccordRepas.SERVICES, 'service_choisi': service_choisi,
        'periodes': PERIODES, 'periode_choisie': periode_choisie,
        'comparaison': comparaison, 'comparer': selection.get('comparer') == '1',
        'rapport': rapport, 'rapports': RAPPORTS,
        'evolution': evolution, 'services': services, 'erreur_evolution': erreur_evolution,
        'debut_iso': periode['debut'].isoformat() if periode else '',
        'fin_iso': periode['fin'].isoformat() if periode else '',
    })
