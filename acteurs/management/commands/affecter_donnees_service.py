"""Inventaire exact, vérification sans écriture puis confirmation par empreinte."""
import hashlib
import json
from pathlib import Path
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from acteurs.models import Service, DossierService, PorteeObjet, JournalAcces
from acteurs.politique import REPERTOIRES


class Command(BaseCommand):
    help='Affecter volontairement des objets anciens à un service. Vérification sans écriture par défaut ; aucun parcours récursif des données.'
    def add_arguments(self,p):
        p.add_argument('manifeste')
        p.add_argument('--auteur',required=True,help='Compte existant responsable de cette affectation.')
        p.add_argument('--appliquer',action='store_true')
        p.add_argument('--empreinte')
    @transaction.atomic
    def handle(self,*args,**o):
        try:
            octets=Path(o['manifeste']).read_bytes()
            if len(octets)>5_000_000:raise ValueError
            d=json.loads(octets)
            if set(d)!={'service','dossiers'} or not isinstance(d['dossiers'],list):raise ValueError
            service=Service.objects.get(pk=d['service'])
            auteur=get_user_model().objects.get(username=o['auteur'],is_active=True)
            entrees=[];vus=set()
            for dossier in d['dossiers']:
                if set(dossier)!={'nature','id','objets'} or dossier['nature'] not in ('personne','menage'):raise ValueError
                cible=apps.get_model('personnes',dossier['nature'])._base_manager.get(pk=dossier['id'])
                for entree in dossier['objets']:
                    if set(entree)!={'modele','id'}:raise ValueError
                    label=entree['modele'].lower()
                    if not label.startswith('personnes.') or label.split('.')[1] in REPERTOIRES|{'modelerapport','importparametrage'}:raise ValueError
                    model=apps.get_model(label)
                    objet=model._base_manager.get(pk=entree['id'])
                    cle=(model._meta.label_lower,str(objet.pk))
                    if cle in vus:raise ValueError
                    vus.add(cle)
                    ancienne=PorteeObjet.objects.filter(modele=cle[0],identifiant=cle[1]).first()
                    if ancienne and ancienne.service_id!=service.pk:raise CommandError('Un objet relève déjà d’un autre service : aucun transfert implicite.')
                    if ancienne and (getattr(ancienne.dossier,dossier['nature']+'_id',None)!=cible.pk):raise CommandError('Un objet relève déjà d’un autre dossier : aucun déplacement implicite.')
                    entrees.append((dossier,cible,objet,cle))
        except (OSError,ValueError,KeyError,LookupError,ObjectDoesNotExist,ValidationError,TypeError,AttributeError) as e:
            raise CommandError('Inventaire invalide, entrée dupliquée ou objet introuvable ; aucune affectation.') from e
        plan={cle:(info,cible) for info,cible,objet,cle in entrees}
        for info,cible,objet,cle in entrees:
            for champ in objet._meta.fields:
                if not champ.is_relation or champ.remote_field.model._meta.app_label!='personnes':continue
                model=champ.remote_field.model
                if model._meta.model_name in REPERTOIRES|{'personne','menage'}:continue
                identifiant=getattr(objet,champ.attname,None)
                if not identifiant:continue
                parent_cle=(model._meta.label_lower,str(identifiant))
                if parent_cle in plan:
                    parent_info,parent_cible=plan[parent_cle]
                    compatible=parent_info['nature']==info['nature'] and parent_cible.pk==cible.pk
                else:
                    origine=PorteeObjet.objects.filter(modele=parent_cle[0],identifiant=parent_cle[1]).select_related('dossier').first()
                    compatible=origine and origine.service_id==service.pk and (not origine.dossier_id or getattr(origine.dossier,info['nature']+'_id')==cible.pk)
                if not compatible:raise CommandError('Un parent privé manque dans l’inventaire ou relève d’un autre dossier/service ; aucune affectation.')
        sha=hashlib.sha256(octets).hexdigest()
        self.stdout.write(f'{len(d["dossiers"])} dossiers ; {len(entrees)} objets précis ; SHA-256 {sha}')
        if not o['appliquer']:return
        if o['empreinte']!=sha:raise CommandError('Empreinte absente ou différente ; aucune affectation.')
        dossiers={}
        # Chaque ligne est un choix explicite de l'exploitant. Les éléments non
        # inventoriés, y compris les journaux et versions, ne sont pas partagés.
        for info,cible,objet,cle in entrees:
            k=(info['nature'],str(cible.pk))
            if k not in dossiers:
                ds,_=DossierService.objects.get_or_create(service=service,**{info['nature']:cible},defaults={'cree_par':auteur,'en_attente':True})
                dossiers[k]=ds
            ds=dossiers[k]
            from acteurs.portees import parent
            origine=parent(objet)
            prise=objet if objet._meta.model_name=='accompagnement' else getattr(objet,'accompagnement',None)
            accord=objet if objet._meta.model_name in ('accordhebergement','accordrepas','accordaide') else getattr(objet,'accord',None)
            if accord and accord._meta.model_name not in ('accordhebergement','accordrepas','accordaide'):accord=None
            if accord:prise=accord.accompagnement
            PorteeObjet.objects.get_or_create(modele=cle[0],identifiant=cle[1],defaults={'dossier':ds,'service':service,
                'prise':prise or (origine.prise if origine else None),
                'prestation_modele':accord._meta.model_name if accord else (origine.prestation_modele if origine else ''),
                'prestation_id':accord.pk if accord else (origine.prestation_id if origine else None)})
        # Tous les objets existent désormais dans l'inventaire : propager la portée
        # précise jusqu'au point fixe, indépendamment de l'ordre des versions/journaux.
        for _ in range(len(entrees)+1):
            change=False
            for info,cible,objet,cle in entrees:
                origine=parent(objet)
                if not origine:continue
                portee=PorteeObjet.objects.get(modele=cle[0],identifiant=cle[1])
                valeurs={}
                if not portee.prise_id and origine.prise_id:valeurs['prise_id']=origine.prise_id
                if not portee.prestation_id and origine.prestation_id:
                    valeurs.update(prestation_modele=origine.prestation_modele,prestation_id=origine.prestation_id)
                if valeurs:
                    PorteeObjet.objects.filter(pk=portee.pk).update(**valeurs);change=True
            if not change:break
        # Une version ou un journal ne doit pas ouvrir un parent privé non
        # inventorié ou déjà affecté ailleurs par un simple select_related.
        for info,cible,objet,cle in entrees:
            ds=dossiers[(info['nature'],str(cible.pk))]
            for champ in objet._meta.fields:
                if not champ.is_relation or champ.remote_field.model._meta.app_label!='personnes':continue
                model=champ.remote_field.model
                if model._meta.model_name in REPERTOIRES|{'personne','menage'}:continue
                identifiant=getattr(objet,champ.attname,None)
                if not identifiant:continue
                parent_prive=PorteeObjet.objects.filter(modele=model._meta.label_lower,identifiant=str(identifiant)).first()
                if not parent_prive or parent_prive.service_id!=service.pk or (parent_prive.dossier_id and parent_prive.dossier_id!=ds.pk):
                    raise CommandError('Un parent privé manque dans l’inventaire ou appartient à un autre dossier/service ; aucune affectation.')
        from django.utils import timezone
        JournalAcces.objects.create(service=service,auteur=auteur,action='affectation_ancienne',date_effet=timezone.localdate(),
            apres={'empreinte':sha,'objets':len(entrees),'dossiers':[str(x.pk) for x in dossiers.values()]})
        self.stdout.write('Inventaire affecté ; aucune responsabilité ni habilitation créée.')
