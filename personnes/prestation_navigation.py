"""NAV7 : présentation locale, jamais une nouvelle autorisation métier."""
from copy import copy
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlencode, urlsplit, parse_qsl, urljoin
from django.http import Http404, HttpResponseRedirect, QueryDict
from django.utils.datastructures import MultiValueDict
from django.shortcuts import render as django_render, get_object_or_404
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import resolve, reverse, Resolver404, get_script_prefix
from django.utils.safestring import mark_safe
from . import models as m, dossier


def rendre(request, template_name, context=None, **kwargs):
    if getattr(request, '_prestation_capture', False):
        return TemplateResponse(request, template_name, context or {}, **kwargs)
    return django_render(request, template_name, context, **kwargs)


def adresse(context, cle='', operation='', impression=False):
    params = dict(context['parametres_prestations'])
    if cle: params['prestation'] = cle
    if operation: params['operation'] = operation
    if impression: params['imprimer'] = '1'
    return reverse('dossiers:prise', args=[context['nature'], context['objet'].pk, context['prise'].pk]) + '?' + urlencode(params) + ('#prestation-'+cle.replace(':','-') if cle else '')


def cible(context, cle):
    cache = context.get('_prestation_cibles')
    if cache is None:
        cache = {}; context['_prestation_cibles'] = cache
    if cle in cache: return cache[cle]
    genre, sep, identifiant = cle.partition(':')
    if not sep: raise Http404
    if genre == 'nouveau':
        if identifiant not in ('commun_hebergement','commun_restauration','hebergement', 'repas', 'services_repas', *[x[0] for x in m.TypeAide.NATURES]): raise Http404
        return genre, identifiant
    if genre == 'commun':
        from .prestations_presentation import initialiser
        initialiser(context)
        objet=context['prestations_nav'].get(identifiant)
        if not objet:raise Http404
        return genre,objet
    if genre == 'sejour': objets = context['sejours_dossier'] + list(context['arrivees_annulees'])
    elif genre == 'hebergement': objets = context['hebergements_prevus'] + context['accords_annules_sans_sejour'] + [s.accord for s in context['sejours_dossier']]
    elif genre == 'repas': objets = context['accords_repas']
    elif genre in dossier.CLES_AIDES:
        objets = [a for a in context['prestations_aides_visibles'] if a.nature == genre[5:]]
    else: raise Http404
    objet = next((x for x in objets if str(x.pk) == identifiant), None)
    if objet is None: raise Http404
    cache[cle] = (genre, objet)
    return genre, objet


def consultation(genre, objet):
    if genre=='commun':return reverse('dossiers:collectif_action',args=['prise',objet.accompagnement_id,'consultation'])+'?'+urlencode({'pk':objet.pk})
    if genre == 'sejour': return reverse('suivi:accord_hebergement', args=[objet.accord_id])
    if genre == 'hebergement': return reverse('suivi:accord_hebergement', args=[objet.pk])
    if genre == 'repas': return reverse('suivi:accord_repas', args=[objet.pk])
    return reverse('dossiers:aide', args=[objet.pk])


def chemin_interne(chemin):
    # reverse() inclut SCRIPT_NAME, resolve() attend le seul PATH_INFO.
    prefixe = get_script_prefix().rstrip('/')
    if prefixe and chemin.startswith(prefixe+'/'): chemin = chemin[len(prefixe):]
    return chemin


def resoudre(chemin):
    return resolve(chemin_interne(chemin))


def autoriser_operation(context, cle, valeur):
    """Liste fermée, avec contrôle d'appartenance de chaque cible et sous-objet.

    Les vues appelées conservent ensuite TOUS leurs contrôles de droits et CAS.
    """
    genre, objet = cible(context, cle)
    url = urlsplit(valeur)
    if url.scheme or url.netloc: raise Http404
    try: match = resoudre(url.path)
    except Resolver404: raise Http404
    nom, kw = match.view_name, match.kwargs
    pk = str(kw.get('pk', ''))
    if genre=='commun' or genre=='nouveau' and objet.startswith('commun_'):
        query=dict(parse_qsl(url.query))
        if nom!='dossiers:collectif_action' or kw.get('cible')!='prise' or str(kw.get('pk'))!=str(context['prise'].pk):raise Http404
        if genre=='commun':
            if query.get('pk')!=str(objet.pk) or kw.get('action') not in ('consultation','correction','prolongation','depart','annulation','lieu','absence','retour','annuler_mouvement'):raise Http404
        elif kw.get('action')!='creation' or query.get('pk') or query.get('nature')!=objet[7:]:raise Http404
        return match,query
    if genre == 'nouveau':
        if objet in ('hebergement','repas','services_repas'):
            ok = nom == 'dossiers:nouveau' and str(kw.get('pk')) == str(context['objet'].pk) and kw.get('nature') == context['nature'] and kw.get('prestation') == objet
        else:
            ok = nom == 'dossiers:aide_accorder' and pk == str(context['prise'].pk) and kw.get('nature') == objet
        if not ok: raise Http404
        return match, dict(parse_qsl(url.query))
    accord = objet.accord if genre == 'sejour' else objet
    if nom in ('suivi:accord_hebergement','suivi:accord_repas','dossiers:aide'):
        if url.path != consultation(genre, objet): raise Http404
    elif genre in ('sejour','hebergement') and nom in ('suivi:prolonger_accord','suivi:annuler_accord','suivi:admettre','suivi:arrivee_prevue','suivi:selection_sejours'):
        if pk != str(accord.pk) or kw.get('nature','hebergement') != 'hebergement': raise Http404
    elif genre == 'sejour' and nom in ('suivi:affecter','suivi:absence','suivi:sortir','dossiers:annuler_arrivee','dossiers:individualiser_sejour'):
        if pk != str(objet.pk): raise Http404
    elif genre == 'sejour' and nom in ('suivi:changer_lieu','suivi:clore_affectation','suivi:clore_absence'):
        relation = objet.absences if nom == 'suivi:clore_absence' else objet.affectations
        get_object_or_404(relation, pk=kw['pk'])
    elif genre == 'repas' and nom in ('suivi:distribuer_repas','suivi:prolonger_accord','suivi:annuler_accord','dossiers:corriger_service_repas'):
        if pk != str(objet.pk) or kw.get('nature','repas') != 'repas': raise Http404
    elif genre == 'repas' and nom in ('suivi:annuler_repas','dossiers:corriger_distribution'):
        get_object_or_404(objet.realisations, pk=kw['pk'])
    elif genre in dossier.CLES_AIDES and nom in ('dossiers:aide_pdf','dossiers:aide_remettre','dossiers:aide_corriger','dossiers:aide_prolonger','dossiers:aide_annuler','dossiers:aide_remise_corriger','dossiers:aide_remise_annuler','dossiers:aide_usage'):
        if pk != str(objet.pk): raise Http404
        if 'remise_pk' in kw: get_object_or_404(objet.remises, pk=kw['remise_pk'])
    elif nom == 'suivi:corriger_saisie':
        nature = kw.get('nature')
        attendus = {'accordhebergement': str(accord.pk)} if genre in ('sejour','hebergement') else {'accordrepas': str(objet.pk)} if genre == 'repas' else {}
        if genre == 'sejour':
            attendus['sejour'] = str(objet.pk)
            if nature in ('affectation','absence'):
                get_object_or_404(objet.affectations if nature == 'affectation' else objet.absences, pk=kw['pk'])
                attendus[nature] = pk
        if attendus.get(nature) != pk: raise Http404
    elif nom == 'suivi:notes':
        attendus = {'accord_hebergement': str(accord.pk)} if genre in ('sejour','hebergement') else {'accord_repas': str(objet.pk)} if genre == 'repas' else {'accord_aide':str(objet.pk)}
        if genre == 'sejour': attendus['sejour'] = str(objet.pk)
        if attendus.get(kw.get('nature')) != pk: raise Http404
    elif nom == 'suivi:cahier':
        query = dict(parse_qsl(url.query))
        attendus = {'hebergement': str(accord.pk)} if genre in ('sejour','hebergement') else {'repas': str(objet.pk)} if genre == 'repas' else {'aide':str(objet.pk)}
        if genre == 'sejour': attendus['sejour'] = str(objet.pk)
        if attendus.get(query.get('lia_cible')) != query.get('lia_id'): raise Http404
    elif nom in ('dossiers:financement','dossiers:financement_calcul','dossiers:financement_emission'):
        nature = 'hebergement' if genre in ('sejour','hebergement') else 'repas' if genre == 'repas' else 'aide'
        if pk != str(accord.pk) or kw.get('nature') != nature: raise Http404
    elif nom in ('suivi:corriger_contribution','dossiers:contribution_annuler'):
        if kw.get('nature') != 'note': raise Http404
        note = get_object_or_404(m.NotePartagee,pk=kw['pk'])
        proprietaires = [('accord_hebergement',accord)] if genre in ('sejour','hebergement') else [('accord_repas',objet)] if genre == 'repas' else [('accord_aide',objet)]
        if genre == 'sejour': proprietaires.append(('sejour',objet))
        if not any(str(getattr(note,n+'_id')) == str(x.pk) for n,x in proprietaires): raise Http404
    elif nom == 'dossiers:document_financement':
        # Un document ne peut être demandé qu'à partir des documents autorisés
        # du financement ; la vue métier contrôle son rattachement et ses droits.
        doc = get_object_or_404(m.DocumentFinancement, pk=kw['pk'])
        if str(doc.version.financement.accord.pk) != str(accord.pk): raise Http404
    else: raise Http404
    return match, dict(parse_qsl(url.query))


class LiensLocaux(HTMLParser):
    """Adapter les liens de fragments explicites, sans extraire une page HTML."""
    def __init__(self, context, cle='', formulaire='', tous=False, base=''):
        super().__init__(convert_charrefs=False)
        self.context, self.cle, self.formulaire, self.tous, self.base = context, cle, formulaire, tous, base
        self.externes=[]
        self.pile, self.sortie = [], []
        self.script = False

    def handle_starttag(self, tag, attrs):
        if tag == 'script': self.script=True; return
        if self.script: return
        a = dict(attrs)
        cle = a.get('data-prestation-cible') or (self.pile[-1][1] if self.pile else self.cle)
        texte = 'texte-narratif' in a.get('class','').split() or bool(self.pile and self.pile[-1][2])
        externe=False
        if not texte and 'data-prestation-lien' not in a and tag == 'a' and cle and a.get('href') and not a['href'].startswith('#') and (self.tous or 'data-dossier-action' in a):
            lien = urljoin(self.base,a['href']) if self.base else a['href']
            try:
                if urlsplit(lien).path == reverse('dossiers:prise', args=[self.context['nature'],self.context['objet'].pk,self.context['prise'].pk]):
                    a['href'] = adresse(self.context, cle)
                    a['data-prestation-lien'] = '1'
                    if self.formulaire: a['data-prestation-annuler'] = '1'
                else:
                    match, _ = autoriser_operation(self.context, cle, lien)
                    genre, objet = cible(self.context, cle)
                    ouvrir = genre != 'nouveau' and urlsplit(lien).path == consultation(genre, objet)
                    a['href'] = adresse(self.context, cle, '' if ouvrir else lien)
                    a['data-prestation-lien'] = '1'
                    if dict(parse_qsl(urlsplit(lien).query)).get('format') == 'pdf' or match.view_name.endswith('_pdf'): a['download']=''
                    if ouvrir and self.formulaire: a['data-prestation-annuler'] = '1'
                if 'data-liaison-annuler' in a: a['data-prestation-annuler'] = '1'
                a.pop('data-dossier-action', None)
            except Http404:
                if self.tous:
                    # Sorties volontaires vers catalogues/rapports, jamais
                    # transformées en opération locale par interception globale.
                    a['href'] = lien
                    a['data-prestation-externe'] = '1'
                    externe=True
        if tag == 'a': self.externes.append(externe)
        if tag == 'form' and self.formulaire:
            a['action'] = self.formulaire
            a['data-prestation-form'] = '1'
        rendu = {'h1':'h4','h2':'h5','h3':'h6'}.get(tag,tag) if self.tous else tag
        self.sortie.append('<' + rendu + ''.join(' '+k if v is None else ' '+k+'="'+escape(v, quote=True)+'"' for k,v in a.items()) + '>')
        if tag == 'form' and self.formulaire and a.get('method','get').lower() == 'get':
            self.sortie.extend('<input type="hidden" name="'+escape(k,quote=True)+'" value="'+escape(v,quote=True)+'">' for k,v in parse_qsl(urlsplit(self.formulaire).query))
        if tag not in ('input','br','hr','img','meta','link','path','wbr','source','area'): self.pile.append((tag, cle, texte))

    def handle_endtag(self, tag):
        if tag == 'script': self.script=False; return
        if self.script: return
        if tag == 'a' and self.externes and self.externes.pop(): self.sortie.append(' <span class="helptext">(hors prise en charge)</span>')
        self.sortie.append('</' + ({'h1':'h4','h2':'h5','h3':'h6'}.get(tag,tag) if self.tous else tag) + '>')
        for i in range(len(self.pile)-1,-1,-1):
            if self.pile[i][0] == tag: del self.pile[i:]; break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag,attrs)
        self.sortie[-1]=self.sortie[-1][:-1]+'/>'
        if self.pile and self.pile[-1][0]==tag:self.pile.pop()
    def handle_data(self, data):
        if not self.script: self.sortie.append(data)
    def handle_entityref(self, name): self.sortie.append('&'+name+';')
    def handle_charref(self, name): self.sortie.append('&#'+name+';')
    def handle_comment(self, data): self.sortie.append('<!--'+data+'-->')


def localiser(html, context, cle='', formulaire='', tous=False, base=''):
    parseur = LiensLocaux(context,cle,formulaire,tous,base); parseur.feed(str(html))
    return mark_safe(''.join(parseur.sortie))


def page(request, nature, pk, prise_pk):
    from . import vues_dossiers
    if not prise_pk: raise Http404
    cle = request.GET.get('prestation','')[:100]
    genre, _, identifiant = cle.partition(':')
    affichage = copy(request); affichage.method = 'GET'; affichage.GET = request.GET.copy()
    affichage._post = QueryDict(''); affichage._files = MultiValueDict()
    for nom in ('prestation','operation','imprimer'): affichage.GET.pop(nom,None)
    if genre=='commun':
        from .prestations_presentation import LECTURE
        if not request.user.has_perms(LECTURE):raise Http404
        p=get_object_or_404(m.PrestationCollective,pk=identifiant,accompagnement_id=prise_pk)
        affichage.GET['sejour' if p.nature=='hebergement' else 'repas']=identifiant
    if genre in ('sejour','repas',*dossier.CLES_AIDES): affichage.GET[genre] = identifiant
    if genre == 'hebergement': affichage.GET['prevision'] = identifiant
    affichage._prestation_interne = True; affichage._prestation_capture = True
    reponse = vues_dossiers.detail(affichage,nature,pk,prise_pk)
    if not isinstance(reponse, TemplateResponse): return reponse
    context = reponse.context_data
    genre, objet = cible(context,cle)
    operation = request.GET.get('operation','')
    if not operation:
        if request.method != 'GET' and genre != 'nouveau': raise Http404
        if genre == 'nouveau':
            if objet.startswith('commun_'):operation=reverse('dossiers:collectif_action',args=['prise',prise_pk,'creation'])+'?'+urlencode({'nature':objet[7:]})
            else:operation = reverse('dossiers:nouveau',args=[nature,pk,objet]) if objet in ('hebergement','repas','services_repas') else reverse('dossiers:aide_accorder',args=[prise_pk,objet])
        else: operation = consultation(genre,objet)
    match, query = autoriser_operation(context,cle,operation)
    if match.view_name == 'suivi:notes':
        aliases = {'accord_hebergement':'hebergement','accord_repas':'repas','accord_aide':'aide'}
        operation = reverse('suivi:cahier')+'?'+urlencode({'lia_cible':aliases.get(match.kwargs['nature'],match.kwargs['nature']),'lia_id':match.kwargs['pk']})
        match, query = autoriser_operation(context,cle,operation)
    interne = copy(request); interne.GET = request.GET.copy()
    interne.GET.update(query)
    if match.view_name == 'suivi:cahier':
        for nom in request.GET:
            if nom.startswith('lia_') and nom not in ('lia_cible','lia_id','lia_fragment'):
                interne.GET.setlist(nom,request.GET.getlist(nom))
    interne.GET['contexte_dossier'] = context['prise'].navigation['contexte_dossier']
    if request.method == 'POST':
        interne._post = request.POST.copy()
        interne._post['contexte_dossier'] = context['prise'].navigation['contexte_dossier']
    interne._prestation_capture = True
    interne.path = urlsplit(operation).path; interne.path_info = chemin_interne(interne.path); interne.resolver_match = match
    resultat = match.func(interne, *match.args, **match.kwargs)
    if 300 <= resultat.status_code < 400:
        if request.method != 'POST': raise Http404
        # Le POST n'est jamais rejoué ; revenir par un GET stable et signé.
        params = dict(context['parametres_prestations'])
        from django.core import signing
        location = urlsplit(resultat['Location']); valeurs = dict(parse_qsl(location.query))
        if valeurs.get('contexte_dossier'):
            try:
                vue = signing.loads(valeurs['contexte_dossier'],salt=dossier.SEL,max_age=86400).get('vue',{})
                params.update({k:v for k,v in vue.items() if k in params or k in ('sejour','repas','prevision',*dossier.CLES_AIDES)})
            except signing.BadSignature: pass
        if genre == 'nouveau':
            if objet.startswith('commun_'):
                ident=resultat.get('X-Prestation-Collective','')
                if not ident:raise Http404
                cle='commun:'+ident
            elif objet == 'hebergement': cle = 'hebergement:'+params['prevision'] if params.get('prevision') else 'sejour:'+params.get('sejour','')
            elif objet in ('repas','services_repas'): cle = 'repas:'+params.get('repas','')
            else:
                try: ident = resoudre(location.path).kwargs['pk']
                except (Resolver404,KeyError): raise Http404
                cle = 'aide_'+objet+':'+str(ident)
        elif genre == 'hebergement' and match.view_name in ('suivi:arrivee_prevue','suivi:admettre') and params.get('sejour'):
            cle = 'sejour:'+params['sejour']
        context['parametres_prestations'] = params
        if genre != 'nouveau' and (match.view_name.startswith('dossiers:financement') or match.view_name == 'suivi:cahier'):
            try:
                autoriser_operation(context,cle,resultat['Location'])
            except Http404: pass
            else: return HttpResponseRedirect(adresse(context,cle,resultat['Location']))
        return HttpResponseRedirect(adresse(context,cle))
    if not isinstance(resultat, TemplateResponse) and resultat.status_code == 409:
        lecture = copy(interne); lecture.method='GET'; lecture._post=QueryDict(''); lecture._files=MultiValueDict()
        repli = match.func(lecture,*match.args,**match.kwargs)
        if isinstance(repli,TemplateResponse) and repli.context_data.get('form') is not None:
            form=repli.context_data['form']; form.data=request.POST; form.files=request.FILES; form.is_bound=True; form._errors=None
            form.add_error(None,resultat.content.decode())
            repli.status_code=409; resultat=repli
    consulter = genre != 'nouveau' and urlsplit(operation).path == urlsplit(consultation(genre,objet)).path
    if genre in ('commun','nouveau') and match.view_name=='dossiers:collectif_action' and resultat.get('Content-Type','').startswith('application/json'):return resultat
    if resultat.get('Content-Type','').startswith('application/pdf') or 'attachment' in resultat.get('Content-Disposition',''):
        return resultat
    if isinstance(resultat, TemplateResponse):
        donnees = {**resultat.context_data,'base_prestation':'dossiers/_prestation_base.html'}
        consulter = genre != 'nouveau' and urlsplit(operation).path == urlsplit(consultation(genre,objet)).path
        if consulter:
            from .financements import LECTURE
            donnees.update(prestation=objet, prestation_genre=genre, prestation_cadre=context, prestation_finance_autorisee=request.user.has_perms(['personnes.'+d for d in LECTURE]))
            if genre == 'commun':
                from .prestations_presentation import actions
                donnees['actions_selection'] = actions(context, 'hebergement' if objet.nature == 'hebergement' else 'restauration')
            if genre == 'sejour':
                donnees['operations_sejour']=[x for x in donnees.get('operations',[]) if x.sejour_id == objet.pk]
            donnees['operations_accord']=[x for x in donnees.get('operations',[]) if x.sejour_id is None] if genre in ('sejour','hebergement') else []
            if genre == 'sejour': donnees['sejours'] = [objet]
            elif genre == 'hebergement':
                donnees['sejours'] = [s for s in context['sejours_dossier'] if s.accord_id == objet.pk]
                donnees['arrivee_prevue_disponible'] = any(a.pk==objet.pk for a in context['hebergements_prevus'])
            gabarit = 'dossiers/_prestation_groupe.html' if genre=='commun' else 'dossiers/_prestation_hebergement.html' if genre in ('sejour','hebergement') else 'dossiers/_prestation_repas.html' if genre == 'repas' else 'dossiers/_prestation_aide.html'
        elif match.view_name == 'suivi:cahier': gabarit = 'liaisons/panneau.html'
        else: gabarit = resultat.template_name
        contenu = render_to_string(gabarit,donnees,request=interne)
    else:
        contenu = '<p role="alert">'+escape(resultat.content.decode())+'</p>'
    contenu = localiser(contenu,context,cle,'' if consulter else adresse(context,cle,operation),True,operation)
    panneau = render_to_string('dossiers/_prestation_panneau.html',{
        'dossier':context['objet'],'prise':context['prise'],'contenu':contenu,'fermer_url':adresse(context)+'#prestation-'+cle.replace(':','-'),'retour_consultation':adresse(context)+'#'+('hebergement' if objet == 'hebergement' else 'repas' if objet in ('repas','services_repas') else 'aides-'+objet) if genre == 'nouveau' else adresse(context,cle),'en_creation':genre == 'nouveau',
        'en_action':urlsplit(operation).path != (urlsplit(consultation(genre,objet)).path if genre != 'nouveau' else ''),
        'imprimer_url':adresse(context,cle,impression=True),'impression':request.GET.get('imprimer')=='1',
    },request=request)
    context.update(prestation_ouverte=cle,prestation_panneau=mark_safe(panneau),prestation_annulee=genre == 'sejour' and bool(objet.annule_le),prestation_accord_annule=genre == 'hebergement' and bool(objet.annule_le))
    reponse.status_code = resultat.status_code
    return reponse
