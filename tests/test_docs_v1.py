from pathlib import Path

def test_operations_runbook_documents_held_unknown_and_release_gates():
 text=(Path(__file__).parents[1]/'docs/OPERATIONS.md').read_text()
 assert all(term in text for term in ('HELD','unknown','pytest','Hermes'))
