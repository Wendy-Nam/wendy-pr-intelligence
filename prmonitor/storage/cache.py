"""Exact-key, hash-verified local stage cache."""
from __future__ import annotations
import hashlib, json, os, uuid
from pathlib import Path
from ..models import canonical_json_bytes

def stage_key(stage_name: str, stage_version: str, input_hashes: dict, config_hash: str, window_start: str, window_end: str, options: dict) -> str:
    return hashlib.sha256(canonical_json_bytes({"stage_name":stage_name,"stage_version":stage_version,"input_hashes":input_hashes,"relevant_config_hash":config_hash,"window_start":window_start,"window_end":window_end,"options":options})).hexdigest()

class StageCache:
    def __init__(self, root: Path): self.root=root
    def _dir(self,key):
        if len(key)!=64 or any(c not in '0123456789abcdef' for c in key): raise ValueError('invalid cache key')
        return self.root/'stages'/key
    def read(self,key):
        root=self._dir(key); artifact=root/'artifact.json'; manifest=root/'manifest.json'
        try:
            meta=json.loads(manifest.read_text(encoding='utf-8')); raw=artifact.read_bytes()
            if meta.get('complete') is not True or meta.get('sha256') != hashlib.sha256(raw).hexdigest(): return None
            return json.loads(raw)
        except (OSError, ValueError, json.JSONDecodeError): return None
    def get_or_build(self,key,producer, *, force_refresh: bool = False):
        """Use a verified exact entry, except explicit fetch force-refresh."""
        cached = None if force_refresh else self.read(key)
        if cached is not None: return cached, True
        value=producer(); raw=canonical_json_bytes(value); root=self._dir(key); root.mkdir(parents=True,exist_ok=True)
        tmp=root/f'.tmp-{uuid.uuid4().hex}'; tmp.write_bytes(raw); os.replace(tmp,root/'artifact.json')
        meta={"complete":True,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}
        tmp=root/f'.tmp-{uuid.uuid4().hex}'; tmp.write_text(json.dumps(meta,sort_keys=True),encoding='utf-8'); os.replace(tmp,root/'manifest.json')
        return value, False
