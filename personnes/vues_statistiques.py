from django.template.response import TemplateResponse
from django.urls import reverse
"""Consultation des statistiques agrégées CHRS10."""
from datetime import timedelta, date
import csv
from django import forms
from .champs_saisie import FormulaireMetier
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import QueryDict
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from .statistiques import bilan, evolution_mensuelle, ventilation_repas, exploration_repas, exploration_affectations, regrouper_exploration, REGROUPEMENTS_EXPLORATION
from .models import AccordRepas, LieuHebergement, ModeleRapport
from . import rapports_metier as metier


RAPPORTS = {
    'mouvements': 'Mouvements et durées des séjours sortis',
    'ages': 'Âges calculables et précision des naissances',
    'synthese': 'Synthèse de l’activité',
    'hebergement': 'Hébergement et nuitées',
    'repas': 'Repas distribués',
    'mensuel': 'Évolution mensuelle',
    'exploration_repas': 'Explorer les repas par mois et service',
    'exploration_hebergement': 'Explorer les nuitées par mois et lieu',
}


from .periodes_rapports import PERIODES,bornes_periode


class PeriodeStatistiquesForm(FormulaireMetier):
    debut = forms.DateField(label='Début inclus', widget=forms.DateInput(attrs={'type': 'date'}))
    fin = forms.DateField(label='Fin exclue', widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        valeurs = super().clean()
        if valeurs.get('debut') and valeurs.get('fin') and valeurs['fin'] <= valeurs['debut']:
            self.add_error('fin', 'La fin doit être postérieure au début.')
        return valeurs


# Seuls les paramètres publics et validés sont conservés ; ni données nominatives,
# ni export CSV, ni identifiants d'autres utilisateurs.
PARAMETRES_MODELE = ('export_prioritaire', 'rapport', 'debut', 'fin', 'periode', 'service', 'lieu', 'regroupement', 'comparer', 'decalage_debut', 'decalage_fin')


def parametres_modele(donnees):
    from .presentation_exports import valider
    from django.core.exceptions import ValidationError
    try:preference=valider(donnees.get('export_prioritaire',''))
    except ValidationError as erreur:raise ValueError(str(erreur))
    code_periode = donnees.get('periode', '')
    if code_periode and code_periode not in PERIODES:
        raise ValueError('Période relative inconnue')
    if code_periode:
        debut, fin = bornes_periode(code_periode, timezone.localdate(),decalage_debut=donnees.get('decalage_debut',-6),decalage_fin=donnees.get('decalage_fin',1))
        periode = PeriodeStatistiquesForm({'debut': debut.isoformat(), 'fin': fin.isoformat()})
    else:
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
        'export_prioritaire': preference,
        'rapport': rapport,
        'debut': periode.cleaned_data['debut'].isoformat(),
        'fin': periode.cleaned_data['fin'].isoformat(),
        'periode': code_periode,
        'decalage_debut':str(donnees.get('decalage_debut',-6)), 'decalage_fin':str(donnees.get('decalage_fin',1)),
        'service': service if rapport == 'exploration_repas' else '',
        'lieu': lieu if rapport == 'exploration_hebergement' else '',
        'regroupement': regroupement,
        'comparer': '1' if donnees.get('comparer') == '1' and rapport != 'ages' else '',
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
    from .modeles_personnels import exiger
    exiger(request.user,modele)
    modele.delete()
    return redirect('statistiques')


@require_GET
@login_required
@permission_required(('personnes.view_accompagnement', 'personnes.view_sejour',
                      'personnes.view_repasdistribue'), raise_exception=True)
def statistiques(request):
    if not request.GET:return redirect('dossiers:rapports_accueil')
    aujourd_hui = timezone.localdate()
    initial = {'debut': aujourd_hui.replace(day=1), 'fin': aujourd_hui + timedelta(days=1)}
    modele = None
    if request.GET.get('modele'):
        modele = get_object_or_404(ModeleRapport, pk=request.GET['modele'], auteur=request.user)
    if modele and modele.parametres.get('exploration'):
        return redirect(reverse('dossiers:explorer')+'?modele='+str(modele.pk))
    from . import modeles_personnels as gestion
    cible=modele
    if not cible and request.GET.get('modele_cible'):
        cible=get_object_or_404(ModeleRapport,pk=request.GET['modele_cible'],auteur=request.user)
    attendu=request.GET.get('attendu_modele') or (gestion.jeton(request.user,cible) if cible else '')
    if modele and modele.parametres.get('_rapport_source'):
        from .catalogue_rapports import ouvrir
        return redirect(ouvrir(modele))
    selection = modele.parametres.copy() if modele else request.GET.copy()
    selection.setdefault('debut',initial['debut'].isoformat());selection.setdefault('fin',initial['fin'].isoformat())
    periode_choisie = selection.get('periode', '')
    if periode_choisie in PERIODES:
        try:
            debut, fin = bornes_periode(periode_choisie, aujourd_hui,decalage_debut=selection.get('decalage_debut',-6),decalage_fin=selection.get('decalage_fin',1))
            formulaire = PeriodeStatistiquesForm({'debut': debut.isoformat(), 'fin': fin.isoformat()})
        except (ValueError,TypeError,OverflowError):
            formulaire=PeriodeStatistiquesForm(selection);formulaire.is_valid();formulaire.add_error(None,'Bornes de période relative invalides.')
    else:
        formulaire = PeriodeStatistiquesForm(selection or None, initial=initial)

    rapport = selection.get('rapport', 'synthese')
    if rapport not in RAPPORTS:
        rapport = 'synthese'
    if rapport == 'ages' and not request.user.has_perm('personnes.view_personne'):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    lecture_lieux = request.user.has_perms(['personnes.view_affectation', 'personnes.view_lieuhebergement'])
    if rapport == 'exploration_hebergement' and not lecture_lieux:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    service_choisi = selection.get('service', '')
    if service_choisi not in dict(AccordRepas.SERVICES):
        service_choisi = ''
    resultats = None
    if formulaire.is_valid():
        resultats = {} if rapport in ('mouvements', 'ages') else bilan(**formulaire.cleaned_data)
    lieu_choisi = selection.get('lieu', '')
    lieux_possibles = list(LieuHebergement.objects.order_by('libelle', 'pk')) if lecture_lieux else []
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
    if resultats is not None and rapport not in ('mouvements', 'ages'):
        services = ventilation_repas(**formulaire.cleaned_data)
        try:
            evolution = evolution_mensuelle(**formulaire.cleaned_data)
        except ValueError as exc:
            erreur_evolution = str(exc)
    mouvements = metier.mouvements(**formulaire.cleaned_data) if resultats is not None and rapport == 'mouvements' else None
    ages = metier.ages(**formulaire.cleaned_data) if resultats is not None and rapport == 'ages' else None
    if request.GET.get('format') == 'csv' and resultats is not None:
        reponse = HttpResponse(content_type='text/csv; charset=utf-8')
        reponse['Content-Disposition'] = 'attachment; filename="statistiques-chrs.csv"'
        writer = csv.writer(reponse)
        if rapport == 'mouvements':
            writer.writerow(['debut_inclus', 'fin_exclue', 'indicateur', 'valeur'])
            for code, valeur in mouvements.items():
                writer.writerow([formulaire.cleaned_data['debut'].isoformat(), formulaire.cleaned_data['fin'].isoformat(), code, valeur])
        elif rapport == 'ages':
            reference, comptes, qualite = ages
            writer.writerow(['debut_inclus', 'fin_exclue', 'date_reference', 'nature', 'valeur', 'effectif'])
            for code, compte in sorted(comptes.items()):
                writer.writerow([formulaire.cleaned_data['debut'].isoformat(), formulaire.cleaned_data['fin'].isoformat(), reference.isoformat(), 'age_exact', code, compte])
            for code, compte in qualite.items():
                writer.writerow([formulaire.cleaned_data['debut'].isoformat(), formulaire.cleaned_data['fin'].isoformat(), reference.isoformat(), 'naissance', code, compte])
        elif rapport == 'exploration_hebergement':
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
    mouvements_precedents = None
    erreur_comparaison = ''
    if resultats is not None and selection.get('comparer') == '1' and rapport != 'ages':
        duree = formulaire.cleaned_data['fin'] - formulaire.cleaned_data['debut']
        try:
            precedent = formulaire.cleaned_data['debut'] - duree
        except OverflowError:
            erreur_comparaison = 'La période précédente dépasserait les dates disponibles. La période choisie reste affichée.'
        else:
            if rapport == 'mouvements':
                mouvements_precedents = metier.mouvements(precedent, formulaire.cleaned_data['debut'])
            else:
                comparaison = bilan(precedent, formulaire.cleaned_data['debut'])
    periode = formulaire.cleaned_data if formulaire.is_valid() else {}
    return TemplateResponse(request, 'suivi/statistiques.html', {
        'formulaire': formulaire, 'resultats': resultats,
        'modeles_rapports': [x for x in ModeleRapport.objects.filter(auteur=request.user) if not x.parametres.get('exploration')],
        'modele_actif': modele, 'modele_gestion':cible,'attendu_modele':attendu,
        'regroupement': regroupement, 'regroupements': REGROUPEMENTS_EXPLORATION,
        'exploration_hebergement': exploration_hebergement,
        'erreur_hebergement': erreur_hebergement,
        'lieux_possibles': lieux_possibles, 'lieu_choisi': lieu_choisi,
        'exploration': exploration, 'erreur_exploration': erreur_exploration,
        'services_possibles': AccordRepas.SERVICES, 'service_choisi': service_choisi,
        'periodes': PERIODES, 'periode_choisie': periode_choisie,
        'erreur_comparaison': erreur_comparaison, 'comparaison': comparaison, 'comparer': selection.get('comparer') == '1' and rapport != 'ages',
        'titre_rapport':RAPPORTS[rapport], 'rapport': rapport, 'rapports': {code: label for code, label in RAPPORTS.items() if (not getattr(request,'acteurs_statistiques_regroupees',False) or code in ('synthese','hebergement','repas','mensuel')) and (code != 'ages' or request.user.has_perm('personnes.view_personne')) and (code != 'exploration_hebergement' or lecture_lieux)},
        'mouvements': [(code, metier.LIBELLES_MOUVEMENTS[code], valeur) for code, valeur in (mouvements or {}).items()],
        'mouvements_comparaison': [(metier.LIBELLES_MOUVEMENTS[code], mouvements_precedents[code], valeur) for code, valeur in (mouvements or {}).items()] if mouvements_precedents is not None else [],
        'age_reference': ages[0] if ages else None,
        'ages': sorted(ages[1].items()) if ages else [],
        'naissances': [(metier.LIBELLES_NAISSANCES[code], valeur) for code, valeur in ages[2].items()] if ages else [],
        'evolution': evolution, 'services': services, 'erreur_evolution': erreur_evolution,
        'debut_iso': periode['debut'].isoformat() if periode else '',
        'fin_iso': periode['fin'].isoformat() if periode else '',
    })
