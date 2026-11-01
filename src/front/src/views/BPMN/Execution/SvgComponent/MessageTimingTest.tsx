import { useState } from "react";
import { Alert, Button, Input, InputNumber, Modal, Space, Table, Typography } from "antd";
import { runMessageTimingExperiment, type TimingContext } from "@/api/messageTimingExperiment";

export default function MessageTimingTest({ context, disabled }: { context: Omit<TimingContext, "rounds" | "progress">; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  const [rounds, setRounds] = useState(3);
  const [file, setFile] = useState<File>();
  const [receiverCoreUrl, setReceiverCoreUrl] = useState("");
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState("");
  const [report, setReport] = useState<any>(null);
  const download = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = "geth_message_ipfs_test_result.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <>
    <Button disabled={disabled} onClick={() => setOpen(true)} style={{ marginBottom: 12 }}>测试模式</Button>
    <Modal title="Message 分阶段耗时实验（Geth）" open={open} width={760}
      onCancel={() => !running && setOpen(false)} maskClosable={!running}
      footer={<Space><Button disabled={!report || running} onClick={download}>导出结果</Button>
        <Button type="primary" loading={running} disabled={disabled || !receiverCoreUrl.trim()} onClick={async () => {
          setRunning(true); setReport(null);
          try { setReport(await runMessageTimingExperiment({ ...context, rounds, file, receiverCoreUrl: receiverCoreUrl.trim(), progress: setProgress })); }
          finally { setRunning(false); }
        }}>Test</Button></Space>}>
      <Typography.Paragraph>使用当前已部署链码，保留页面原实例。文件上传后在后台发布IPFS，取得Message ID即发起合约调用；分别等待并核验两条链路。每轮使用独立测试实例和不同内容的1 KiB文件。</Typography.Paragraph>
      <Typography.Text>接收方 FireFly Core URL</Typography.Text>
      <Input aria-label="接收方 FireFly Core URL" placeholder="http://127.0.0.1:5002" value={receiverCoreUrl}
        disabled={running} onChange={event => setReceiverCoreUrl(event.target.value)} style={{ marginBottom: 12 }} />
      <Space wrap>测试次数 <InputNumber min={1} max={100} value={rounds} disabled={running} onChange={value => setRounds(value || 1)} />
        <input aria-label="实验文件" type="file" disabled={running} onChange={event => setFile(event.target.files?.[0])} /></Space>
      <Typography.Paragraph style={{ marginTop: 12 }}>{progress}</Typography.Paragraph>
      {report && <><Alert type={report.status === "passed" ? "success" : report.status === "completed_with_warnings" ? "warning" : "error"}
        message={report.status === "passed" ? "实验完成" : report.status === "completed_with_warnings" ? "执行验证完成；部分时间戳倒置，异常阶段不纳入统计。原始值已保留。" : report.error} />
        <Table size="small" pagination={false} rowKey="key" scroll={{ y: 420 }} dataSource={[...report.samples.flatMap((sample: any) =>
          (sample.stages || []).map((stage: any) => ({ key: `${sample.index}-${stage.step}`, round: sample.index, step: stage.step, ms: stage.available === false ? "N/A（未观测到 IPFS 上传）" : `${stage.duration_ms.toFixed(2)}${stage.valid === false ? "（异常）" : ""}` }))),
          ...(report.summary || []).map((row: any) => ({ key: `mean-${row.step}`, round: "平均", step: row.step, ms: row.mean_ms == null ? "N/A" : row.mean_ms.toFixed(2) }))]}
          columns={[{ title: "轮次", dataIndex: "round" }, { title: "阶段", dataIndex: "step" }, { title: "耗时（ms）", dataIndex: "ms" }]} />
        <Typography.Text type="secondary">蓝色：文件上传至参与组织同步/pin完成。黄色：FireFly→IPFS内部调用。绿色：合约请求开始至Operation创建。红色：同一Operation创建至对应业务调用成功事件。</Typography.Text></>}
    </Modal>
  </>;
}
