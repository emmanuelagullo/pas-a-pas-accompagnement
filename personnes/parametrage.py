from acteurs.contexte import service_metier
"""Échange fermé des répertoires et catalogues : aperçu, puis création atomique.

Les homonymes ne sont jamais fusionnés. Une confirmation séparée peut autoriser
leur création ; aucun objet existant, droit, dossier ou compte n'est modifié.
"""
import hashlib
import json
from uuid import uuid4
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction, IntegrityError
from django.utils import timezone
from . import models as m, partenaires, intervenants, hebergement, aides, financements, bd6, suivi

FORMAT='pas-a-pas-parametrage-1'
MAX_OCTETS=1_000_000
MAX_ENTREES=500
MAX_VERSIONS=2000
FAMILLES=('organismes','professionnels','lieux','types_aide','tarifs')
MODELES=dict(zip(FAMILLES,(m.Partenaire,m.Intervenant,m.LieuHebergement,m.TypeAide,m.TarifPrestation)))
LIEU=('libelle','partenaire','organisme','parent','niveau')
LECTURE=('view_partenaire','view_fichepartenaire','view_revisionfichepartenaire','view_intervenant','view_ficheintervenant','view_revisionficheintervenant','view_lieuhebergement','view_revisionlieu','view_typeaide','view_revisiontypeaide','view_tarifprestation','view_versiontarif','view_importparametrage')
ECRITURE=('add_importparametrage','add_partenaire','add_fichepartenaire','add_intervenant','add_ficheintervenant','add_lieuhebergement','add_typeaide','add_tarifprestation','add_versiontarif')


@service_metier
def droits(acteur,ecriture=False):
    suivi.exiger(acteur,*LECTURE)
    if ecriture:
        suivi.exiger(acteur,*ECRITURE)
        hebergement.droit(acteur,'add_lieuhebergement')


def serialiser(x):return json.dumps(x,cls=DjangoJSONEncoder,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def empreinte(x):return hashlib.sha256(serialiser(x).encode()).hexdigest()


@service_metier
def exporter(acteur):
    droits(acteur);suivi.exiger(acteur,'exporter_parametrage')
    if sum(modele.objects.count() for modele in MODELES.values())>MAX_ENTREES:raise ValidationError('Au plus 500 entrées par fichier de paramétrage.')
    resultat={'format':FORMAT,**{k:[] for k in FAMILLES}}
    def valeurs(obj,champs):
        return {c:(str(getattr(obj,c+'_id')) if getattr(obj,c+'_id',None) is not None else None) if obj._meta.get_field(c).is_relation else getattr(obj,c) for c in champs}
    for nom,modele,service in [('organismes',m.Partenaire,partenaires),('professionnels',m.Intervenant,intervenants)]:
        for x in modele.objects.order_by('pk').prefetch_related('fiches'):
            resultat[nom].append({'ref':str(x.pk),'libelle':x.libelle,'versions':[{'debut':f.debut,'source':f.source,**valeurs(f,service.CHAMPS)} for f in x.fiches.order_by('debut')]})
    for nom,modele,champs in [('lieux',m.LieuHebergement,LIEU),('types_aide',m.TypeAide,aides.CATALOGUE)]:
        resultat[nom]=[{'ref':str(x.pk),'valeurs':valeurs(x,champs)} for x in modele.objects.order_by('pk')]
    for x in m.TarifPrestation.objects.order_by('pk').prefetch_related('versions'):
        resultat['tarifs'].append({'ref':str(x.pk),'versions':[valeurs(v,financements.TARIF) for v in x.versions.order_by('version')]})
    # Same decoder as import: no creation of an oversized/unusable export.
    return decoder(serialiser(resultat).encode())


def decoder(octets):
    if not isinstance(octets,bytes) or len(octets)>MAX_OCTETS:raise ValidationError('Fichier JSON limité à 1 Mo.')
    def paires(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('Clé répétée')
            d[k]=v
        return d
    try:x=json.loads(octets.decode('utf-8'),object_pairs_hook=paires,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
    except (ValueError,UnicodeError,RecursionError):raise ValidationError('JSON UTF-8 invalide, clé répétée ou nombre non fini.')
    try:serialiser(x).encode('utf-8')
    except (UnicodeError,RecursionError):raise ValidationError('Texte Unicode invalide dans le paramétrage.')
    verifier(x)
    return x


def nettoyer(modele,valeurs,champs,liens=()):
    if not isinstance(valeurs,dict) or set(valeurs)!=set(champs):raise ValidationError('Champs inconnus ou manquants dans le paramétrage.')
    d={}
    for c,v in valeurs.items():
        if isinstance(v,str) and '\x00' in v:raise ValidationError('Un caractère nul n’est pas accepté dans un champ.')
        if c in liens:
            if v is not None and (not isinstance(v,str) or not v or len(v)>80):raise ValidationError('Référence de répertoire invalide.')
            d[c]=v;continue
        f=modele._meta.get_field(c)
        if isinstance(f,models.BooleanField):
            if type(v) is not bool:raise ValidationError('Une option doit être true ou false.')
        elif isinstance(f,models.DateField):
            if v is not None and (not isinstance(v,str) or len(v)!=10):raise ValidationError('Date civile ISO attendue.')
        elif isinstance(f,models.DecimalField):
            if not isinstance(v,str):raise ValidationError('Prix décimal attendu sous forme de texte exact.')
        elif not isinstance(v,str):raise ValidationError('Une information textuelle doit rester du texte.')
        try:d[c]=f.clean(v,None)
        except (TypeError,ValueError,ArithmeticError):raise ValidationError('Valeur de paramétrage invalide.')
    for c in ('nom','libelle','unite','source'):
        if c in d and not d[c].strip():raise ValidationError('Une valeur non vide est nécessaire : '+c)
    # Field validation is identical to manual entry; validate period explicitly.
    if 'debut' in d and d.get('fin') is not None and d['fin']<=d['debut']:raise ValidationError('La fin exclue doit suivre le début.')
    return d


def verifier(x):
    if not isinstance(x,dict) or set(x)!=set(('format',*FAMILLES)) or x['format']!=FORMAT:raise ValidationError('Format de paramétrage non reconnu ; aucun dossier ni compte n’est accepté.')
    if any(not isinstance(x[k],list) for k in FAMILLES):raise ValidationError('Listes de paramétrage attendues.')
    if sum(len(x[k]) for k in FAMILLES)>MAX_ENTREES:raise ValidationError('Au plus 500 entrées par fichier.')
    refs={};n=0
    for k in FAMILLES:
        refs[k]=set()
        for e in x[k]:
            versionne=k in ('organismes','professionnels','tarifs')
            if not isinstance(e,dict) or set(e)!=({'ref','libelle','versions'} if k in ('organismes','professionnels') else {'ref','versions' if versionne else 'valeurs'}):raise ValidationError('Entrée de catalogue inconnue.')
            r=e['ref']
            if not isinstance(r,str) or not r or len(r)>80 or r in refs[k]:raise ValidationError('Référence vide, répétée ou trop longue.')
            refs[k].add(r)
            vs=e['versions'] if versionne else [e['valeurs']]
            if not isinstance(vs,list) or not vs and k not in ('organismes','professionnels'):raise ValidationError('Une définition au moins est nécessaire pour chaque entrée.')
            if k in ('organismes','professionnels'):
                nettoyer(MODELES[k],{'libelle':e['libelle']},('libelle',))
                if not e['libelle'].strip():raise ValidationError('Le libellé du répertoire est nécessaire.')
            n+=len(vs)
            if n>MAX_VERSIONS:raise ValidationError('Au plus 2 000 définitions datées par fichier.')
            precedent=None
            for v in vs:
                d=definition(k,v)
                if k in ('organismes','professionnels'):
                    if d['debut']>timezone.localdate() or precedent is not None and d['debut']<=precedent:raise ValidationError('Les fiches sont ordonnées par date passée distincte.')
                    precedent=d['debut']
    for k in FAMILLES:
        for e in x[k]:
            for v in e.get('versions',[e.get('valeurs')]):
                for champ,cible in (('organisme','organismes'),('prestataire','organismes'),('parent','lieux')):
                    if champ in v and v[champ] is not None and v[champ] not in refs[cible]:raise ValidationError('Référence absente du fichier : '+champ)
    ordre_lieux(x['lieux'])


def definition(k,v):
    if k=='organismes':return nettoyer(m.FichePartenaire,v,('debut','source',*partenaires.CHAMPS))
    if k=='professionnels':return nettoyer(m.FicheIntervenant,v,('debut','source',*intervenants.CHAMPS),('organisme',))
    if k=='tarifs':return nettoyer(m.VersionTarif,v,financements.TARIF,('prestataire',))
    if k=='types_aide':return nettoyer(m.TypeAide,v,aides.CATALOGUE)
    d=nettoyer(m.LieuHebergement,v,LIEU,('organisme','parent'))
    if d['organisme'] and d['partenaire'].strip():raise ValidationError('Le lieu ne peut avoir deux opérateurs concurrents.')
    return d


def ordre_lieux(entrees):
    resultat=[];attente=list(entrees);vus=set()
    while attente:
        suite=[e for e in attente if e['valeurs']['parent'] is None or e['valeurs']['parent'] in vus]
        if not suite:raise ValidationError('La hiérarchie de lieux contient une boucle.')
        for e in suite:resultat.append(e);vus.add(e['ref']);attente.remove(e)
    return resultat


def collisions(x):
    """Aucune fusion nominale : signaler ce qui aurait le même libellé."""
    resultat=[]
    for k in FAMILLES:
        noms=set(MODELES[k].objects.values_list('libelle',flat=True))
        for e in x[k]:
            vs=e.get('versions',[e.get('valeurs')]);v=vs[-1] if vs else {}
            nom=v.get('nom',v.get('libelle',e.get('libelle')))
            if nom in noms:resultat.append(f'{k} : {nom}')
            noms.add(nom)
    return resultat


@service_metier
def preparer(acteur,x):
    droits(acteur,ecriture=True);verifier(x)
    if m.ImportParametrage.objects.filter(empreinte=empreinte(x)).exists():raise ValidationError('Ce fichier a déjà été importé ; consultez son reçu.')
    conflit=collisions(x)
    return signing.dumps({'id':str(uuid4()),'contenu':x,'collisions':conflit},salt='parametrage-apercu-1',compress=True),conflit


def lire_apercu(attendu):
    try:p=signing.loads(attendu,salt='parametrage-apercu-1',max_age=3600)
    except (signing.BadSignature,TypeError,ValueError):raise ValidationError('Aperçu expiré ou non vérifiable ; choisissez à nouveau le fichier.')
    verifier(p['contenu']);return p


@service_metier
def confirmer(acteur,attendu,motif,accepter_homonymes=False):
    droits(acteur,ecriture=True)
    if not isinstance(motif,str) or not motif.strip() or len(motif)>240:raise ValidationError('Expliquez cet import (240 caractères maximum).')
    p=lire_apercu(attendu)
    x=p['contenu'];verifier(x);nouveaux={k:{} for k in FAMILLES}
    try:
        with transaction.atomic():
            # First SQL write: reserve nonce and digest before reading target state.
            j=m.ImportParametrage.objects.create(pk=p['id'],empreinte=empreinte(x),motif=motif.strip(),contenu=x,auteur=acteur)
            conflit=collisions(x)
            if conflit!=p['collisions']:raise ValidationError('Le répertoire a changé depuis l’aperçu ; préparez-le à nouveau.')
            if conflit and not accepter_homonymes:raise ValidationError('Des homonymes existent. Confirmez séparément leur création ou modifiez le fichier. Aucune fusion n’est faite.')
            for k in FAMILLES:
                entrees=ordre_lieux(x[k]) if k=='lieux' else x[k]
                for e in entrees:
                    objet=None
                    for brut in e.get('versions',[e.get('valeurs')]):
                        d=definition(k,brut)
                        for champ,cible in (('organisme','organismes'),('prestataire','organismes'),('parent','lieux')):
                            if champ in d:d[champ]=nouveaux[cible][d[champ]] if d[champ] else None
                        if k in ('organismes','professionnels'):
                            service=partenaires if k=='organismes' else intervenants
                            debut=d.pop('debut');source=d.pop('source')
                            if objet is None:objet=service.creer(acteur,debut,source,service.jeton_creation(),motif=motif,**d)
                            else:service.renseigner(acteur,objet,debut,source,bd6.jeton(objet),motif=motif,**d)
                        elif k=='lieux':objet=hebergement.creer_lieu(acteur,**d)
                        elif k=='types_aide':objet=aides.cataloguer(acteur,aides.jeton_catalogue(),motif,**d)
                        else:
                            action='definition' if objet is None else 'correction' if objet.versions.filter(debut=d['debut']).exists() else 'changement'
                            objet=financements.definir_tarif(acteur,bd6.jeton(objet) if objet else financements.creation_tarif(),motif,action=action,tarif=objet,**d)
                    if objet is None and k in ('organismes','professionnels'):
                        objet=MODELES[k].objects.create(libelle=e['libelle'],cree_par=acteur)
                    nouveaux[k][e['ref']]=objet
            j.correspondances={k:{ref:str(o.pk) for ref,o in vs.items()} for k,vs in nouveaux.items()}
            j.save(update_fields=['correspondances']);return j
    except IntegrityError as erreur:raise ValidationError('Confirmation déjà utilisée ou catalogue concurrent ; aucune reprise partielle.') from erreur
