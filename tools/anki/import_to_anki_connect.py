#!/usr/bin/env python3
"""Learning OS shared, subject-scoped Anki import. Dry-run is read-only."""
from __future__ import annotations
import argparse, hashlib, html, json, os, re, sys, unicodedata, urllib.error, urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_anki_import import load_items, find_value, FRONT_KEYS, BACK_KEYS, EXTRA_KEYS, SOURCE_KEYS, split_tags, merge_tags

CSS='''.card { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 20px; line-height: 1.6; text-align: left; color: #222; background-color: #fff; max-width: 48rem; margin: 0 auto; padding: 18px; overflow-wrap: anywhere; } .nightMode.card { color: #eee; background-color: #202020; } .anki-extra { margin-top: 1em; } .anki-source { margin-top: 1em; font-size: .8em; opacity: .7; } code { font-family: monospace; white-space: pre-wrap; }'''
TEMPLATES=[{'Name':'Card 1','Front':'{{Front}}','Back':'{{FrontSide}}<hr id=answer>{{Back}}'}]
class ImportProblem(RuntimeError):pass

def same_text(left,right):
    """Compare text by meaning, tolerating Unicode composed/decomposed forms."""
    return unicodedata.normalize('NFC',left)==unicodedata.normalize('NFC',right)

def request_anki(action, params=None, endpoint='http://127.0.0.1:8765'):
    if endpoint != 'http://127.0.0.1:8765':
        raise ImportProblem('Only the local AnkiConnect endpoint is supported; no remote transmission.')
    req=urllib.request.Request(endpoint,data=json.dumps({'action':action,'version':6,'params':params or {}}).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=15) as r: body=json.load(r)
    except Exception as e:raise ImportProblem(f'{action}连接失败：{e}；停止，不自动重试或切换UI。') from e
    if body.get('error'):raise ImportProblem(f'{action}失败：{body["error"]}')
    return body['result']

def ensure_anki_available(endpoint):
    version = request_anki('version', {}, endpoint)
    if not isinstance(version, int) or version < 6:
        raise ImportProblem('AnkiConnect API version 6 is required; nothing imported.')
    return 'already-running'

def normalized(s):
    s=re.sub(r'<(br\s*/?|hr[^>]*)>', ' ',s,flags=re.I)
    return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>','',s))).strip()

from formatting import render_text, back_html

def canonical_back(s):
    # Normalize known presentation wrappers only; case and answer words remain meaningful.
    s=re.sub(r'<b>\s*(?:Explanation|Source|补充)\s*</b>\s*(?:<br\s*/?>)?',' ',s,flags=re.I)
    s=re.sub(r'(<div[^>]*class="anki-source"[^>]*>\s*)出处：',r'\1',s)
    return normalized(s)

def compatible(fields,templates):
    if len(templates)!=1:return None
    for front,back in [('Front','Back'),('正面','背面')]:
        if fields!=[front,back]:continue
        t=next(iter(templates.values()));q=t.get('Front','');a=t.get('Back','')
        if re.search(r'{{\s*'+re.escape(front)+r'\s*}}',q) and re.search(r'{{\s*'+re.escape(back)+r'\s*}}',a) and not re.search(r'{{\s*(?:type:|cloze:)',q+a):
            if not re.search(r'{{\s*'+re.escape(back)+r'\s*}}',q):return front,back
    return None

def resolve_model(call,preferred):
    names=set(call('modelNames',{}))
    candidates=list(dict.fromkeys([preferred,'Basic','问答题','Learning OS Basic']))
    for name in candidates:
        if name not in names:continue
        mapping=compatible(call('modelFieldNames',{'modelName':name}),call('modelTemplates',{'modelName':name}))
        if mapping:return {'name':name,'fields':mapping,'create':False}
        if name==preferred and preferred not in ['Basic','问答题','Learning OS Basic']:
            raise ImportProblem('配置指定的笔记类型不是兼容单向问答；停止，不把填空/翻转/输入答案类型静默改成Basic。')
    name='Basic' if 'Basic' not in names else 'Learning OS Basic'
    if name in names:raise ImportProblem('标准类型同名但结构不兼容；未覆盖任何模板，请核对名称。')
    return {'name':name,'fields':('Front','Back'),'create':True}

def note_values(note):
    vals=sorted(note['fields'].values(),key=lambda v:v['order'])
    return vals[0]['value'], vals[1]['value'] if len(vals)>1 else ''

def target_notes(call,deck):
    escaped=deck.replace('\\','\\\\').replace('"','\\"')
    ids=call('findNotes',{'query':f'deck:"{escaped}"'})
    result=[]
    for i in range(0,len(ids),200):result+=call('notesInfo',{'notes':ids[i:i+200]})
    # Anki deck search includes children. Filter card deck names so only the configured deck is compared.
    cids=[c for n in result for c in n.get('cards',[])]
    exact=set()
    for i in range(0,len(cids),200):
        for c in call('cardsInfo',{'cards':cids[i:i+200]}):
            if c['deckName']==deck:exact.add(c['note'])
    return [n for n in result if n['noteId'] in exact]

def prepare(items,deck,tags,args):
    rows=[];seen={};duplicate_count=0
    for line,item in enumerate(items,1):
        for key in ('deck','deckName','deck_name'):
            if item.get(key) and item[key]!=deck:raise ImportProblem(f'第{line}行指向其他牌组；拒绝跨科导入。')
        front=find_value(item,FRONT_KEYS,args.front_key);answer=find_value(item,BACK_KEYS,args.back_key)
        if not front or not answer:raise ImportProblem(f'第{line}行问题或核心答案为空；不能由extra/source补成有效答案。')
        extra=find_value(item,EXTRA_KEYS,args.extra_key);source=find_value(item,SOURCE_KEYS,args.source_key) if args.include_source else ''
        if not source:raise ImportProblem(f'第{line}行缺少可定位的source，请注明本科模块与材料。')
        if re.search(r'```|\*\*[^*]+\*\*',front+answer+extra) or any(re.search(r'\\[A-Za-z]|[{}^]',x) for x in re.findall(r'(?<!\\)\$([^$\n]+)\$',front+answer+extra)):raise ImportProblem(f'第{line}行含未约定的Markdown；请将公式改为MathJax、其余保留纯文本。')
        row={'line':line,'front':render_text(front),'back':back_html(answer,extra,source),'tags':merge_tags(tags,item.get(args.tags_key or 'tags',[]))}
        key=normalized(row['front'])
        if key in seen:
            if canonical_back(row['back'])!=canonical_back(seen[key]['back']):raise ImportProblem(f'第{line}行同题面但答案不同；请先审核。')
            duplicate_count+=1;continue
        seen[key]=row;rows.append(row)
    return rows,duplicate_count

def execute(rows,deck,preferred,call,dry_run):
    model=resolve_model(call,preferred);decks=set(call('deckNames',{}));existing=target_notes(call,deck) if deck in decks else []
    fronts={}
    for n in existing:fronts.setdefault(normalized(note_values(n)[0]),[]).append(n)
    kept=[];done=[]
    for row in rows:
        found=fronts.get(normalized(row['front']),[])
        if found:
            matches=[n for n in found if canonical_back(note_values(n)[1])==canonical_back(row['back'])]
            if len(matches)!=len(found):raise ImportProblem(f'第{row["line"]}行与已有笔记同题面但内容不同；保留原卡，审核后按note ID修订。')
            n=matches[0]; actual_front,actual_back=note_values(n)
            done.append({**row,'front':actual_front,'back':actual_back,'tags':n['tags'],'model_name':n['modelName'],'field_names':tuple(k for k,v in sorted(n['fields'].items(),key=lambda kv:kv[1]['order'])),'status':'existing','note_id':n['noteId']});continue
        kept.append(row)
    f,b=model['fields']
    notes=[{'deckName':deck,'modelName':model['name'],'fields':{f:r['front'],b:r['back']},'tags':r['tags'],'options':{'allowDuplicate':False,'duplicateScope':'deck','duplicateScopeOptions':{'deckName':deck,'checkChildren':False,'checkAllModels':True}}} for r in kept]
    def validate():
        if not notes:return
        check=call('canAddNotesWithErrorDetail',{'notes':notes})
        if len(check)!=len(notes):raise ImportProblem('校验响应长度异常，停止。')
        errors=[{'line':r['line'],'reason':x.get('error','未知原因')} for r,x in zip(kept,check) if not x.get('canAdd')]
        if errors:raise ImportProblem('Anki拒绝添加（不一律当重复）：'+json.dumps(errors,ensure_ascii=False))
    if dry_run:
        if deck in decks and not model['create']:validate()
        return {'status':'preview','deck':deck,'model':model,'would_create_deck':deck not in decks,'would_add':len(kept),'existing':len(done),'rows':done+[{**r,'status':'planned'} for r in kept]}
    if not kept:return {'status':'confirmed','deck':deck,'model':model,'added':0,'existing':len(done),'rows':done}
    if model['create']:call('createModel',{'modelName':model['name'],'inOrderFields':['Front','Back'],'cardTemplates':TEMPLATES,'css':CSS,'isCloze':False})
    if deck not in decks:call('createDeck',{'deck':deck})
    validate()
    ids=call('addNotes',{'notes':notes})
    if len(ids)!=len(notes) or any(not isinstance(x,int) or x<=0 for x in ids):raise ImportProblem('导入返回数量或ID异常；状态未确认，不标成功，不自动重试。下次先重新核对本科牌组。')
    readback=call('notesInfo',{'notes':ids});by={n['noteId']:n for n in readback}
    for r,nid in zip(kept,ids):
        n=by.get(nid)
        if not n or n['modelName']!=model['name'] or not same_text(n['fields'][f]['value'],r['front']) or not same_text(n['fields'][b]['value'],r['back']) or not set(r['tags']).issubset(n['tags']):raise ImportProblem(f'笔记{nid}回读不一致；不标成功，保留候选，勿盲目重试。')
        done.append({**r,'model_name':model['name'],'field_names':model['fields'],'status':'added','note_id':nid})
    cards=call('cardsInfo',{'cards':[cid for n in readback for cid in n['cards']]})
    if len(cards)!=len(ids) or any(c['deckName']!=deck for c in cards):raise ImportProblem('回读牌组或生成卡片数量不一致，状态待核对。')
    return {'status':'confirmed','deck':deck,'model':model,'added':len(ids),'existing':len(done)-len(ids),'rows':done}

def atomic_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,path)

def write_confirmed(path,result,source_hash):
    # TSV contains only read-back confirmed rows. Field names reflect the actual model mapping.
    pairs={(r['model_name'],tuple(r['field_names'])) for r in result['rows']}
    if len(pairs)>1:
        for idx,(name,fields) in enumerate(sorted(pairs),1):
            subset={**result,'model':{'name':name,'fields':fields},'rows':[r for r in result['rows'] if r['model_name']==name and tuple(r['field_names'])==fields]}
            subset['added']=sum(r['status']=='added' for r in subset['rows']);subset['existing']=sum(r['status']=='existing' for r in subset['rows'])
            write_confirmed(path.with_name(path.stem+f'.{idx}'+path.suffix),subset,source_hash)
        return
    if not pairs:return
    name,fields=next(iter(pairs));result={**result,'model':{**result['model'],'name':name,'fields':fields}}
    f,b=fields;headers=['#separator:tab','#html:true',f'#notetype:{result["model"]["name"]}',f'#deck:{result["deck"]}',f'#columns:{f}\t{b}\tTags','#tags column:3']
    rows=sorted(result['rows'],key=lambda x:x['line'])
    body='\n'.join(headers)+'\n'+''.join(r['front'].replace('\t',' ')+'\t'+r['back'].replace('\t',' ')+'\t'+' '.join(r['tags'])+'\n' for r in rows)
    record={k:v for k,v in result.items() if k!='rows'};record.update({'source_sha256':source_hash,'notes':[{'line':r['line'],'note_id':r['note_id'],'status':r['status']} for r in rows]})
    # Receipt first: a TSV alone never serves as a success signal.
    atomic_json(path.with_suffix('.result.json'),record)
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp');tmp.write_text(body,encoding='utf-8');os.replace(tmp,path)

def parse_args(argv):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--config',type=Path);p.add_argument('--deck');p.add_argument('--notetype');p.add_argument('--tags',nargs='*',default=[]);p.add_argument('--backup-tsv',type=Path);p.add_argument('--endpoint',default='http://127.0.0.1:8765');p.add_argument('--apply',action='store_true',help='Write only after reviewing a dry-run and authorizing import');p.add_argument('--dry-run',action='store_true');p.add_argument('--create-deck',action='store_true',help='兼容旧命令；已配置本科牌组正式导入时自动准备')
    for k in ['front','back','extra','source','tags']:p.add_argument('--'+k+'-key')
    p.add_argument('--include-source',action=argparse.BooleanOptionalAction,default=True)
    return p.parse_args(argv)

def main(argv=None):
    args=parse_args(argv)
    if args.apply and args.dry_run:
        print("Choose --apply or --dry-run, not both.", file=sys.stderr); return 2
    args.dry_run = not args.apply
    try:
        config=args.config
        if config is None:
            config=next((p/'配置.json' for p in args.input.resolve().parents if p.name=='Anki' and (p/'配置.json').exists()),None)
        if config is None:raise ImportProblem('未找到本科配置；请传--config，不能凭临时牌组名跨科导入。')
        cfg=json.loads(config.read_text(encoding='utf-8'));deck=cfg['deck'];preferred=cfg.get('notetype',cfg.get('note_type','Basic'))
        if args.deck and args.deck!=deck:raise ImportProblem('--deck与本科配置不符。')
        if args.notetype and args.notetype!=preferred:raise ImportProblem('--notetype与本科配置不符。')
        if cfg.get('enabled') is not True:raise ImportProblem('本科Anki未启用，不导入。')
        rows,local_duplicates=prepare(load_items(args.input),deck,merge_tags(cfg.get('tags',[]),args.tags),args)
        if not rows:raise ImportProblem('没有候选；零张卡正常，无需导入。')
        startup=ensure_anki_available(args.endpoint)
        result=execute(rows,deck,preferred,lambda a,p:request_anki(a,p,args.endpoint),args.dry_run);result['batch_duplicates']=local_duplicates
        result['anki_startup']=startup
        if not args.dry_run:
            output=args.backup_tsv or config.parent/'已导入'/(args.input.stem+'.tsv')
            write_confirmed(output,result,hashlib.sha256(args.input.read_bytes()).hexdigest())
        print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False,indent=2));return 0
    except Exception as e:print('未确认导入：'+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
