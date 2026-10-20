"""Consultation des statistiques agrégées CHRS10."""
from datetime import timedelta, date
import csv
from django import forms
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.http import QueryDict
from django.utils import timezone
from django.views.decorators.http import require_GET
from .statistiques import bilan, evolution_mensuelle, ventilation_repas, exploration_repas, exploration_affectations
from .models import AccordRepas, LieuHebergement


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


@require_GET
@login_required
@permission_required(('personnes.view_accompagnement', 'personnes.view_sejour',
                      'personnes.view_repasdistribue'), raise_exception=True)
def statistiques(request):
    aujourd_hui = timezone.localdate()
    initial = {'debut': aujourd_hui.replace(day=1), 'fin': aujourd_hui + timedelta(days=1)}
    periode_choisie = request.GET.get('periode', '')
    if periode_choisie in PERIODES:
        debut, fin = bornes_periode(periode_choisie, aujourd_hui)
        formulaire = PeriodeStatistiquesForm({'debut': debut.isoformat(), 'fin': fin.isoformat()})
    else:
        formulaire = PeriodeStatistiquesForm(request.GET or None, initial=initial)

    rapport = request.GET.get('rapport', 'synthese')
    if rapport not in RAPPORTS:
        rapport = 'synthese'
    service_choisi = request.GET.get('service', '')
    if service_choisi not in dict(AccordRepas.SERVICES):
        service_choisi = ''
    resultats = bilan(**formulaire.cleaned_data) if formulaire.is_valid() else None
    lieu_choisi = request.GET.get('lieu', '')
    lieux_possibles = list(LieuHebergement.objects.order_by('libelle', 'pk'))
    if lieu_choisi and not any(str(l.pk) == lieu_choisi for l in lieux_possibles):
        lieu_choisi = ''
    exploration_hebergement = []
    erreur_hebergement = ''
    if resultats is not None and rapport == 'exploration_hebergement':
        try:
            exploration_hebergement = exploration_affectations(
                **formulaire.cleaned_data, lieu=lieu_choisi)
        except ValueError as exc:
            erreur_hebergement = str(exc)
    exploration = []
    erreur_exploration = ''
    if resultats is not None and rapport == 'exploration_repas':
        try:
            exploration = exploration_repas(**formulaire.cleaned_data, service=service_choisi)
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
            writer.writerow(['mois', 'lieu', 'nuitees_affectation_theoriques'])
            for ligne in exploration_hebergement:
                writer.writerow([ligne['mois'], ligne['lieu'], ligne['nuitees']])
        elif rapport == 'exploration_repas':
            if erreur_exploration:
                return HttpResponse(erreur_exploration, status=400, content_type='text/plain; charset=utf-8')
            writer.writerow(['mois', 'service', 'quantite_distribuee'])
            for ligne in exploration:
                writer.writerow([ligne['mois'], ligne['service'], ligne['quantite']])
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
    if resultats is not None and request.GET.get('comparer') == '1':
        duree = formulaire.cleaned_data['fin'] - formulaire.cleaned_data['debut']
        comparaison = bilan(formulaire.cleaned_data['debut'] - duree,
                            formulaire.cleaned_data['debut'])
    periode = formulaire.cleaned_data if formulaire.is_valid() else {}
    return render(request, 'suivi/statistiques.html', {
        'formulaire': formulaire, 'resultats': resultats,
        'exploration_hebergement': exploration_hebergement,
        'erreur_hebergement': erreur_hebergement,
        'lieux_possibles': lieux_possibles, 'lieu_choisi': lieu_choisi,
        'exploration': exploration, 'erreur_exploration': erreur_exploration,
        'services_possibles': AccordRepas.SERVICES, 'service_choisi': service_choisi,
        'periodes': PERIODES, 'periode_choisie': periode_choisie,
        'comparaison': comparaison, 'comparer': request.GET.get('comparer') == '1',
        'rapport': rapport, 'rapports': RAPPORTS,
        'evolution': evolution, 'services': services, 'erreur_evolution': erreur_evolution,
        'debut_iso': periode['debut'].isoformat() if periode else '',
        'fin_iso': periode['fin'].isoformat() if periode else '',
    })
