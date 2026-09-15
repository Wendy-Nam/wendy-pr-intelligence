from prmonitor.schedule import schedule_key
def test_schedule_key_is_stable_and_pipeline_scoped():
 assert schedule_key('s','2026-09-15T00:00:00Z','market') == schedule_key('s','2026-09-15T00:00:00Z','market')
 assert schedule_key('s','2026-09-15T00:00:00Z','market') != schedule_key('s','2026-09-15T00:00:00Z','self')
