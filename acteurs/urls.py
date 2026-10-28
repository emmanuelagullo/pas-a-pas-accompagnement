from django.urls import path
from . import views as v
app_name='acteurs'
urlpatterns=[
    path('services/<int:service_pk>/reperage/',v.reperage_politique,name='reperage_politique'),
    path('dossiers/<uuid:pk>/demander/',v.demander_rattachement,name='demander_rattachement'),
    path('demandes/<int:pk>/decider/',v.decider_rattachement,name='decider_rattachement'),
    path('responsabilites/<int:pk>/terminer/',v.terminer,name='terminer'),
    path('services/<int:service_pk>/exploitation/',v.exploitation,name='exploitation'),
    path('dossiers/<uuid:pk>/attribuer/',v.attribuer,name='attribuer_dossier'),
    path('dossiers/<uuid:pk>/attribuer/<str:niveau>/<uuid:objet_pk>/',v.attribuer,name='attribuer_objet'),
    path('',v.organisation,name='organisation'),
    path('services/nouveau/',v.organisation,{'action':'creer_service'},name='creer_service'),
    path('services/<int:service_pk>/',v.organisation,name='service'),
    path('services/<int:service_pk>/politique/',v.organisation,{'action':'politique'},name='politique'),
    path('services/<int:service_pk>/membre/',v.organisation,{'action':'membre'},name='membre'),
    path('services/<int:service_pk>/habilitation/',v.organisation,{'action':'habilitation'},name='habilitation'),
    path('habilitations/<int:pk>/revoquer/',v.revocation,name='revoquer'),
    path('choisir-service/',v.choisir_service,name='choisir_service'),
    path('dossiers/<uuid:pk>/reprendre/',v.reprendre,name='reprendre'),
    path('dossiers/<uuid:pk>/relais/',v.relais,name='relais_dossier'),
    path('dossiers/<uuid:pk>/relais/<str:niveau>/<uuid:objet_pk>/',v.relais,name='relais_objet'),
]
