from pathlib import Path

def test_host_skill_workflows_are_host_neutral():
 root=Path(__file__).parents[1]
 for name in ('market-brief','pr-monitor','pr-setup'):
  text=(root/'skills'/name/'SKILL.md').read_text()
  assert 'prmonitor' in text

def test_hermes_register_only_registers_skill_files():
 from hermes_plugin import register
 class C:
  def __init__(self): self.items=[]
  def register_skill(self,name,path): self.items.append((name,path.name))
 c=C(); register(c)
 assert any(name=='market-brief' for name,_ in c.items)
