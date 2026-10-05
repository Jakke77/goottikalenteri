#!/usr/bin/env python3
"""GitHub Actions publisher. Token is confined to authenticated REST requests."""
import base64
import json
import os
from pathlib import Path
import sys
from urllib.request import Request,urlopen
from urllib.error import HTTPError


def upload(directory):
    repo=os.environ['GITHUB_REPOSITORY']
    token=os.environ['GITHUB_TOKEN']
    def api(path,method='GET',data=None):
        req=Request('https://api.github.com/repos/'+repo+'/'+path,method=method,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                     'Content-Type':'application/json','User-Agent':'Varjoaika-package-build'})
        with urlopen(req,timeout=30) as response: return json.load(response)
    parent=None
    try: parent=api('git/ref/heads/apt')['object']['sha']
    except HTTPError as exc:
        if exc.code!=404: raise
    tree=[]
    for path in sorted(directory.iterdir()):
        blob=api('git/blobs','POST',dict(content=base64.b64encode(path.read_bytes()).decode(),encoding='base64'))
        tree.append(dict(path=path.name,mode='100644',type='blob',sha=blob['sha']))
    sha=api('git/trees','POST',dict(tree=tree))['sha']
    commit=api('git/commits','POST',dict(message='Publish tested Ubuntu package '+os.environ['GITHUB_SHA'][:12],
        tree=sha,parents=[parent] if parent else []))['sha']
    if parent: api('git/refs/heads/apt','PATCH',dict(sha=commit,force=False))
    else: api('git/refs','POST',dict(ref='refs/heads/apt',sha=commit))
    print('Public package channel updated: '+commit)

if __name__=='__main__': upload(Path(sys.argv[1]))
