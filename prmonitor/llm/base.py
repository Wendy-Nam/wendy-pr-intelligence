from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
@dataclass(frozen=True)
class BackendHealth: available: bool; reason: str=''; supported: bool=True
@dataclass(frozen=True)
class Invocation: argv: list[str]; stdin: str=''; cwd: str|None=None; env_delta: dict[str,str]=field(default_factory=dict)
@dataclass(frozen=True)
class BackendResult: process_rc: int|None; stdout_json_or_text: str=''; stderr_path: Path|None=None; duration_ms:int=0; error:dict|None=None; model_requested:str|None=None; model_reported:str|None=None; usage:dict|None=None
class Backend(Protocol):
 def probe(self, live:bool=False)->BackendHealth: ...
 def build_invocation(self, request:dict, options:dict)->Invocation: ...
 def execute(self, request:dict, options:dict|None=None, deadline:float|None=None)->BackendResult: ...
