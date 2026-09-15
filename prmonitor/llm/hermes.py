from .generic import GenericBackend
class HermesBackend(GenericBackend):
 """Configured generic CLI; absent template is explicitly unsupported."""
 def __init__(self,template=None): super().__init__(template or [])
