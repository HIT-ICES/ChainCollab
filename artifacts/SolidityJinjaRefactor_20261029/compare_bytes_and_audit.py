from pathlib import Path
import hashlib, json, csv, difflib, ast, subprocess, shutil
r=Path('/home/shenxz-lab/code/ChainCollab');e=r/'artifacts/SolidityJinjaRefactor_20261029'
rows=[];diffs=[]
a=json.loads((e/'baseline.sha256.json').read_text());b=json.loads((e/'after_layout.sha256.json').read_text());assert a.keys()==b.keys()
for name in sorted(a):
 before=(e/'baseline'/name).read_bytes();after=(e/'after_layout'/name).read_bytes();repeat=(e/'baseline_repeat'/name).read_bytes()
 row={'file':name,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(after).hexdigest(),'baseline_repeat_byte_equal':before==repeat,'before_after_byte_equal':before==after,'bytes':len(before)}
 rows.append(row)
 if before!=after:diffs.append(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='baseline/'+name,tofile='after_layout/'+name)))
assert all(x['baseline_repeat_byte_equal'] and x['before_after_byte_equal'] for x in rows)
with (e/'byte_comparison.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(e/'byte_comparison.json').write_text(json.dumps({'method':'Direct bytes equality (no normalization), plus SHA256','files':len(rows),'matched':len(rows)-len(diffs),'differences':len(diffs),'rows':rows},indent=2)+'\n')
(e/'generation.diff').write_text(''.join(diffs))
source=r/'src/newTranslator/CodeGenerator';changes=[]
for p in [source/'b2cdsl-solidity/b2cdsl_solidity/__init__.py',source/'b2cdsl-go/b2cdsl_go/__init__.py']:
 tree=ast.parse(p.read_text());skeletons=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.JoinedStr):
   text=''.join(v.value for v in node.values if isinstance(v,ast.Constant))
   if 'function ' in text or 'func (cc *SmartContract)' in text:skeletons.append(node.lineno)
 assert not skeletons,(p,skeletons)
 changes.append(p)
changes+=list((source/'b2cdsl-solidity/templates/flows').glob('*.jinja'))
changes+=list((source/'b2cdsl-solidity/templates/actions').glob('*.jinja'))
changes+=[source/'b2cdsl-go/templates/flows/oracle_task.go.jinja']
source_manifest={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in changes}
(e/'after_source.sha256.json').write_text(json.dumps(source_manifest,indent=2)+'\n')
(e/'code.diff').write_bytes(subprocess.check_output(['git','diff','--','src/newTranslator/CodeGenerator'],cwd=r))
for p in changes:
 target=e/'after_source'/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
(e/'audit.json').write_text(json.dumps({'python_function_skeleton_fstrings_remaining':0,'new_flow_templates':[str(p.relative_to(r)) for p in changes if p.suffix=='.jinja'],'businessrule_request_continue':'Already Jinja in unchanged Solidity contract.sol.jinja lines 717-799 and Go contract.go.jinja; no runtime change','existing_generator_tests':'Before refactor Go/Solidity/DSL test directories contained only .dummy; unittest discovery of existing Go/DSL returns 0 tests. Added 3 golden regression tests.'},indent=2)+'\n')
print('Direct comparison: all',len(rows),'files byte-identical; generation.diff is empty; function f-string skeleton audit PASS')
for platform,ext in [('go','go'),('solidity','sol')]:
 p='structured/SupplyChainPaper/'+platform+'/SupplyChainPaper.'+ext
 print(p, a[p])
