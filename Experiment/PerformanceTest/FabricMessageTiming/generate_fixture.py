import os,sys,json,copy,re,argparse,shutil,subprocess,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
sys.path.insert(0,str(PROJECT/'src/backend'));os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django;django.setup()
from apps.core.models import BPMN
from apps.core.services.new_translator import NewTranslatorClient
parser=argparse.ArgumentParser(description='Generate an isolated repeatable file fixture using the current translator')
parser.add_argument('--owner-bpmn',required=True)
args=parser.parse_args()
out=ROOT/'deployment';out.mkdir(exist_ok=True)
assert not (out/'deployment.json').exists(), 'Do not regenerate a deployed fixture'
b=BPMN.objects.get(pk=args.owner_bpmn);root=ET.fromstring(b.bpmnContent);ns='{http://www.omg.org/spec/BPMN/20100524/MODEL}'
for node in list(root):
 if node.tag==ns+'message' and node.get('id')=='Message_1wswgqu':
  schema=next(v for v in node.iter() if v.tag.endswith('MessageSchema'))
  # A declared scalar prevents Fabric contract-api v1.1.1 rejecting an empty
  # generated StateMemory schema. File definition remains untouched.
  abc='{https://chaincollab.io/schema/abc}'
  ET.SubElement(schema,abc+'Property',{'name':'requestId','type':'number','required':'true',
      'description':'Fixed experiment request number','definition':json.dumps({'type':'number','description':'Fixed experiment request number'})})
  continue
 if node.tag==ns+'choreography':
  keep={'Participant_0w6qkdf','Participant_19mgbdn','MessageFlow_06374xt','Event_06sexe6','ChoreographyTask_0tyax7p','Flow_1btgvf6'}
  for child in list(node):
   if child.get('id') not in keep:node.remove(child)
  ET.SubElement(node,ns+'sequenceFlow',{'id':'Flow_timingEnd','sourceRef':'ChoreographyTask_0tyax7p','targetRef':'Event_timingEnd'})
  end=ET.SubElement(node,ns+'endEvent',{'id':'Event_timingEnd'});ET.SubElement(end,ns+'incoming').text='Flow_timingEnd'
  for child in node.iter(ns+'outgoing'):
   if child.text=='Flow_06esz8k':child.text='Flow_timingEnd'
  continue
 root.remove(node)
xml=ET.tostring(root,encoding='unicode');(out/'FabricFileTiming.bpmn').write_text(xml)
art=NewTranslatorClient().generate_artifacts(xml,'go',artifact_name='FabricFileTiming',persist_to_runtime=False)
(out/'generated-artifacts.json').write_text(json.dumps(art,indent=2))
code=art['chaincodeContent'];(out/'generated.go').write_text(code)
pattern=r'(func \(cc \*SmartContract\) Message_1wswgqu_Send\([^\n]+\n)(.*?)(\n\})'
m=re.search(pattern,code,re.S);assert m
body=m[2];body,n=re.subn(r'^\s*cc\.ChangeMsgState\(ctx, instance, [^\n]+\)\s*$', '', body,flags=re.M);assert n==1,(n,body)
assert not re.search(r'cc\.Change(?:Event|Gtw|BusinessRule)State',body)
code=code[:m.start()]+m[1]+body+m[3]+code[m.end():]
(out/'smartcontract.go').write_text(code)
(out/'ffi.json').write_text(art['ffiContent'])
print('Generated:',len(code.splitlines()),'lines; repeatable Send:');print(body)
print('IMPORTS',code[:700])
module=out/'source'/'fabric-file-timing';(module/'chaincode').mkdir(parents=True,exist_ok=True)
shutil.copy2(out/'smartcontract.go',module/'chaincode/smartcontract.go')
template=PROJECT/'src/backend/opt/chaincode-go-bpmn/chaincode-go-bpmn'
for name in ['go.sum','bpmnChoreography.go']:shutil.copy2(template/name,module/name)
mod=(template/'go.mod').read_text()
(module/'go.mod').write_text('\n'.join(line for line in mod.splitlines() if 'IBC/Oracle' not in line)+'\n')
for cmd in [['go','mod','tidy'],['go','test','./...']]:
 subprocess.run(cmd,cwd=module,env={**os.environ,'GOWORK':'off'},check=True)
with zipfile.ZipFile(out/'FabricFileTiming.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
 for p in module.rglob('*'):
  if p.is_file():archive.write(p,p.relative_to(out/'source'))
