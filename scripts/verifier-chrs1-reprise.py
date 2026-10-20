import tempfile, subprocess, os, sqlite3, sys
from pathlib import Path
python=sys.executable
os.chdir(Path(__file__).resolve().parents[1])
with tempfile.TemporaryDirectory() as t:
    racine=Path(t);source=racine/'source';source.mkdir()
    env=dict(os.environ,ACCOMPAGNEMENT_DONNEES=str(source))
    def cmd(*args, environnement=env):
        return subprocess.check_output([python,'manage.py',*args],env=environnement,text=True)
    cmd('migrate','personnes','0001','--noinput')
    cmd('migrate','identites','0002','--noinput')
    cmd('shell','-c',"from django.contrib.auth import get_user_model; from personnes.models import Personne; u=get_user_model().objects.create_user('historique',password='Mot-fictif-12345'); p=Personne.objects.create(designation='Historique fictif',cree_par=u); print(p.pk)")
    db=source/'accompagnement.sqlite3'
    with sqlite3.connect(db) as c: avant=c.execute('select id,designation from personnes_personne').fetchall(); mot=c.execute('select password from identites_utilisateur').fetchone()
    # Archive historique puis reprise et migration dans une autre copie.
    cmd('sauvegarder_paquet',str(racine/'ancienne.zip'))
    cmd('restaurer_copie',str(racine/'ancienne.zip'),str(racine/'ancienne-restauree'))
    ancien_env=dict(env,ACCOMPAGNEMENT_DONNEES=str(racine/'ancienne-restauree'))
    cmd('migrate','--noinput',environnement=ancien_env)
    cmd('migrate','--noinput')
    cmd('autoriser_chrs1','historique')
    cmd('shell','-c',"from personnes import suivi; from personnes.models import Personne; from django.contrib.auth import get_user_model; from datetime import date; u=get_user_model().objects.get(); p=Personne.objects.get(); m=suivi.creer_menage(u,'Ménage historique',[p],date(2026,1,1)); suivi.ouvrir(u,m,[p],date(2026,1,1))")
    cmd('autoriser_chrs2','historique')
    cmd('shell','-c',"from personnes import repas; from personnes.models import Accompagnement; from django.contrib.auth import get_user_model; from datetime import date; u=get_user_model().objects.get(); a=Accompagnement.objects.get(); p=a.beneficiaires.get(); accord=repas.accorder(u,a,[p],date(2026,1,1),date(2026,2,1),'dejeuner'); r=repas.distribuer(u,accord,p,date(2026,1,2),1); repas.annuler(u,r,'Erreur fictive'); repas.distribuer(u,accord,p,date(2026,1,2),2)")
    cmd('sauvegarder_paquet',str(racine/'nouvelle.zip'))
    cmd('restaurer_copie',str(racine/'nouvelle.zip'),str(racine/'restauree'))
    with sqlite3.connect(racine/'restauree'/'accompagnement.sqlite3') as c:
        assert c.execute('select id,designation from personnes_personne').fetchall()==avant
        assert c.execute('select password from identites_utilisateur').fetchone()==mot
        assert c.execute('select count(*) from personnes_accompagnement_beneficiaires').fetchone()==(1,)
        assert c.execute('select count(*) from personnes_evenementsuivi').fetchone()==(3,)
        assert c.execute('select count(*) from personnes_accordrepas_beneficiaires').fetchone()==(1,)
        assert c.execute('select count(*) from personnes_operationrepas').fetchone()==(4,)
        assert c.execute('select sum(quantite) from personnes_repasdistribue where annule_le is null').fetchone()==(2,)
        assert c.execute('pragma foreign_key_check').fetchall()==[]
    print('CHRS1/2 : migration historique, ancienne archive, UUID/mot de passe et nouvelles relations restaurées : OK')
