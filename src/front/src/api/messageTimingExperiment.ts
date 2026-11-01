// Experimental port of the Fabric Message timing test (c304405f / 4ede3eb7).
// Normal execution APIs deliberately do not call this module.
export type TimingContext = {
  apiBaseUrl: string;
  signer: string;
  elementsFromSnapshot: (snapshot: any) => any[];
  payloadForMessage: (element: any, instanceId: number) => Record<string, any>;
  rounds: number;
  file?: File;
  receiverCoreUrl?: string;
  protectedInstanceId?: number;
  progress?: (text: string) => void;
};

const pause = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
const stamp = (value: string | number) => typeof value === "number" ? value : Date.parse(value);
const deadlineMs = 120000;

async function clockSync() {
  const before = performance.timeOrigin + performance.now();
  const value = await request("http://127.0.0.1:8791/clock");
  const after = performance.timeOrigin + performance.now();
  return { ...value, browserBefore: before, browserAfter: after };
}

async function request(url: string, body?: any): Promise<any> {
  const response = await fetch(url, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined || body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    signal: AbortSignal.timeout(deadlineMs),
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`${response.status} ${url}: ${text}`);
  return text ? JSON.parse(text) : null;
}

async function until(label: string, get: () => Promise<any>, accept: (value: any) => boolean) {
  const deadline = performance.now() + deadlineMs;
  while (performance.now() < deadline) {
    const value = await get();
    if (accept(value)) return value;
    await pause(250);
  }
  throw new Error(`Timed out waiting for ${label}`);
}

// Use the browser's actual Resource Timing, matching the old TimeDecorator.
// Resource entries are read after the response body, without the old 300ms delay.
async function timed(url: string, body: any) {
  const before = performance.now();
  const wallOriginBefore = Date.now() - before;
  const value = await request(url, body);
  const wallOriginAfter = Date.now() - performance.now();
  await pause(0);
  const entry = (performance.getEntriesByName(url, "resource") as PerformanceResourceTiming[])
    .filter(item => item.startTime >= before).at(-1);
  if (!entry) throw new Error(`No browser resource timing for ${url}`);
  // On this VM the monotonic clock can drift from Date.now() during long block
  // waits. Anchor each short request locally rather than reusing page-load time.
  const wallOrigin = (wallOriginBefore + wallOriginAfter) / 2;
  return { value, start: wallOrigin + entry.fetchStart, end: wallOrigin + entry.responseEnd,
    clock: { wallOriginBefore, wallOriginAfter, drift_ms: wallOriginAfter - wallOriginBefore,
      rawStart: performance.timeOrigin + entry.fetchStart, rawEnd: performance.timeOrigin + entry.responseEnd } };
}

async function operation(core: string, initial: any) {
  if (!initial?.id) throw new Error("Invoke did not return an Operation id");
  return until(`operation ${initial.id}`, () => request(`${core}/operations/${initial.id}?fetchstatus=true`), op => {
    if (op.status === "Failed") throw new Error(`Operation failed: ${JSON.stringify(op)}`);
    return op.status === "Succeeded";
  });
}

export async function runMessageTimingExperiment(context: TimingContext) {
  const sourceApi = context.apiBaseUrl.replace(/\/$/, "");
  const core = sourceApi.split("/apis/")[0];
  const api = sourceApi;
  if (!core.includes("/namespaces/") || core === sourceApi) throw new Error("Invalid registered FireFly API URL");
  if (!context.receiverCoreUrl) throw new Error("Specify the receiving FireFly Core URL");
  const receiverCore = `${context.receiverCoreUrl.replace(/\/$/, "")}/api/v1/namespaces/default`;
  if (!context.signer) throw new Error("Select an Ethereum signer first");
  if (!Number.isInteger(context.rounds) || context.rounds < 1 || context.rounds > 100) throw new Error("Rounds must be 1–100");
  const report: any = {
    startedAt: new Date().toISOString(), platform: "geth", api, sourceApi, signer: context.signer,
    legacySource: "c304405f:src/front/src/views/BPMN/Execution/SvgComponent/index.tsx",
    metricsVersion: 8,
    executionMode: "existing-contract-fresh-instance-per-round",
    scheduling: "Start IPFS publication in background; invoke Message_Send immediately after private Message ID is returned; join completion only afterward",
    instanceIds: [],
    metrics: { "Private Data Bus": "File upload request start → both participating FireFly organizations confirm the file message, including batch pin",
      "IPFS": "Audited internal FireFly→IPFS /api/v0/add HTTP call",
      "API Invoker": "Message_Send HTTP request start → correlated FireFly Operation.created",
      "BPMN SC": "The same Operation.created → correlated blockchain_invoke_op_succeeded event.created" },
    browserClock: "Resource Timing anchored to Date.now() per request; raw page-origin timestamps retained",
    samples: [], status: "running",
  };
  const note = (text: string) => context.progress?.(text);
  try {
    note("准备实验实例与 MessageSent 监听器");
    const interfaceDef = await request(`${api}/interface`);
    const apis = await request(`${core}/apis`);
    const registered = apis.find((item: any) => item.name === interfaceDef.name);
    if (!registered) throw new Error("Registered contract API not found");
    const sourceRegistered = apis.find((item: any) => item.name === sourceApi.split("/apis/")[1]);
    if (!sourceRegistered) throw new Error("Source contract API not found");
    const ownerResult = await request(`${api}/query/owner`, { input: {} });
    const owner = ownerResult.ret0 ?? ownerResult.output;
    if (typeof owner !== "string") throw new Error("Cannot resolve experiment contract owner");
    // Reuse the deployed model's initialization, creating new instances only.
    const operations = await request(`${core}/operations?type=blockchain_invoke&limit=1000`);
    const template = operations.find((op: any) => op.status === "Succeeded" &&
      op.input?.methodPath === "createInstance" &&
      op.input?.location?.address?.toLowerCase() === sourceRegistered.location.address.toLowerCase());
    if (!template) throw new Error("No successful createInstance template for this contract");
    const status = await request(`${core}/status`);
    const identities = await request(`${core}/identities?type=org&limit=100`);
    const receiverStatus = await request(`${receiverCore}/status`);
    const recipient = identities.find((item: any) => item.type === "org" && item.did === receiverStatus.org.did && item.did !== status.org.did);
    if (!recipient) throw new Error("No remote FireFly organization for private transfer");
    const listenerName = `message-timing-${registered.id.slice(0, 8)}`;
    const messageSent = interfaceDef.events?.find((event: any) => event.name === "MessageSent");
    if (!messageSent?.params?.length) throw new Error("MessageSent event definition is missing");
    let listener = (await request(`${core}/contracts/listeners?limit=1000`))
      .find((item: any) => item.name === listenerName);
    if (!listener) listener = await request(`${core}/contracts/listeners`, {
      name: listenerName, interface: { id: registered.interface.id },
      location: registered.location, event: { name: messageSent.name, params: messageSent.params },
      topic: listenerName, options: { firstEvent: "newest" },
    });
    if (listener.signature !== "MessageSent(uint256,uint8,string)") throw new Error(`Unexpected listener signature: ${listener.signature}`);
    report.listener = listener;
    report.recipient = recipient.did;
    report.participatingFireflyCores = [core, receiverCore];
    const file = context.file || new File(["x".repeat(1024)], "message-timing-1KiB.txt", { type: "text/plain" });
    report.file = { name: file.name, bytes: file.size };
    report.filePolicy = context.file ? "User-selected file, bytes preserved; cached IPFS publication excluded" : "Fresh 1 KiB text per round with unique nonce to avoid upload-cache reuse";
    const invoke = (method: string, input: any, key = context.signer) => request(`${api}/invoke/${method}`, { input, key });
    if (context.protectedInstanceId != null) {
      report.protectedInstanceId = context.protectedInstanceId;
      report.originalInstanceBefore = await request(`${api}/query/getExecutionSnapshot`, { input: { instanceId: context.protectedInstanceId } });
    }
    report.preparations = [];
    for (let index = 0; index < context.rounds; index++) {
      note(`创建测试实例 ${index + 1}/${context.rounds}（当前已部署链码）`);
      const counter = await request(`${api}/query/currentInstanceId`, { input: {} });
      const instanceId = Number(counter.ret0 ?? counter.output);
      if (!Number.isSafeInteger(instanceId) || instanceId === context.protectedInstanceId) throw new Error("Invalid test instance counter");
      report.instanceIds.push(instanceId);
      const preparation: any = { instanceId, index: index + 1, actions: [] };
      report.preparations.push(preparation);
      preparation.createOperation = await operation(core, await invoke("createInstance", template.input.input, owner));
    }
    // Prepare disposable instances in parallel, before any measured run starts.
    await Promise.all(report.preparations.map(async (preparation: any) => {
      const { instanceId } = preparation;
      const snapshot = () => request(`${api}/query/getExecutionSnapshot`, { input: { instanceId } });
      for (let step = 0; step < 40; step++) {
        const current = await snapshot();
        const elements = context.elementsFromSnapshot(current);
        const enabled = elements.filter(item => Number(item.state) === 1);
        const target = enabled.find(item => item.type === "message" && Object.keys(item.Format?.files || {}).length > 0);
        if (target) { preparation.target = target; preparation.snapshotBefore = current; return; }
        // Complete enabled branches before attempting their parallel join.
        const next = enabled.find(item => item.type === "message") || enabled.find(item => item.type === "event") || enabled.find(item => item.type === "gateway");
        if (!next) throw new Error(`Instance ${instanceId}: no file Message reachable without BusinessRule/Oracle execution`);
        const method = next.type === "message" ? `${next.MessageID}_Send` : next.EventID || next.GatewayID;
        const input = next.type === "message" ? context.payloadForMessage(next, instanceId) : { instanceId };
        if (next.type === "message") input.fireflyTranId = `preparation-${instanceId}-${next.MessageID}`;
        note(`实例 ${instanceId} 前置准备：${method}（不计入测量）`);
        const op = await operation(core, await invoke(method, input));
        preparation.actions.push({ method, input, operation: op, preparationOnly: true });
      }
      throw new Error(`Instance ${instanceId}: exceeded preparation step limit`);
    }));
    for (let index = 0; index < context.rounds; index++) {
      const preparation = report.preparations[index];
      const instanceId = preparation.instanceId;
      const snapshot = () => request(`${api}/query/getExecutionSnapshot`, { input: { instanceId } });
      const element = preparation.target;
      const sample: any = { index: index + 1, instanceId, status: "running", snapshotBefore: preparation.snapshotBefore };
      report.samples.push(sample);
      const method = `${element.MessageID}_Send`;
      const payload = context.payloadForMessage(element, instanceId);
      note(`第 ${index + 1}/${context.rounds} 轮：文件上传，IPFS后台发布与合约调用并行`);
      sample.clockSyncBefore = await clockSync();
      performance.clearResourceTimings();
      sample.measuredStartedAt = Date.now();
      const roundFile = context.file || new File([
        `Geth Message IPFS experiment\nround=${index + 1}\nnonce=${crypto.randomUUID()}\n`.padEnd(1024, "x"),
      ], file.name, { type: "text/plain" });
      sample.file = { name: roundFile.name, bytes: roundFile.size };
      const form = new FormData();
      form.append("autometa", "true"); form.append("file", roundFile);
      const upload = await timed(`${core}/data`, form);
      sample.fileUpload = upload;
      if (upload.value.blob?.public) throw new Error("File already published to IPFS; use new file content to measure an actual upload");
      let publicationDone = false;
      // Launch the real FireFly→IPFS operation without waiting for its CID.
      // Settled outcomes prevent an unhandled rejection while the other branch runs.
      const publicationPromise = timed(`${core}/data/${upload.value.id}/blob/publish`, {}).then(
        value => { publicationDone = true; sample.ipfsPublishRequest = value; return { value, error: null }; },
        error => { publicationDone = true; return { value: null, error }; },
      );
      sample.fileBindings = Object.keys(element.Format.files).filter(name => name in payload);
      if (!sample.fileBindings.length) throw new Error("Message file fields do not match contract parameters");
      // Use the already-existing file resource handle. Its CID becomes available
      // on this same data resource after publication; do not gate Message ID/SC on it.
      for (const name of sample.fileBindings) payload[name] = upload.value.id;
      sample.fileReferenceType = "FireFly dataId; resolves to CID after background publication";
      const businessData = Object.fromEntries(Object.entries(payload).filter(([key]) => !/^(instanceid|fireflytranid)$/i.test(key)));
      const data = await timed(`${core}/messages/private`, {
        data: [{ value: businessData }, { id: upload.value.id }],
        group: { members: [{ identity: recipient.did }] },
        header: { tag: "message-timing-experiment", topics: [`timing_${element.MessageID}`] },
      });
      sample.messageRequest = data;
      sample.messageId = data.value.header.id;
      payload.fireflyTranId = sample.messageId;
      sample.method = method; sample.payload = payload;
      sample.ipfsPendingWhenContractInvoked = !publicationDone;
      const invocation = await timed(`${api}/invoke/${method}`, { input: payload, key: context.signer });
      sample.invokeRequest = invocation;
      sample.invokeResponse = invocation.value;
      // Both branches have already started. Waiting here does not serialize their execution.
      const [op, publicationOutcome] = await Promise.all([operation(core, invocation.value), publicationPromise]);
      sample.operationObservedRaw = performance.timeOrigin + performance.now();
      if (publicationOutcome.error) throw publicationOutcome.error;
      const published = publicationOutcome.value;
      const cid = published?.value.blob?.public;
      if (!published || !cid) throw new Error("FireFly IPFS publication did not return a CID");
      sample.ipfsCid = cid;
      sample.ipfsOperations = await until("correlated real IPFS upload", () => request(`${core}/operations?type=sharedstorage_upload_blob&limit=1000`),
        rows => rows.some((item: any) => item.input?.dataId === upload.value.id));
      const ipfsInitial = sample.ipfsOperations.find((item: any) => item.input?.dataId === upload.value.id);
      sample.ipfsUploadOperation = await until("IPFS upload completion", () => request(`${core}/operations/${ipfsInitial.id}`), item => {
        if (item.status === "Failed") throw new Error("IPFS upload failed");
        return item.status === "Succeeded";
      });
      if (sample.ipfsUploadOperation.plugin !== "ipfs" || sample.ipfsUploadOperation.output?.payloadRef !== cid) throw new Error("IPFS operation/CID correlation failed");
      const ipfsStage = { step: "IPFS", start_time: published.start, end_time: published.end, available: true };
      sample.senderPublishedData = await request(`${core}/data/${upload.value.id}`);
      if (sample.senderPublishedData.blob?.public !== cid) throw new Error("Published CID is not linked to the Message file dataId");
      sample.fileCidMapping = { dataId: upload.value.id, cid };
      sample.operation = op;
      const events = await until("invoke success event", () => request(`${core}/events?tx=${op.tx}&limit=1000`),
        rows => rows.some((event: any) => event.type === "blockchain_invoke_op_succeeded" && event.reference === op.id));
      const event = events.find((item: any) => item.type === "blockchain_invoke_op_succeeded" && item.reference === op.id);
      sample.events = events;
      const message = await until("message batch", () => request(`${core}/messages/${sample.messageId}`), item => Boolean(item.batch));
      const batch = await request(`${core}/batches/${message.batch}`);
      sample.message = message; sample.batch = batch;
      sample.transportOperations = await request(`${core}/operations?tx=${batch.tx.id}&limit=1000`);
      const chainEvents = await until("correlated MessageSent", () => request(`${core}/blockchainevents?listener=${listener.id}&limit=1000`),
        rows => rows.some((item: any) => item.name === "MessageSent" &&
          item.output?.fireflyTranId === sample.messageId && Number(item.output?.instanceId) === instanceId));
      sample.chainEvent = chainEvents.find((item: any) => item.output?.fireflyTranId === sample.messageId && Number(item.output?.instanceId) === instanceId);
      sample.snapshotAfter = await snapshot();
      const completed = context.elementsFromSnapshot(sample.snapshotAfter).find(item => item.MessageID === element.MessageID);
      if (Number(completed?.state) !== 3 || completed?.FireflyTranID !== sample.messageId) throw new Error("Message completion/new Message ID verification failed");
      sample.executionVerified = true;
      sample.messageFinal = await until("private message confirmation", () => request(`${core}/messages/${sample.messageId}`),
        item => item.state === "confirmed" && Boolean(item.confirmed));
      sample.receiverMessage = await until("receiver private message confirmation", () => request(`${receiverCore}/messages/${sample.messageId}`),
        item => item.state === "confirmed" && Boolean(item.confirmed));
      sample.transportOperations = await until("all private delivery and batch pin operations", () => request(`${core}/operations?tx=${batch.tx.id}&limit=1000`),
        rows => {
          if (rows.some((item: any) => item.status === "Failed")) throw new Error("Private transport/pin operation failed");
          return rows.some((item: any) => item.type === "blockchain_pin_batch") && rows.every((item: any) => item.status === "Succeeded");
        });
      const received = await fetch(`${receiverCore}/data/${upload.value.id}/blob`, { signal: AbortSignal.timeout(deadlineMs) });
      if (!received.ok) throw new Error("Receiver file unavailable");
      const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", await received.arrayBuffer()))).map(b => b.toString(16).padStart(2, "0")).join("");
      if (hash !== upload.value.blob.hash) throw new Error("Receiver file hash mismatch");
      sample.receiverFileSha256 = hash;
      sample.receiverOperations = await request(`${receiverCore}/operations?tx=${batch.tx.id}&limit=1000`);
      sample.receiverData = await request(`${receiverCore}/data/${upload.value.id}`);
      // Verify the stable file dataId in the Message and its separately audited
      // source dataId→CID mapping. Private receivers may omit blob.public.
      sample.receiverMessageData = await request(`${receiverCore}/messages/${sample.messageId}/data`);
      if (!sample.fileBindings.every((name: string) => sample.receiverMessageData.some((item: any) => item.value?.[name] === upload.value.id))) {
        throw new Error("Receiver Message file field does not contain the uploaded file dataId");
      }
      const completedAt = Math.max(published.end, stamp(sample.messageFinal.confirmed), stamp(sample.receiverMessage.confirmed),
        ...sample.transportOperations.map((item: any) => stamp(item.updated)));
      sample.pinOperation = sample.transportOperations.find((item: any) => item.type === "blockchain_pin_batch");
      sample.pinOperation_ms = stamp(sample.pinOperation.updated) - stamp(sample.pinOperation.created);
      sample.stages = [
        { step: "Private Data Bus", start_time: upload.start, end_time: completedAt },
        ipfsStage,
        { step: "API Invoker", start_time: invocation.start, end_time: stamp(op.created) },
        { step: "BPMN SC", start_time: stamp(op.created), end_time: stamp(event.created) },
      ].map((stage: { step: string; start_time: number; end_time: number; available?: boolean }) => ({ ...stage, duration_ms: stage.start_time == null || stage.end_time == null ? null : stage.end_time - stage.start_time,
        valid: stage.available !== false && stage.start_time != null && stage.end_time != null && Number.isFinite(stage.end_time - stage.start_time) && stage.end_time >= stage.start_time }));
      sample.warnings = sample.stages.filter((stage: any) => !stage.valid && stage.available !== false)
        .map((stage: any) => `${stage.step}: timestamp inversion/invalid interval; raw value retained, exclude from latency statistics`);
      sample.messageToInvokeSuccess_ms = stamp(event.created) - data.start;
      sample.privateMessageHttp_ms = data.end - data.start;
      sample.messageIdToInvokeStart_ms = invocation.start - data.end;
      sample.httpPublishInvokeOverlap_ms = Math.max(0, Math.min(published.end, invocation.end) - Math.max(published.start, invocation.start));
      sample.legacyMessageToBatch_ms = stamp(batch.created) - stamp(data.value.header.created);
      sample.status = sample.warnings.length ? "passed_with_warnings" : "passed";
      sample.observedFinishedAt = Date.now();
      sample.observedFinishedRaw = performance.timeOrigin + performance.now();
      sample.clockSyncAfter = await clockSync();
      note(`第 ${index + 1}/${context.rounds} 轮完成`);
    }
    if (context.protectedInstanceId != null) {
      report.originalInstanceAfter = await request(`${api}/query/getExecutionSnapshot`, { input: { instanceId: context.protectedInstanceId } });
      if (JSON.stringify(report.originalInstanceAfter) !== JSON.stringify(report.originalInstanceBefore)) throw new Error("Original page instance changed during experiment");
    }
    report.status = report.samples.some((sample: any) => sample.warnings?.length) ? "completed_with_warnings" : "passed";
  } catch (error: any) {
    report.status = "failed"; report.error = String(error?.message || error);
    const sample = report.samples.at(-1);
    if (sample?.status === "running") { sample.status = "failed"; sample.error = report.error; }
  }
  report.finishedAt = new Date().toISOString();
  report.summary = ["Private Data Bus", "IPFS", "API Invoker", "BPMN SC"].map(step => {
    const values = report.samples.flatMap((sample: any) => (sample.stages || [])
      .filter((stage: any) => stage.step === step && stage.valid).map((stage: any) => stage.duration_ms));
    return { step, count: values.length, mean_ms: values.length ? values.reduce((a: number, b: number) => a + b, 0) / values.length : null,
      min_ms: values.length ? Math.min(...values) : null, max_ms: values.length ? Math.max(...values) : null };
  });
  if (report.status === "passed" || report.status === "completed_with_warnings") {
    try {
      note("核对 FireFly→IPFS 内部调用及 Geth 交易提交/回执记录");
      return await request("http://127.0.0.1:8791/audit", { report, apiScope: "contract" });
    } catch (error: any) {
      report.status = "audit_required";
      report.error = `实验交易已完成，内部计时核验未完成；请检查 metric-audit/audit_server.py 返回的错误。${String(error?.message || error)}`;
    }
  }
  return report;
}
