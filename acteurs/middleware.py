from django.core.exceptions import PermissionDenied
from .contexte import perimetre
from . import politique as p


class PerimetreMiddleware:
    def __init__(self, get_response): self.get_response=get_response
    def __call__(self, request):
        if not getattr(request.user,'is_authenticated',False):return self.get_response(request)
        from django.urls import resolve, Resolver404
        try:
            vue_courante=resolve(request.path_info)
        except Resolver404:
            return self.get_response(request)
        service=request.session.get('service_acteurs')
        stats=False
        if p.active():
            hs=p.habilitations(request.user)
            if service and not hs.filter(service_id=service).exists():
                request.session.pop('service_acteurs',None);service=None
            if not service:
                ids=list(hs.order_by('service__etablissement_id','service__libelle','service_id').values_list('service_id',flat=True).distinct()[:1])
                if ids:service=ids[0]
            # Le mode regroupé ne s'applique qu'aux rapports, jamais aux faits,
            # justificatifs, téléchargements ou ouvertures depuis leurs résultats.
            modules_rapports={'personnes.vues_statistiques','personnes.vues_exploration','personnes.vues_rapports'}
            if vue_courante.func.__module__ in modules_rapports:
                stats='mes'
            if request.GET.get('portee_statistiques') in ('service','etablissement'):
                vue=vue_courante
                if vue.func.__module__=='personnes.vues_statistiques' and vue.func.__name__=='statistiques':
                    stats=request.GET['portee_statistiques']
                    request.acteurs_statistiques_regroupees=True
                    autorise=hs.filter(service_id=service)
                    if stats=='etablissement':autorise=autorise.filter(statistiques_etablissement=True)
                    else:autorise=autorise.filter(statistiques_service=True)
                    if not autorise.exists():return self.refus()
                    # Seuls les rapports regroupés qualifiés sont proposés dans ce
                    # mode ; les analyses nominatives passent par les accès ordinaires.
                    if request.GET.get('rapport','synthese') not in ('synthese','hebergement','repas','mensuel'):
                        return self.refus()
            if request.GET.get('format') in ('csv','pdf') or 'export' in request.path_info:
                if not hs.filter(exporter=True).exists():return self.refus()
        nom=vue_courante.view_name
        creations={'dossiers:creer':'dossier','personnes:creer':'dossier','suivi:creer':'dossier',
            'dossiers:nouvelle_prise':'prise','suivi:ouvrir':'prise','dossiers:nouveau':'prestation',
            'suivi:accorder_hebergement':'prestation','suivi:accorder_repas':'prestation'}
        creation=creations.get(nom,'')
        responsable=request.POST.get('responsable_acteurs') if creation else None
        if responsable and p.active():
            from .models import AppartenanceProfessionnelle
            from django.core.exceptions import ValidationError
            try:
                if not AppartenanceProfessionnelle.objects.filter(p.periode(),service_id=service,professionnel_id=responsable).exists():return self.refus()
            except (ValidationError,ValueError):return self.refus()
        export_demande=request.GET.get('format') in ('csv','pdf') or any(mot in request.path_info for mot in ('export','/fichier/','/pdf/','.pdf'))
        with perimetre(request.user,service,stats,responsable,creation,export_demande,vue_courante.kwargs.get('nature','')) as ctx:
            response=self.get_response(request)
            if hasattr(response,'render') and not response.is_rendered:response.render()
            if p.active() and response.get('Content-Disposition','').lower().startswith('attachment'):
                hs=p.habilitations(request.user)
                if ctx.statistiques in ('service','etablissement'):
                    option='statistiques_etablissement' if ctx.statistiques=='etablissement' else 'statistiques_service'
                    if not hs.filter(service_id=ctx.service_id,exporter=True,**{option:True}).exists():return self.refus()
                else:
                    services=set(ctx.services_export)
                    if not services:
                        services=set(p.missions(request.user).values_list('dossier__service_id',flat=True))
                    exportables=set(hs.filter(exporter=True).values_list('service_id',flat=True))
                    if not exportables or not services.issubset(exportables):return self.refus()
            return response

    def refus(self):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Votre habilitation actuelle ne permet pas cette opération.')
