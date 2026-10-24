"""Restitution à la demande ; les documents émis et figés relèvent du financement."""
from django.template.loader import render_to_string
from django.conf import settings


def produire(a,remises,*,navigateur=False):
    from pas_communs.pdf import fiche_texte,rendre_html
    lignes=['Données fictives uniquement','Référence de l’autorisation : '+str(a.pk),
        'Nature : '+a.get_nature_display(),'Titre / aide : '+a.libelle,'Unité : '+a.unite,a.precision,
        'Personnes autorisées : '+' ; '.join(str(p) for p in a.beneficiaires.all()),
        'Période autorisée : '+str(a.debut)+' → '+(str(a.fin) if a.fin else 'sans fin prévue')+' (fin exclue)',
        'Quantité globale autorisée : '+(str(a.quantite) if a.quantite is not None else 'Non chiffrée'),
        'Source : '+a.source,'Prestataire : '+(str(a.prestataire) if a.prestataire else 'Non renseigné'),
        'Financeur annoncé : '+(str(a.financeur) if a.financeur else 'Non renseigné')]
    if a.valeur_bon is not None:lignes.append('Valeur faciale par bon : '+str(a.valeur_bon)+' '+a.devise+' ; ce n’est pas un tarif facturé.')
    if a.annule_le:lignes.append('Autorisation annulée : '+a.motif_annulation)
    for r in remises:
        lignes += ['Réalisation du '+str(r.date)+' : '+str(r.quantite)+' '+a.unite,
            'Personnes concernées : '+' ; '.join(str(p) for p in r.beneficiaires.all()),'Source : '+r.source]
        if r.annule_le:lignes.append('Remise annulée : '+r.motif_annulation)
        u=r.usages.first()
        lignes.append('Utilisation déclarée : '+(str(u.quantite)+' '+a.unite+' au '+str(u.date) if u and u.quantite is not None else 'Non renseignée'))
    lignes+=['Une autorisation n’est pas une remise. Une remise de titre ne prouve pas un trajet effectué.',
        'Restitution des données actuellement enregistrées ; aucune signature, émission numérotée ou facturation automatique.']
    titre='Pas à Pas — Autorisation et relevé de réalisation'
    if navigateur:return fiche_texte(titre,lignes)
    def refuser(url):raise ValueError('Aucune ressource externe autorisée.')
    return rendre_html(render_to_string('aides/pdf.html',{'titre':titre,'lignes':lignes}),base_url=None,
        feuille_style=settings.BASE_DIR/'static/fiche-pdf.css',recuperer=refuser)
