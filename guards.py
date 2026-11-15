"""Conservative guards for known extraction failures. Not a general semantic verifier."""
import re
GUARD_VERSION='known-errors-2026-11-15-r2'

P={
'unsure':r"не\s+зна[а-яё]*|не\s+увер[а-яё]*|неизвест[а-яё]*|непонят[а-яё]*|не\s+(?:оцен[а-яё]*|провер[а-яё]*)|don['’]?t\s+know|do\s+not\s+know|not\s+sure|unknown|unclear|not\s+(?:assessed|checked)|(?:nobody|no\s+one)\s+(?:has\s+)?checked",
'past':r'вчера|раньше|позавчера|в\s+прошлом|yesterday|previously|used\s+to',
'normal_yes':r'дыш[а-яё]*\s+нормальн[а-яё]*|нормальн[а-яё]*\s+дыхан[а-яё]*|дыхан[а-яё]*\s+(?:ровн[а-яё]*\s+и\s+)?нормальн[а-яё]*|breath(?:es|ing)?\s+normal(?:ly)?|normal\s+breathing|breathing\s+is\s+normal',
'normal_no':r'не\s+дыш[а-яё]*|нет\s+(?:нормальн[а-яё]*\s+)?дыхан[а-яё]*|дыхан[а-яё]*\s+(?:нет|отсутств[а-яё]*)|судорожн[а-яё]*\s+вдох[а-яё]*|not\s+breathing|isn[\x27’]?t\s+breathing|no\s+(?:normal\s+)?breathing|only\s+gasping|\bgasping\b|не\s+нормальн[а-яё]*\s+дыхан[а-яё]*',
'responsive_no':r'не\s+(?:реагир[а-яё]*|отвеча[а-яё]*|просыпа[а-яё]*)|без\s+сознан[а-яё]*|потер[а-яё]*\s+сознан[а-яё]*|не\s+приход[а-яё]*\s+в\s+себя|unresponsive|unconscious|(?:does\s+not|not|doesn[\x27’]?t)\s+respond(?:ing)?|no\s+response|won[\x27’]?t\s+wake',
'responsive_yes':r'реагир[а-яё]*|отвеча[а-яё]*|в\s+сознан[а-яё]*|\brespons(?:ive|e)\b|\brespond(?:s|ing)?\b|\bawake\b',
'aed_ready':r'готов[а-яё]*|исправ[а-яё]*|\bready\b|\bworking\b|\boperational\b',
'aed_no':r'разряж[а-яё]*|неисправ[а-яё]*|сломан[а-яё]*|нет\s+(?:AED|дефибриллятор[а-яё]*)|\bdead\b|\bdischarged\b|\bbroken\b|not\s+(?:working|available|ready)',
}

def has(key,text):return bool(re.search(P[key],text,re.I))

def clause_for(text,evidence):
    match=re.search(re.escape(evidence),text,re.I)
    if not match:return evidence
    # Include the complete sentence, not a possibly misleading fragment picked by LLM.
    left=max(text.rfind(c,0,match.start()) for c in '.!?;\n')+1
    ends=[text.find(c,match.end()) for c in '.!?;\n']
    right=min([i for i in ends if i>=0],default=len(text))
    return text[left:right]


def apply_guards(facts,text):
    accepted=[];warnings=[]
    for f in facts:
        field,value,ev=f['field'],f['value'],f['evidence']
        scope=clause_for(text,ev);reason=None
        if has('unsure',ev) or has('unsure',scope):reason='unsure'
        elif has('past',ev):reason='past'
        elif field=='normal_breathing':
            # Conflicting explicit predicates anywhere in the message block reassurance.
            if value=='yes' and (not has('normal_yes',ev) or has('normal_no',scope) or has('normal_no',text)):
                reason='breath'
            elif value=='no' and not has('normal_no',ev):reason='breath'
            elif has('unsure',scope):reason='unsure'
            elif has('normal_yes',text) and has('normal_no',text):reason='conflict'
        elif field=='responsive':
            if value=='no' and (not has('responsive_no',ev) or re.search(r'not\s+(?:unresponsive|unconscious)|не\s+без\s+сознания',scope,re.I)):reason='react'
            elif value=='yes' and (not has('responsive_yes',ev) or has('responsive_no',scope) or has('responsive_no',text)):reason='react'
            elif has('unsure',scope):reason='unsure'
        elif field=='aed_ready':
            if value=='yes' and (not has('aed_ready',ev) or has('aed_no',scope)):reason='equipment'
            elif value=='no' and not has('aed_no',ev):reason='equipment'
            elif has('unsure',scope):reason='unsure'
        if reason:
            warnings.append({'field':field,'value':'unknown','evidence':ev,'reason':reason,'original_value':value})
        else:accepted.append(f)
    present={f['field'] for f in accepted}|{w['field'] for w in warnings}
    for field,key in [('normal_breathing','normal_no'),('responsive','responsive_no')]:
        match=re.search(P[key],text,re.I)
        if field not in present and match:
            warnings.append({'field':field,'value':'unknown','evidence':match.group(0),'reason':'missing_critical','original_value':'omitted'})
    return accepted,warnings

class GuardedFacts(list):
    def __init__(self,raw,text):
        facts,self.guard_warnings=apply_guards(raw,text)
        super().__init__(facts);self.raw_facts=raw
