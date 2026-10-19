"""Contrats de refus et de promotion ; aucun appel distant ni secret réel."""
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from pas_communs.publication import manifeste, sha256

ROOT=Path(__file__).resolve().parent.parent


def charger(nom):
    spec=importlib.util.spec_from_file_location(nom,ROOT/'scripts'/f'{nom}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


PWA=charger('preparer-publication-pwa')
PROGRAMMES=charger('publier-paquets')
DEPLOY=charger('deployer-demonstration')
SHA='a'*40


class PublicationTests(unittest.TestCase):
    def test_run_github_refuse_origine_et_echecs(self):
        ok={'head_repository':{'full_name':PROGRAMMES.DEPOT},'conclusion':'success',
            'status':'completed','path':PROGRAMMES.WORKFLOW,'head_branch':'0.2.0',
            'event':'push','head_sha':SHA}
        self.assertEqual(PROGRAMMES.verify_run(ok,'0.2.0'),SHA)
        for key,value in [('head_repository',{'full_name':'autre/depot'}),('conclusion','failure'),
                          ('head_branch','main'),('path','.github/workflows/autre.yml'),('event','pull_request')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                PROGRAMMES.verify_run({**ok,key:value},'0.2.0')

    def test_archives_traversees_et_liens_refuses(self):
        import stat
        from zipfile import ZipInfo
        for nom in ['../secret','/secret','a\\secret']:
            with self.subTest(nom=nom),tempfile.TemporaryDirectory() as t:
                root=Path(t);archive=root/'a.zip'
                with ZipFile(archive,'w') as z:z.writestr(nom,b'fictif')
                for extract in [PROGRAMMES.unpack,PWA.extract]:
                    with self.assertRaises(ValueError):extract(archive,root/'out')
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);archive=root/'a.zip';entry=ZipInfo('lien');entry.external_attr=(stat.S_IFLNK|0o777)<<16
            with ZipFile(archive,'w') as z:z.writestr(entry,'cible')
            with self.assertRaises(ValueError):PWA.extract(archive,root/'out')

    def test_selection_gitlab_exige_tous_les_controles_du_commit(self):
        jobs=[{'name':name,'status':'success','id':i,'commit':{'id':SHA},'pipeline':{'id':12}}
              for i,name in enumerate(['test: [3.12, 5.2]','pwa-prototype','deploiement-ephemere','deploiement-persistant-local'],1)]
        def request(url):
            if '/jobs?' in url:return jobs,{}
            if '/pipelines/' in url:return {'sha':SHA,'ref':'main','source':'push'},{}
            return {'id':1,'path_with_namespace':PWA.SOURCE,'default_branch':'main'},{}
        with patch.object(PWA,'json_request',side_effect=request):
            self.assertEqual(PWA.select_job('https://forge.invalid/api','1','12',SHA)[0]['name'],'pwa-prototype')
            for job in jobs:
                job['status']='failed'
                with self.assertRaises(ValueError):PWA.select_job('https://forge.invalid/api','1','12',SHA)
                job['status']='success'
            jobs[-1]['commit']['id']='b'*40
            with self.assertRaises(ValueError):PWA.select_job('https://forge.invalid/api','1','12',SHA)

    def test_rc_acceptee_par_la_politique_actuelle_du_canal_pages(self):
        jobs=[{'name':name,'status':'success','id':i,'commit':{'id':SHA},'pipeline':{'id':12}}
              for i,name in enumerate(['test: [3.12, 5.2]','pwa-prototype','deploiement-ephemere','deploiement-persistant-local'],1)]
        for tag in ['0.3.0', '0.3.0-rc.1']:
            def request(url):
                if '/jobs?' in url:return jobs,{}
                if '/pipelines/' in url:return {'sha':SHA,'ref':tag,'source':'push'},{}
                if '/repository/tags/' in url:return {'commit':{'id':SHA}},{}
                if '/commits/' in url:return {'sha':SHA},{}
                return {'id':1,'path_with_namespace':PWA.SOURCE,'default_branch':'main'},{}
            with self.subTest(tag=tag),patch.object(PWA,'json_request',side_effect=request):
                self.assertEqual(PWA.select_job('https://forge.invalid/api','1','12',SHA,tag,tag)[0]['name'],'pwa-prototype')

    def test_promotion_pwa_normale_et_refus_test_alteration(self):
        for mode in ['normal','test','altere','mauvais-commit']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                root=Path(t);bundle=root/'bundle';bundle.mkdir();assets=[]
                for nom in ['index.html','worker.js','sw.js','application.zip']:
                    p=bundle/nom;p.write_bytes(b'contenu fictif');assets.append({'url':'/'+nom,'sha256':sha256(p)})
                config={'application':'pas-a-pas-accompagnement','version':'chrs.pwa.'+'a'*16,
                        'testMode':mode=='test','commit':SHA if mode!='mauvais-commit' else 'b'*40,
                        'tag':None,'application_version':'dev.'+SHA[:8],'assets':assets}
                (bundle/'config.json').write_text(json.dumps(config))
                candidate=root/'candidate';candidate.mkdir();archive=candidate/'PasAPasAccompagnement-pwa.zip'
                with ZipFile(archive,'w') as z:
                    for p in bundle.iterdir():z.write(p,p.name)
                notes=candidate/'notes-version.md';notes.write_text('Notes fictives.\n')
                record=manifeste(PWA.FORMAT,{'commit':SHA,'tag':None,'application_version':'dev.'+SHA[:8]},
                    'navigateur','chromium-statique',[archive,notes],{'CI_PIPELINE_ID':'12','CI_JOB_ID':'2'})
                (candidate/'publication-pwa.json').write_text(json.dumps(record))
                if mode=='altere':archive.write_bytes(archive.read_bytes()+b'alteration')
                artifact=root/'artifact.zip'
                with ZipFile(artifact,'w') as z:
                    for p in candidate.iterdir():z.write(p,'dist/'+p.name)
                env={'CI_PIPELINE_SOURCE':'pipeline','PWA_SOURCE_PROJECT':PWA.SOURCE,'PWA_SOURCE_PROJECT_ID':'1',
                     'PWA_SOURCE_PIPELINE_ID':'12','PWA_SOURCE_SHA':SHA,'PWA_SOURCE_REF':'main','CI_API_V4_URL':'https://forge.invalid/api'}
                def download(url,path):shutil.copyfile(artifact,path)
                old=Path.cwd()
                try:
                    os.chdir(root)
                    with patch.dict(os.environ,env,clear=True),patch('sys.argv',['p','--destination',str(root/'public'),'--pages-url','https://pwa.invalid/']),patch.object(PWA,'select_job',return_value=({'id':2},'https://forge.invalid/artifact')),patch.object(PWA,'download',side_effect=download):
                        if mode=='normal':
                            PWA.main();self.assertEqual((root/'public/config.json').read_bytes(),(bundle/'config.json').read_bytes())
                        else:
                            with self.assertRaises(ValueError):PWA.main()
                            self.assertFalse((root/'public').exists())
                finally:os.chdir(old)

    def test_programmes_promeuvent_les_octets_et_refusent_une_tentative_differente(self):
        run={'head_repository':{'full_name':PROGRAMMES.DEPOT},'conclusion':'success',
             'status':'completed','path':PROGRAMMES.WORKFLOW,'head_branch':'0.2.0',
             'event':'push','head_sha':SHA,'run_attempt':1}
        for alter in [False,True,"notes","sans-setup","setup-altere"]:
            with self.subTest(alter=alter),tempfile.TemporaryDirectory() as t:
                root=Path(t);arts=[];blobs={}
                for i,(system,target,name) in enumerate([
                    ('Linux','linux-ubuntu24.04-x86_64','PasAPasAccompagnement-linux.tar.gz'),
                    ('Windows','windows-x86_64','PasAPasAccompagnement-windows.zip')],1):
                    src=root/system;src.mkdir();f=src/name;f.write_bytes(b'archive fictive '+system.encode())
                    notes=src/'notes-version.md';notes.write_text('Autres notes.\n' if alter=='notes' else 'Notes fictives.\n')
                    fichiers=[f,notes]
                    if system=='Windows':
                        setup=src/'PasAPasAccompagnement-Setup-0.2.0-x64.exe'
                        setup.write_bytes(b'setup fictif');fichiers.append(setup)
                    m=manifeste('pas-a-pas-accompagnement-publication',{'commit':SHA,'tag':'0.2.0','application_version':'0.2.0'},
                        'programme',target,fichiers,{'GITHUB_RUN_ID':'12','GITHUB_JOB':'programme','GITHUB_RUN_ATTEMPT':'2' if alter is True else '1'})
                    (src/'publication-programme.json').write_text(json.dumps(m))
                    if system=='Windows' and alter=='sans-setup':setup.unlink()
                    if system=='Windows' and alter=='setup-altere':setup.write_bytes(b'setup altere')
                    archive=root/(system+'.zip')
                    with ZipFile(archive,'w') as z:
                        for p in src.iterdir():z.write(p,p.name)
                    blobs[str(i)]=archive.read_bytes()
                    arts.append({'id':i,'name':'PasAPasAccompagnement-'+system,'expired':False,'digest':'sha256:'+sha256(archive)})
                def api(path):return {'artifacts':arts} if '/artifacts?' in path else run
                def gh(*args,**kwargs):
                    ident=args[1].split('/')[-2];kwargs['stdout'].write(blobs[ident])
                out=root/'out';out.mkdir()
                with patch.object(PROGRAMMES,'api',side_effect=api),patch.object(PROGRAMMES,'gh',side_effect=gh),patch.object(PROGRAMMES,'verify_tags'),patch.object(PROGRAMMES.subprocess,'check_output',return_value='## 0.2.0\nNotes fictives.\n'):
                    if alter:
                        with self.assertRaises(ValueError):PROGRAMMES.prepare('12','0.2.0',out)
                    else:
                        files,commit=PROGRAMMES.prepare('12','0.2.0',out)
                        self.assertEqual(commit,SHA)
                        self.assertEqual(len(files),7)
                        self.assertEqual((out/'PasAPasAccompagnement-linux.tar.gz').read_bytes(),b'archive fictive Linux')

    def test_hook_confirme_le_commit_et_masque_les_destinations_invalides(self):
        env={'DEMO_DEPLOY_HOOK':'https://hook.invalid/secret-fictif','DEMO_HEALTH_URL':'https://demo.invalid/health/',
             'CI_COMMIT_SHA':SHA,'CI_COMMIT_BRANCH':'main','CI_DEFAULT_BRANCH':'main'}
        calls=[]
        def ouvrir(req,timeout):
            calls.append(req)
            r=io.BytesIO(json.dumps({'status':'ok','commit':SHA}).encode());r.status=200;return r
        DEPLOY.deployer(env,ouvrir,lambda _:None)
        self.assertEqual(calls[0].method,'POST')
        with self.assertRaises(ValueError):DEPLOY.deployer({**env,'DEMO_DEPLOY_HOOK':'http://hook.invalid'},ouvrir)
        with self.assertRaises(ValueError):DEPLOY.deployer({**env,'CI_COMMIT_BRANCH':'branche'},ouvrir)


if __name__=='__main__':unittest.main()
