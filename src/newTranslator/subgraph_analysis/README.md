# Subgraph (SESE) 扫描算法

以下伪代码描述“扫描 BPMN→DAG→SESE 子图”的核心步骤，可直接用于论文或技术说明。

```text
Algorithm ScanSESESubgraphs(BPMNFile)
Input:
  BPMNFile: BPMN XML file
Output:
  Regions: list of SESE subgraphs (entry, exit, nodes)

1. G ← parse BPMN into directed graph (ignore participant/message nodes)
2. if G has cycles:
     SCCs ← strongly connected components of G
     G' ← condensed DAG by SCCs
   else:
     G' ← G
3. Regions ← ∅
4. Precompute Descendants[n] and Ancestors[n] for all nodes in G'
5. for each entry in G':
       for each exit in Descendants[entry]:
           Region ← (Descendants[entry] ∪ {entry}) ∩ (Ancestors[exit] ∪ {exit})
           if Region size < 2: continue
           EntryNodes ← {v ∈ Region | ∃pred(v) ∉ Region}
           ExitNodes  ← {v ∈ Region | ∃succ(v) ∉ Region}
           if EntryNodes = {entry} and ExitNodes = {exit}:
               add (entry, exit, Region) to Regions
6. if G was condensed:
       expand each Region from components back to original nodes
7. return Regions
```

说明：
- **SESE (Single-Entry Single-Exit)**：子图内部节点仅与子图内相连，只有一个入口接收外部控制，只有一个出口对外输出。
- 当 BPMN 含环时，先做 **SCC 压缩**，在压缩 DAG 上识别 SESE，再展开回原节点集合。
