from datetime import date
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.contrib import messages
from .models import Accompagnement, LieuHebergement, AccordHebergement, Personne
from .forms_hebergement import AccordForm, AdmissionForm, date_champ
from . import admission, hebergement as h, dossier, accords



from .prestation_navigation import rendre as render

class AdmissionGuideeForm(AccordForm):
    objet_periode = "le séjour"
    arrivee_effectuee = forms.BooleanField(label='Arrivée déjà effectuée', required=False, initial=True,
        help_text='Décochez pour un accueil prévu. La date d’arrivée et le lieu s’appliquent seulement à une arrivée effectuée.',
        widget=forms.CheckboxInput(attrs={'data-arrivee-effectuee': '1'}))
    admission = date_champ('Date d’arrivée', False)
    lieu = forms.ModelChoiceField(LieuHebergement.objects.none(), required=False,
        label='Lieu — facultatif')
    attendu = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, acteur, simple=False, accompagnement=None, sejour=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.simple = simple
        self.edition_sejour = sejour is not None
        self.accompagnement = accompagnement
        self.peut_admettre = acteur.has_perm('personnes.add_sejour')
        if not simple and self.is_bound and forms.BooleanField(required=False).clean(self.data.get('arrivee_effectuee')) and not self.peut_admettre:
            h.exiger(acteur, 'add_sejour')
        if not self.is_bound:
            self.initial.setdefault('arrivee_effectuee', self.peut_admettre)
        if not self.peut_admettre:
            self.fields['arrivee_effectuee'].disabled = True
            self.initial['arrivee_effectuee'] = False
            self.fields['arrivee_effectuee'].help_text = 'Votre compte permet de préparer l’accueil ; une personne autorisée enregistrera l’arrivée.'
        self.champs_arrivee_visibles = simple or bool(self['arrivee_effectuee'].value())
        if not self.champs_arrivee_visibles:
            for nom in ('admission', 'lieu'):
                self.fields[nom].disabled = True
                self.initial[nom] = None
        self.fields['debut'].label = 'Début prévu inclus'
        self.fields['fin'].label = 'Fin prévue exclue — facultative'
        for nom in ('debut', 'fin', 'admission'):
            champ = self.fields[nom]
            champ.widget = forms.DateInput(format='%d/%m/%Y', attrs={
                **champ.widget.attrs, 'type': 'text', 'placeholder': 'jj/mm/aaaa', 'data-date-fr': '1',
            })
            champ.input_formats = ('%d/%m/%Y', '%Y-%m-%d')
        if simple:
            del self.fields['arrivee_effectuee'], self.fields['admission']
            self.champs_arrivee_visibles = True
            self.fields['debut'].label = 'Date d’arrivée'
        droits_lieu = ['personnes.view_affectation', 'personnes.view_lieuhebergement']
        if not self.edition_sejour:
            droits_lieu.append('personnes.add_affectation')
        if acteur.has_perms(droits_lieu):
            self.fields['lieu'].queryset = LieuHebergement.objects.all()
        else:
            del self.fields['lieu']

        from acteurs.profils_collectifs import fin_hebergement_unique
        fin_unique = fin_hebergement_unique(accompagnement) if accompagnement else False
        if fin_unique:
            self.fields['fin'].label = 'Fin du séjour (exclue)'

        if self.edition_sejour:
            self.fields['beneficiaires'].disabled = bool(
                sejour.origine_collective_id or hasattr(sejour, 'individualisation')
            )
            self.fields['fin'].label = 'Fin du séjour (exclue)'
            if sejour.fin is None and not fin_unique:
                self.fields['fin'].help_text = 'Une date future fixe la fin prévue, sans enregistrer de départ.'
            if 'lieu' in self.fields:
                affectations = list(sejour.affectations.order_by('debut', 'pk')[:2])
                champ = self.fields['lieu']
                if len(affectations) == 1:
                    self.initial['lieu'] = affectations[0].lieu_id
                    champ.required = True
                champ.disabled = len(affectations) > 1 or not acteur.has_perm(
                    'personnes.change_affectation' if affectations else 'personnes.add_affectation'
                )


    def clean(self):
        donnees = super().clean()
        debut, fin = donnees.get('debut'), donnees.get('fin')
        if debut and fin and fin <= debut:
            self.add_error('fin', 'La date de fin du séjour doit suivre sa date de début.')
        if self.edition_sejour:
            for nom in ('beneficiaires', 'lieu'):
                if nom in self.fields and self.fields[nom].disabled:
                    donnees.pop(nom, None)
            return donnees
        if self.simple:
            donnees.update(arrivee_effectuee=True, admission=donnees.get('debut'))
        if donnees.get('arrivee_effectuee') and not donnees.get('admission'):
            self.add_error('admission', 'Indiquez la date de l’arrivée effectuée.')
        return donnees


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
def accueillir(request, pk):
    h.droit(request.user, 'add_accordhebergement')
    a = get_object_or_404(Accompagnement.objects.select_related('menage'), pk=pk)
    navigation = dossier.lire(request, a)
    date_contexte = navigation.get('dossier_valeurs', {}).get('date_service')
    jour = date.fromisoformat(date_contexte) if date_contexte else timezone.localdate()
    fin = min(a.fin_prevue, a.fin) if a.fin_prevue and a.fin else a.fin or a.fin_prevue
    debut = max(a.debut, jour)
    from acteurs.profils_collectifs import parcours_simple
    simple = parcours_simple(a, 'hebergement') and request.user.has_perm('personnes.add_sejour')
    form = AdmissionGuideeForm(request.POST if request.method == 'POST' else None,
        acteur=request.user, simple=simple, accompagnement=a, beneficiaires=a.beneficiaires.all(), initial={'debut': debut, 'fin': fin if fin and fin > debut else None,
            'admission': debut, 'beneficiaires': list(a.beneficiaires.values_list('pk', flat=True)),
            'attendu': admission.jeton(a)})
    from .validation_prestations import autoriser_enregistrement, diagnostic
    if request.method == 'POST' and request.headers.get('X-Verifier-Prestation') == '1':
        return diagnostic(form, a, request=request, proposer_nouvelle_prise=True)
    statut = 200
    if request.method == 'POST' and form.is_valid() and autoriser_enregistrement(request, form, a, proposer_nouvelle_prise=True):
        try:
            nouvelle = getattr(form, 'nouvelle_prise_confirmee', False)
            accord = admission.accueillir(request.user, a, prise_confirmee=form.prise_confirmee, nouvelle_prise=nouvelle, **form.cleaned_data)
        except ValidationError as erreur:
            form.add_error(None, 'Aucun accord, séjour ou lieu d’affectation n’a été enregistré. ' + ' '.join(erreur.messages))
            statut = 409
        except OperationalError:
            form.add_error(None, 'Écriture non confirmée. Rechargez l’accompagnement avant de réessayer.')
            statut = 409
        else:
            messages.success(request, 'Arrivée enregistrée.' if form.cleaned_data['arrivee_effectuee'] else 'Séjour prévu ; arrivée à confirmer.')
            if nouvelle:
                return redirect(dossier.pour_prise(request, accord.accompagnement, 'menage', a.menage_id, {})['retour_dossier'])
            return redirect(navigation['retour_dossier']) if navigation else redirect('suivi:accord_hebergement', pk=accord.pk)
    return render(request, 'hebergement/admission_guidee.html', {**navigation, 'accompagnement': a, 'form': form}, status=statut)


class ArriveePrevueForm(AdmissionForm):
    attendu = forms.CharField(widget=forms.HiddenInput)
    lieu = forms.ModelChoiceField(LieuHebergement.objects.none(), required=False, label='Premier lieu — facultatif')

    def __init__(self, *args, acteur, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['debut'].label = 'Date d’arrivée'
        if acteur.has_perms(['personnes.add_affectation', 'personnes.view_affectation', 'personnes.view_lieuhebergement']):
            self.fields['lieu'].queryset = LieuHebergement.objects.all()
        else:
            del self.fields['lieu']


@never_cache
@require_http_methods(['GET', 'POST'])
@login_required
def arriver(request, pk):
    from django.urls import reverse
    h.droit(request.user, 'add_sejour')
    accord = get_object_or_404(AccordHebergement.objects.select_related('accompagnement'), pk=pk)
    if accord.annule_le:
        from django.http import HttpResponse
        return HttpResponse('Cet hébergement est annulé ; aucune arrivée ne peut être enregistrée.', status=409)
    a = accord.accompagnement
    navigation = dossier.lire(request, a)
    # Le jeton est lu avant les bénéficiaires proposés ; toute mutation ultérieure sera refusée.
    attendu = accords.jeton(accord)
    beneficiaires = accord.beneficiaires.exclude(pk__in=accord.sejours.non_annules().filter(beneficiaires__isnull=False).values('beneficiaires'))
    vue = navigation.get('dossier_valeurs', {}).get('vue', {})
    if vue.get('nature') == 'personne':
        beneficiaires = beneficiaires.filter(pk=vue['pk'])
    date_contexte = navigation.get('dossier_valeurs', {}).get('date_service')
    jour = date.fromisoformat(date_contexte) if date_contexte else timezone.localdate()
    form = ArriveePrevueForm(request.POST if request.method == 'POST' else None, acteur=request.user,
        beneficiaires=beneficiaires, initial={'attendu': attendu, 'debut': max(accord.debut, jour),
            'beneficiaires': list(beneficiaires.values_list('pk', flat=True))})
    statut = 200
    if request.method == 'POST' and form.is_valid():
        try:
            sejours = admission.enregistrer_arrivee(request.user, accord, **form.cleaned_data)
        except ValidationError as erreur:
            form.add_error(None, ' '.join(erreur.messages))
            statut = 409
        except OperationalError:
            form.add_error(None, 'Écriture non confirmée. Rechargez la prise en charge avant de réessayer.')
            statut = 409
        else:
            messages.success(request, 'Arrivée enregistrée.')
            if vue:
                params = {**vue, 'sejour': str(sejours[0].pk), 'prevision': ''}
                signer = dossier.pour_prise if vue.get('ecran') == 'prise' else dossier.pour_vue
                return redirect(signer(request, a, vue['nature'], vue['pk'], params)['retour_dossier'])
            return redirect('suivi:accord_hebergement', pk=accord.pk)
    return render(request, 'hebergement/arrivee_prevue.html', {**navigation, 'accord': accord, 'form': form,
        'retour': navigation.get('retour_dossier') or reverse('suivi:accord_hebergement', args=[accord.pk])}, status=statut)
