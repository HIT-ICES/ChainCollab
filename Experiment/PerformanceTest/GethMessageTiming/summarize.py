"""Verify saved measurements and export statistics offline, without transactions."""
import argparse
import copy
import csv
import json
from pathlib import Path
from statistics import mean, median
import sys

ROOT = Path(__file__).resolve().parent
PHASES = ['Private Data Bus', 'IPFS', 'API Invoker', 'BPMN SC']


def export_report(report, output):
    output = Path(output)
    assert report['status'] == 'passed'
    samples = report['samples']
    assert [s['index'] for s in samples] == list(range(1,len(samples)+1))
    assert all(s['status'] == 'passed' for s in samples)
    selection=report.get('sampleSelection', {})
    limit=selection.get('maxRed_ms')
    if limit is not None:
        assert len(samples)==selection['targetAcceptedCount']==selection['acceptedCount']
        assert all(next(v['duration_ms'] for v in s['stages'] if v['step']=='BPMN SC')<=limit for s in samples)
    repeat = report.get('executionMode') == 'existing-contract-same-enabled-instance'
    if repeat:
        state_keys = [k for k in report['originalInstanceBefore'] if k.endswith('States') or k == 'businessRuleRequestIds']
        assert all(report['originalInstanceBefore'][k] == report['originalInstanceAfter'][k] for k in state_keys)
        assert report['counterBefore'] == report['counterAfter']
        assert len({s['instanceId'] for s in samples}) == 1
    summary=[]
    for name in PHASES:
        values=[next(v['duration_ms'] for v in s['stages'] if v['step']==name) for s in samples]
        summary.append({'step':name,'count':len(values),'mean_ms':mean(values),'median_ms':median(values),'min_ms':min(values),'max_ms':max(values)})
    # Replay the wall-clock corrections from the actual retained sampling pairs.
    sys.path.insert(0,str(ROOT/'metric-audit'))
    from monotonic_clock import normalize
    pairs=sorted({tuple(v) for s in samples for v in s['clockNormalization']['clockPairs']},key=lambda v:v[1])
    replay=copy.deepcopy(report)
    for s in replay['samples']:s['stages']=s['stagesBeforeClockNormalization']
    normalize(replay,pairs)
    verification=[]
    for s,t in zip(samples,replay['samples']):
        assert s['executionVerified']
        for a,b in zip(s['stages'],t['stages']):assert abs(a['duration_ms']-b['duration_ms']) < .001
        phases={v['step']:v for v in s['stages']}
        assert phases['API Invoker']['end_time'] == phases['BPMN SC']['start_time']
        assert all(v['valid'] and v['duration_ms']>=0 for v in s['stages'])
        if report.get('metricsVersion',0)>=9:
            assert s['receiverFileSha256'] == s['ipfsFileSha256'] == s['file']['sha256']
            publish_ms=s['ipfsPublishRequest']['clock']['rawEnd']-s['ipfsPublishRequest']['clock']['rawStart']
            assert abs(phases['IPFS']['duration_ms']-publish_ms)<.001
            assert s['ipfsUploadOperation']['status']=='Succeeded'
            assert s['ipfsUploadOperation']['output']['payloadRef']==s['ipfsCid']
            assert s['senderPublishedData']['blob']['public']==s['ipfsCid']
            assert s['snapshotAfter']['messageStates']==s['snapshotBefore']['messageStates']
            verification.append({'round':s['index'],'instanceId':s['instanceId'],'messageId':s['messageId'],
                'dataId':s['fileCidMapping']['dataId'],'cid':s['ipfsCid'],'sha256':s['file']['sha256'],
                'messageStateAfter':s['snapshotAfter']['messageStates'],'operationId':s['operation']['id'],
                'businessTransactionHash':s['operation']['output']['transactionHash'],
                'clockReplayPassed':True,'greenRedBoundaryIdentical':True,
                'uploadReceiverIpfsContentsIdentical':True})
    report['summary']=summary
    (output/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (output/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    with (output/'timings.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['round','instanceId','stage','start_offset_ms','end_offset_ms','duration_ms'])
        for s in samples:
            folder=output/f"round-{s['index']}";folder.mkdir(exist_ok=True)
            (folder/'result.json').write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n')
            for v in s['stages']:w.writerow([s['index'],s['instanceId'],v['step'],v['start_time']-s['fileUpload']['start'],v['end_time']-s['fileUpload']['start'],v['duration_ms']])
    selection_text=(f"共执行{selection['totalAttempts']}次尝试，按预设红色阈值≤{limit/1000:g}秒保留{len(samples)}轮；"
        f"排除红色超阈值{selection['excludedHighRedCount']}次、无效计时{selection['excludedInvalidTimingCount']}次。下表是筛选后结果，不代表未经筛选的全体延迟。"
        if limit is not None else f"{len(samples)}轮全部成功，原轮次完整保留，不筛除慢样本。")
    lines=['# 同一 Message 连续调用：分阶段耗时结果','',
        selection_text+f"合约 `{report.get('contractAddress', '')}`，方法 `{report.get('targetMessage', '')}_Send`，实例 `{samples[0]['instanceId']}`。",'',
        '![均值时间线](geth_message_timeline_mean.png)','',
        '| 阶段 | 平均(ms) | 中位数(ms) | 最小(ms) | 最大(ms) |','|---|---:|---:|---:|---:|']
    for v in summary:lines.append(f"| {v['step']} | {v['mean_ms']:.2f} | {v['median_ms']:.2f} | {v['min_ms']:.2f} | {v['max_ms']:.2f} |")
    lines+=['','| 轮次 | 实例 | 蓝(ms) | 黄(ms) | 绿(ms) | 红(ms) |','|---|---:|---:|---:|---:|---:|']
    for s in samples:lines.append(f"| {s['index']} | {s['instanceId']} | "+' | '.join(f"{v['duration_ms']:.2f}" for v in s['stages'])+' |')
    lines+=['',
        '蓝：自动化客户端开始向现有prepare-file-message接口上传文件，至双方消息确认、batch pin成功和IPFS发布完成的最晚时间。接收端文件哈希核验作为正确性检查，不额外计入哈希计算耗时。',
        '黄：向FireFly发起blob/publish请求，至成功响应返回CID；核验对应上传Operation为Succeeded，dataId、CID、blob.public及文件内容一致。黄色覆盖发布请求、排队、上传、发布处理，不再使用内部/add调用耗时代替。',
        '绿：业务合约HTTP请求开始至匹配的Operation.created；红：同一Operation.created至匹配Operation ID和事务ID的blockchain_invoke_op_succeeded事件.created。红绿严格衔接；红色包含调度、上链等待和成功事件处理，不是纯EVM执行。','',
        '脚本调用与用户新增上传控件相同的认证后端接口。该接口完成文件上传并返回真实MessageID后，实验显式发起IPFS发布，并立即调用业务合约；两条请求不互相等待完成。私有传输仍由原有dataexchange路径完成。',
        '计时客户端为Python HTTP脚本，非人工点击或浏览器渲染耗时。客户端使用单调时钟，服务端时间戳通过5ms连续wall/monotonic采样映射；原始时间和校准样本保留。Fabric比较时也应采用同一客户端和边界。','',
        '所有测量使用同一已有实例；每轮Message仍为ENABLED，其他节点状态不变，仅更新链上最新FireFly Message ID。currentInstanceId计数器前后相同，未创建新实例。',
        f"发送端：`{report['participatingFireflyCores'][0]}`；接收端：`{report['participatingFireflyCores'][1]}`。",'',
        '每轮默认新生成1KiB不同内容的文件，CID不同。IPFS网关及接收端读回内容均与上传字节一致；业务Operation、MessageSent事件及链上最新MessageID匹配。',
        'results.json为完整数据；round-N/result.json为单轮数据；timings.csv为逐段起止偏移；verification.json保存核验摘要。summary.json为汇总。','']
    if report.get('attempts'):
        raw_values={name:[] for name in PHASES}
        with (output/'attempts.csv').open('w',newline='') as stream:
            writer=csv.writer(stream)
            writer.writerow(['attempt','status','acceptedRound','blue_ms','yellow_ms','green_ms','red_ms','reason','messageId','operationId'])
            for entry in report['attempts']:
                record=json.loads((output/entry['rawFile']).read_text())
                assert record['attempt']==entry['attempt'] and record['status']==entry['status']
                durations={v['step']:v['duration_ms'] for v in record.get('stages',[])} if record['status']!='excluded_invalid_timing' else {}
                if durations:
                    for name in PHASES:raw_values[name].append(durations[name])
                writer.writerow([entry['attempt'],entry['status'],record['index'] if record['status']=='passed' else '',
                    *(durations.get(name,'') for name in PHASES),entry.get('reason'),entry.get('messageId'),entry.get('operationId')])
        raw_summary=[{'step':name,'count':len(values),'mean_ms':mean(values),'median_ms':median(values),'min_ms':min(values),'max_ms':max(values)} for name,values in raw_values.items() if values]
        (output/'summary-all-attempts.json').write_text(json.dumps(raw_summary,indent=2)+'\n')
        lines+=['','筛选规则及计数保存在results.json的sampleSelection。attempts.json和attempts.csv列出全部尝试；attempts/attempt-NNNN/result.json保留每次原始数据，排除样本不参与正式summary或均值图。summary-all-attempts.json为所有可正确计时尝试的未筛选汇总。','']
    (output/'RESULTS.md').write_text('\n'.join(lines))
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'results-100/results.json')
    args=parser.parse_args();report=json.loads(args.input.read_text())
    export_report(report,args.input.parent)
    print(f"Verified and exported {len(report['samples'])} saved rounds; no transactions sent.")


if __name__=='__main__':main()
