import unittest,sys,copy,tempfile,json,contextlib,io,unicodedata
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/anki'))
import import_to_anki_connect as m
class Fake:
 def __init__(self,missing=False,chinese=False,normalize_on_write=False):
  self.actions=[];self.name='问答题' if chinese else 'Basic';self.fields=['正面','背面'] if chinese else ['Front','Back'];self.names=[] if missing else [self.name];self.decks=[] if missing else ['Test'];self.notes={};self.reject=None;self.badids=False;self.normalize_on_write=normalize_on_write
 def __call__(self,a,p):
  self.actions.append(a)
  if a=='modelNames':return self.names
  if a=='modelFieldNames':return self.fields
  if a=='modelTemplates':return {'Card':{'Front':'{{'+self.fields[0]+'}}','Back':'{{FrontSide}}<hr>{{'+self.fields[1]+'}}'}}
  if a=='deckNames':return self.decks
  if a=='findNotes':return list(self.notes)
  if a=='notesInfo':return [self.notes[i] for i in p['notes']]
  if a=='cardsInfo':return [{'cardId':i,'note':i,'deckName':'Test'} for i in p['cards']]
  if a=='createDeck':self.decks.append(p['deck']);return 1
  if a=='createModel':self.names.append(p['modelName']);return 1
  if a=='canAddNotesWithErrorDetail':return [{'canAdd':not self.reject,'error':self.reject} for n in p['notes']]
  if a=='addNotes':
   if self.badids:return [None]*len(p['notes'])
   ids=[]
   for note in p['notes']:
     nid=100+len(self.notes);fields={k:{'value':unicodedata.normalize('NFC',v) if self.normalize_on_write else v,'order':i} for i,(k,v) in enumerate(note['fields'].items())};self.notes[nid]={'noteId':nid,'modelName':note['modelName'],'cards':[nid],'fields':fields,'tags':note['tags']};ids.append(nid)
   return ids
  raise AssertionError(a)
def rows():return [{'line':1,'front':'Q','back':m.back_html('A','','module1'),'tags':['test']}]
class Tests(unittest.TestCase):
 def test_missing_dry_readonly(self):
  api=Fake(True);r=m.execute(rows(),'Test','Basic',api,True);self.assertEqual(r['would_add'],1);self.assertFalse(any(a.startswith(('add','create','update')) for a in api.actions))
 def test_create_then_confirm(self):
  api=Fake(True);r=m.execute(rows(),'Test','Basic',api,False);self.assertEqual(r['added'],1);self.assertIn('createModel',api.actions);self.assertIn('notesInfo',api.actions)
 def test_chinese_mapping(self):
  api=Fake(chinese=True);r=m.execute(rows(),'Test','Basic',api,False);self.assertEqual(r['model']['name'],'问答题');self.assertIn('正面',api.notes[100]['fields'])
 def test_reversed_rejected(self):
  self.assertIsNone(m.compatible(['Front','Back'],{'1':{'Front':'{{Front}}','Back':'{{Back}}'},'2':{'Front':'{{Back}}','Back':'{{Front}}'}}))
 def test_explicit_cloze_not_silently_converted(self):
  api=Fake();api.names=['Cloze','Basic'];api.fields=['Text','Extra']
  with self.assertRaisesRegex(m.ImportProblem,'静默'):m.resolve_model(api,'Cloze')
 def test_input_rejected(self):self.assertIsNone(m.compatible(['Front','Back'],{'1':{'Front':'{{Front}}{{type:Back}}','Back':'{{Back}}'}}))
 def test_idempotency(self):
  api=Fake();m.execute(rows(),'Test','Basic',api,False);r=m.execute(rows(),'Test','Basic',api,False);self.assertEqual(r['added'],0);self.assertEqual(len(api.notes),1)
 def test_changed_back_conflict(self):
  api=Fake();m.execute(rows(),'Test','Basic',api,False);r=rows();r[0]['back']='different'
  with self.assertRaisesRegex(m.ImportProblem,'内容不同'):m.execute(r,'Test','Basic',api,False)
 def test_nonduplicate_error(self):
  api=Fake();api.reject='cannot create note because it is empty'
  with self.assertRaisesRegex(m.ImportProblem,'empty'):m.execute(rows(),'Test','Basic',api,False)
  self.assertNotIn('addNotes',api.actions)
 def test_null_ids_unconfirmed(self):
  api=Fake();api.badids=True
  with self.assertRaisesRegex(m.ImportProblem,'未确认'):m.execute(rows(),'Test','Basic',api,False)
 def test_case_sensitive_math_answers(self):
  api=Fake();m.execute(rows(),'Test','Basic',api,False);r=rows();r[0]['back']=m.back_html('a','','module1')
  with self.assertRaisesRegex(m.ImportProblem,'内容不同'):m.execute(r,'Test','Basic',api,False)
 def test_unicode_normalization_readback(self):
  api=Fake(normalize_on_write=True);r=rows();r[0]['back']='A' + '\\u0304';self.assertEqual(m.execute(r,'Test','Basic',api,False)['added'],1)
 def test_excel_dollars_not_math(self):
  r,_=m.prepare([{'front':'复制=$B2*C$1','back':'=$B3*D$1','source':'Excel'}],'Test',[],m.parse_args(['x']))
  self.assertIn('$B2',r[0]['front'])
 def test_back_required(self):
  args=m.parse_args(['x']);
  with self.assertRaisesRegex(m.ImportProblem,'核心答案为空'):m.prepare([{'front':'Q','extra':'x','source':'module'}],'Test',[],args)
 def test_crossdeck_rejected(self):
  with self.assertRaisesRegex(m.ImportProblem,'跨科'):m.prepare([{'front':'Q','back':'A','source':'module','deck':'Wrong'}],'Test',[],m.parse_args(['x']))
 def test_math_no_br_inside(self):self.assertEqual(m.render_text('\\[a\n+b\\]'),'\\[a +b\\]')
 def test_html_escaped(self):self.assertEqual(m.render_text('<script>x</script>'),'&lt;script&gt;x&lt;/script&gt;')
 def test_dry_no_backup_file(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);src=root/'x.jsonl';src.write_text(json.dumps({'front':'Q','back':'A','source':'module1'}));cfg=root/'配置.json';cfg.write_text(json.dumps({'enabled':True,'deck':'Test','notetype':'Basic'}));dest=root/'已导入'/'x.tsv';old=m.request_anki;old_probe=m.ensure_anki_available;m.ensure_anki_available=lambda endpoint:'offline-test';api=Fake(True);m.request_anki=lambda a,p,e:api(a,p)
   try:
    with contextlib.redirect_stdout(io.StringIO()):rc=m.main([str(src),'--config',str(cfg),'--dry-run','--create-deck','--backup-tsv',str(dest)])
    self.assertEqual(rc,0);self.assertFalse(dest.parent.exists());self.assertNotIn('createDeck',api.actions)
   finally:m.request_anki=old;m.ensure_anki_available=old_probe
 def test_actual_existing_fields_export(self):
  api=Fake(chinese=True);m.execute(rows(),'Test','Basic',api,False);r=m.execute(rows(),'Test','Basic',api,False)
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'x.tsv';m.write_confirmed(p,r,'hash');self.assertIn('#columns:正面\t背面',p.read_text());self.assertEqual(json.loads(p.with_suffix('.result.json').read_text())['notes'][0]['note_id'],100)
 def test_remote_endpoint_is_refused_before_request(self):
  with self.assertRaisesRegex(m.ImportProblem,'local'):m.request_anki('version',{},'https://example.com')
 def test_disabled_configuration_never_probes_anki(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);src=root/'x.jsonl';src.write_text(json.dumps({'front':'Q','back':'A','source':'module'}));cfg=root/'config.json';cfg.write_text(json.dumps({'enabled':False,'deck':'Test'}));old=m.ensure_anki_available
   def forbidden(endpoint):raise AssertionError('Must not connect when disabled')
   m.ensure_anki_available=forbidden
   try:
    with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(m.main([str(src),'--config',str(cfg)]),2)
   finally:m.ensure_anki_available=old
 def test_export_conflict_does_not_write_output(self):
  import build_anki_import as exporter
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);src=root/'x.json';src.write_text(json.dumps([{'front':'Q','back':'A'},{'front':'Q','back':'B'}]));out=root/'x.tsv'
   with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(exporter.main([str(src),'--output',str(out)]),2)
   self.assertFalse(out.exists())
 def test_export_cannot_overwrite_source(self):
  import build_anki_import as exporter
  with tempfile.TemporaryDirectory() as td:
   src=Path(td)/'x.json';src.write_text(json.dumps([{'front':'Q','back':'A'}]));before=src.read_bytes()
   with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(exporter.main([str(src),'--output',str(src)]),2)
   self.assertEqual(before,src.read_bytes())
 def test_export_valid_card_keeps_tags(self):
  import build_anki_import as exporter
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);src=root/'x.json';src.write_text(json.dumps([{'front':'Q','back':'A','source':'module','tags':['topic']}]))
   out=root/'x.tsv'
   with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(exporter.main([str(src),'--output',str(out)]),0)
   self.assertIn('topic',out.read_text())
if __name__=='__main__':unittest.main()
