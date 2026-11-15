"""Explicit mission context; never infer gravity from planet destination."""
ENVIRONMENTS = ('unknown','microgravity','moon_surface','mars_surface','earth_surface','artificial_gravity')
LINKS = ('unknown','available_delayed','unavailable')
def validate_context(value):
    if not isinstance(value,dict) or set(value)-{'environment','link','phase','crew_training'}:
        raise ValueError('Invalid mission context')
    env=value.get('environment','unknown'); link=value.get('link','unknown')
    phase=value.get('phase','unknown'); training=value.get('crew_training','unknown')
    if env not in ENVIRONMENTS or link not in LINKS or not isinstance(phase,str) or len(phase)>100 or training not in ('unknown','basic','medical_professional'):
        raise ValueError('Invalid mission context')
    return {'environment':env,'link':link,'phase':phase,'crew_training':training}

def applicability(protocol,context):
    """Metadata gate only, not clinical validation. No treatment activation."""
    if context['environment']=='unknown': return {'eligible':False,'reason':'environment_required'}
    if protocol.get('review_status')!='reviewed': return {'eligible':False,'reason':'protocol_not_reviewed'}
    if context['environment'] not in protocol.get('environments',[]): return {'eligible':False,'reason':'environment_not_covered'}
    return {'eligible':False,'reason':'clinical_execution_not_implemented'}
