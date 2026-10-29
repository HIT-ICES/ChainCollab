import sys, json, runpy, hashlib, inspect, traceback
from pathlib import Path
O=Path(sys.argv[1]);T=Path('/home/shenxz-lab/code/ChainCollab/src/newTranslator');reads=[]
def audit(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)):
  reads.append({'path':str(args[0]),'mode':str(args[1]),'flags':args[2]})
sys.addaudithook(audit)
def dump(name,x):
 p=O/'generation_contexts'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def typed(x,path='$',seen=None):
 if seen is None:seen={}
 t=type(x).__module__+'.'+type(x).__name__
 if x is None or isinstance(x,(str,int,float,bool)):return {'type':t,'value':x}
 if id(x) in seen:return {'type':t,'ref':seen[id(x)]}
 seen[id(x)]=path
 if isinstance(x,dict):return {'type':t,'entries':[{'key':typed(k,path+'.key',seen),'value':typed(v,path+'.'+str(k),seen)} for k,v in x.items()]}
 if isinstance(x,(list,tuple)):return {'type':t,'items':[typed(v,path+f'[{i}]',seen) for i,v in enumerate(x)]}
 return {'type':t,'attributes':{k:typed(v,path+'.'+k,seen) for k,v in vars(x).items() if not k.startswith('_tx') and k!='parent'},'omitted':['parent','_tx*']}
# Native APIs with observation only: return each actual context unchanged.
import b2cdsl_go as go, b2cdsl_solidity as sol
from jinja2 import Template
original_render=Template.render;calls=[]
def render(self,*args,**kw):
 calls.append({'template':self.name,'context':typed(dict(*args,**kw))})
 return original_render(self,*args,**kw)
Template.render=render
locations={}
for label,cls in [('fabric',go.GoChaincodeRenderer),('geth',sol.SolidityRenderer)]:
 original=cls.build_context
 locations[label]={'renderer':inspect.getfile(cls),'build_context_line':inspect.getsourcelines(original)[1]}
 def wrap(self,_original=original,_label=label):
  ctx=_original(self);dump(_label+'.context.typed.json',typed(ctx))
  try:dump(_label+'.context.json',ctx)
  except TypeError:pass
  return ctx
 cls.build_context=wrap
original_layout=sol.SolidityRenderer.build_execution_layout
def layout(self):
 result=original_layout(self);dump('geth.execution_layout.diagnostic.json',result);return result
sol.SolidityRenderer.build_execution_layout=layout
try:
 sys.argv=[str(T/'generator/bpmn_to_dsl.py'),str(O/'source_models/SupplyChainPaper.bpmn'),'-o',str(O/'generation_contexts/SupplyChainPaper.audit.b2c')]
 try:runpy.run_path(str(T/'generator/bpmn_to_dsl.py'),run_name='__main__')
 except SystemExit as e:
  if e.code:raise
 dump('A_file_reads.json',reads.copy());reads.clear()
 from generator.translator import _load_b2c_metamodel, _render_solidity_contract
 b2c=O/'pim/SupplyChainPaper.b2c';mm=_load_b2c_metamodel();model=mm.model_from_file(str(b2c))
 d=O/'generation_contexts/fabric_sidecar';d.mkdir(exist_ok=True)
 go.generator_callback(model,str(d/'SupplyChainPaper.go'))
 dump('fabric.template_calls.typed.json',calls.copy());calls.clear();dump('B_file_reads.json',reads.copy());reads.clear()
 out=_render_solidity_contract(b2c.read_text());(O/'generation_contexts/SupplyChainPaper.sidecar.sol').write_text(out)
 dump('geth.template_calls.typed.json',calls.copy());dump('C_file_reads.json',reads.copy())
 pairs=[(O/'pim/SupplyChainPaper.b2c',O/'generation_contexts/SupplyChainPaper.audit.b2c'),(O/'fabric/raw/SupplyChainPaper.go',d/'SupplyChainPaper.go'),(O/'geth/raw/SupplyChainPaper.sol',O/'generation_contexts/SupplyChainPaper.sidecar.sol')]
 comparison=[{'native':str(a.relative_to(O)),'diagnostic':str(b.relative_to(O)),'native_sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'diagnostic_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'identical':a.read_bytes()==b.read_bytes()} for a,b in pairs]
 dump('native_sidecar_comparison.json',comparison);dump('source_locations.json',locations)
 assert all(x['identical'] for x in comparison)
 print('Contexts exported; all native / diagnostic outputs byte-identical.')
finally:
 dump('serialization_notes.json',{'purpose':'generation-context diagnostic dump; not a native PSM or external profile','method':'wrap original build_context and Jinja Template.render, return original unchanged; record runtime Python types and all context entries','object_limitations':'For non-JSON textX objects, parent and _tx internals omitted to avoid cycles; repeated references retain ref paths. Plain context JSON is lossless when present. Read audit observes Python open events, not OS syscalls.'})
