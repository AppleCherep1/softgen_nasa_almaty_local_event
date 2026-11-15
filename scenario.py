"""Deterministic, source-linked educational preview. Not a flight-certified protocol."""
VERSION = 'microgravity-preview-0.1'
SOURCE_URLS = {
 'micro_cpr_2020':'https://pmc.ncbi.nlm.nih.gov/articles/PMC7607644/',
 'redcross_breathing':'https://www.redcross.org/take-a-class/resources/learn-first-aid/unresponsive-and-breathing-person',
 'nasa_cdss_conops':'https://ntrs.nasa.gov/citations/20220017856'}

def validate_equipment(equipment):
    if not isinstance(equipment,dict) or set(equipment)-{'aed','cmrs','isolated_surface'}:
        raise ValueError('Invalid equipment')
    out={}
    for key in ('aed','cmrs','isolated_surface'):
        item=equipment.get(key,{})
        if not isinstance(item,dict) or set(item)-{'ready','model','location'}:
            raise ValueError('Invalid equipment item')
        ready=item.get('ready','unknown')
        if ready not in ('yes','no','unknown'): raise ValueError('Invalid readiness')
        out[key]={'ready':ready}
        for f in ('model','location'):
            v=item.get(f,'')
            if not isinstance(v,str) or len(v)>160: raise ValueError('Invalid equipment metadata')
            out[key][f]=v
    return out

def build_preview(context,facts,equipment):
    equipment=validate_equipment(equipment)
    result={'version':VERSION,'mode':'educational_preview','clinical_protocol_enabled':False,
            'flight_review_status':'not_reviewed','sources':SOURCE_URLS,'steps':[],
            'limits':['Учебная демонстрация; не утверждённый бортовой протокол.',
                      'Показанные шаги не заменяют обучение и локальные процедуры корабля.'],
            'equipment':equipment}
    def add(id,text,source):result['steps'].append({'id':id,'text':text,'source':source})
    if context['environment']!='microgravity':
        result['branch']='environment_not_supported';return result
    if facts.get('responsive')!='no':
        result['branch']='outside_unresponsive_scenario';return result
    add('call_crew','Позовите медика и других членов экипажа.','micro_cpr_2020')
    result['communication_note']=('Связь недоступна: не ожидать ответа Земли для начала помощи. Журнал остаётся на устройстве.' if context['link']=='unavailable' else 'Бортовая помощь не должна ждать ответа Земли. Отправка журнала пока не реализована.')
    breathing=facts.get('normal_breathing','unknown')
    if breathing=='unknown':
        result['branch']='breathing_required'
        add('clarify_breathing','Уточните, есть ли нормальное дыхание; отдельные судорожные вдохи не считать нормальным дыханием.','redcross_breathing')
    elif breathing=='yes':
        result['branch']='unresponsive_normal_breathing'
        add('monitor','Продолжайте наблюдать за реакцией и дыханием до передачи помощи медику; изменения внесите новым сообщением.','redcross_breathing')
        result['limits'].append('Рекомендация Красного Креста о наблюдении — общий принцип земной первой помощи. Положение тела и обращение с дыхательными путями в микрогравитации здесь не реализованы; требуется бортовая инструкция.')
    else:
        result['branch']='unresponsive_no_normal_breathing'
        add('bls','Отсутствие реакции и нормального дыхания требует немедленной СЛР обученным спасателем по доступной бортовой инструкции.','micro_cpr_2020')
        result['microgravity_reference']='Руководство DGLRM/ESAM 2020 рассматривает Evetts–Russomano для начальной СЛР и handstand после фиксации на CMRS при подходящей геометрии. Это справка, не обучение технике.'
        ready=equipment['aed']['ready']
        if facts.get('aed_ready')=='no':ready='no'
        elif facts.get('aed_ready')=='yes' and ready=='no':ready='conflict'
        result['aed_effective_status']=ready
        if ready=='no':
            add('aed_unavailable','AED отмечен как недоступный/неисправный. Сообщите это медику; исправный запасной аппарат не предполагается автоматически.','micro_cpr_2020')
        elif ready=='conflict':
            add('aed_conflict','Есть противоречие между подтверждённым сообщением и инвентарём AED. Повторно проверьте готовность, не задерживая помощь.','nasa_cdss_conops')
        elif ready=='yes' and equipment['cmrs']['ready']=='yes' and equipment['isolated_surface']['ready']=='yes':
            add('aed_ready','Подготовьте указанный AED для обученного спасателя. Руководство по микрогравитации требует фиксации пациента на электрически изолированной безопасной поверхности; применение — по инструкции аппарата и бортовому протоколу.','micro_cpr_2020')
        else:
            add('aed_check','Готовность AED, системы фиксации или изолированной безопасной поверхности не подтверждена. Проверьте условия с медиком; разрешение на разряд системой не выдаётся.','micro_cpr_2020')
    return result
