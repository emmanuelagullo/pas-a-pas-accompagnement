#!/usr/bin/env python3
"""Déclencher le hook configuré et attendre le commit attendu, sans afficher le secret."""
import json
import os
import re
import time
import urllib.request
from urllib.parse import urlsplit


class SansRedirection(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def deployer(env, ouvrir=None, pause=time.sleep):
    hook, health, sha = env['DEMO_DEPLOY_HOOK'], env['DEMO_HEALTH_URL'], env['CI_COMMIT_SHA']
    for value in [hook, health]:
        url = urlsplit(value)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment:
            raise ValueError('Destinations HTTPS explicites requises.')
    if not re.fullmatch('[a-f0-9]{40}', sha) or env.get('CI_COMMIT_BRANCH') != env.get('CI_DEFAULT_BRANCH'):
        raise ValueError('Déployer depuis la branche principale seulement.')
    ouvrir = ouvrir or urllib.request.build_opener(SansRedirection).open
    with ouvrir(urllib.request.Request(hook, data=b'', method='POST'), timeout=30) as r:
        if not 200 <= r.status < 300:
            raise ValueError('Hook refusé.')
    for _ in range(120):
        try:
            with ouvrir(health, timeout=10) as r:
                data=json.load(r)
                if data.get('status') == 'ok' and data.get('commit') == sha:
                    print('Démonstration prête sur le commit attendu.')
                    return
        except (OSError, ValueError):
            pass
        pause(5)
    raise ValueError('Le commit attendu ne répond pas ; examiner le déploiement chez l’hébergeur.')


if __name__ == '__main__':
    try:
        deployer(os.environ)
    except Exception:
        # Les exceptions HTTP peuvent contenir le hook secret : ne pas les afficher.
        raise SystemExit('Déploiement non confirmé. Examiner le service et les paramètres sans publier le hook.') from None
