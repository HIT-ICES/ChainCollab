import { useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  IconButton,
  LinearProgress,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { FileUpload, AutoAwesome, ContentCopy, Refresh, Insights, CloudDownload } from '@mui/icons-material';
import { TabContext, TabPanel } from '@mui/lab';
import { translatorService } from '../services/translator';
import type {
  ChaincodeOutput,
  DecisionDetail,
  ParticipantsResponse,
  MessagesResponse,
  BusinessRuleResponse,
} from '../services/translator';

const sampleBpmn = `<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Definitions_1">
  <choreography id="Choreo_1" name="Sample Order Flow">
    <participant id="Participant_Seller" name="Seller"/>
    <participant id="Participant_Buyer" name="Buyer"/>
    <choreographyTask id="Task_Order" name="Create Order">
      <participantRef>Participant_Buyer</participantRef>
      <participantRef>Participant_Seller</participantRef>
      <messageFlowRef>Message_Order</messageFlowRef>
    </choreographyTask>
    <message id="Message_Order" name="Order Message" documentation="Send purchase request"/>
  </choreography>
</definitions>`;

const sampleDmn = `<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" id="SampleDecision" name="Decisions">
  <decision id="Decision_Eligibility" name="Eligibility">
    <variable id="var" name="Eligibility" typeRef="string" />
    <decisionTable>
      <input id="Input_Age">
        <inputExpression typeRef="number">
          <text>applicant.age</text>
        </inputExpression>
      </input>
      <output id="Output_Result" typeRef="string" />
      <rule>
        <inputEntry>
          <text>&gt;=18</text>
        </inputEntry>
        <outputEntry>
          <text>"Approved"</text>
        </outputEntry>
      </rule>
    </decisionTable>
  </decision>
</definitions>`;

const emptyInsights = {
  participants: {},
  messages: {},
  rules: {},
};

type InsightData = {
  participants: ParticipantsResponse;
  messages: MessagesResponse;
  rules: BusinessRuleResponse;
};

export default function TranslatorWorkbench() {
  const [bpmnContent, setBpmnContent] = useState('');
  const [dmnContent, setDmnContent] = useState('');
  const [chaincodeOutput, setChaincodeOutput] = useState<ChaincodeOutput | null>(null);
  const [insights, setInsights] = useState<InsightData>(emptyInsights);
  const [decisions, setDecisions] = useState<DecisionDetail[]>([]);
  const [activeTab, setActiveTab] = useState<'chaincode' | 'ffi'>('chaincode');
  const [loading, setLoading] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ severity: 'success' | 'error'; message: string } | null>(null);

  const hasBpmn = bpmnContent.trim().length > 0;
  const hasDmn = dmnContent.trim().length > 0;

  const participantEntries = useMemo(() => Object.entries(insights.participants || {}), [insights.participants]);
  const messageEntries = useMemo(() => Object.entries(insights.messages || {}), [insights.messages]);
  const ruleEntries = useMemo(() => Object.entries(insights.rules || {}), [insights.rules]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>, setter: (value: string) => void) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    setter(text);
  };

  const handleGenerate = async () => {
    if (!hasBpmn) {
      setFeedback({ severity: 'error', message: '请先粘贴或上传 BPMN 内容。' });
      return;
    }
    try {
      setLoading('chaincode');
      const result = await translatorService.generateChaincode(bpmnContent);
      setChaincodeOutput(result);
      setFeedback({ severity: 'success', message: '链码与 FFI 生成完成。' });
    } catch (error) {
      setFeedback({ severity: 'error', message: '生成链码失败，请检查后端服务是否可用。' });
    } finally {
      setLoading(null);
    }
  };

  const handleInsights = async () => {
    if (!hasBpmn) {
      setFeedback({ severity: 'error', message: '请先提供 BPMN 内容。' });
      return;
    }
    try {
      setLoading('insights');
      const [participants, messages, rules] = await Promise.all([
        translatorService.getParticipants(bpmnContent),
        translatorService.getMessages(bpmnContent),
        translatorService.getBusinessRules(bpmnContent),
      ]);
      setInsights({
        participants,
        messages,
        rules,
      });
      setFeedback({ severity: 'success', message: '已刷新参与者、消息、业务规则视图。' });
    } catch (error) {
      setFeedback({ severity: 'error', message: '获取 BPMN 元数据失败。' });
    } finally {
      setLoading(null);
    }
  };

  const handleDecisions = async () => {
    if (!hasDmn) {
      setFeedback({ severity: 'error', message: '请粘贴 DMN 内容以分析决策。' });
      return;
    }
    try {
      setLoading('decisions');
      const data = await translatorService.getDecisions(dmnContent);
      setDecisions(data);
      setFeedback({ severity: 'success', message: '决策表解析成功。' });
    } catch (error) {
      setFeedback({ severity: 'error', message: '解析 DMN 失败。' });
    } finally {
      setLoading(null);
    }
  };

  const copyToClipboard = async (text: string) => {
    if (!text) return;
    await navigator.clipboard?.writeText(text);
    setFeedback({ severity: 'success', message: '内容已复制到剪贴板。' });
  };

  return (
    <Stack spacing={3}>
      <Card>
        <CardHeader
          title="Choreography Translator"
          subheader="使用 Material + AWS Console 风格打造的翻译工作台，支持 BPMN → Chaincode、FFI 生成，以及参与者与业务规则洞察。"
          action={
            <Stack direction="row" spacing={1}>
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={() => {
                  setBpmnContent(sampleBpmn);
                  setFeedback({ severity: 'success', message: '已填充示例 BPMN。' });
                }}
              >
                示例 BPMN
              </Button>
              <Button
                variant="outlined"
                color="secondary"
                startIcon={<Refresh />}
                onClick={() => {
                  setDmnContent(sampleDmn);
                  setFeedback({ severity: 'success', message: '已填充示例 DMN。' });
                }}
              >
                示例 DMN
              </Button>
            </Stack>
          }
        />
        {loading === 'chaincode' && <LinearProgress />}
        <CardContent>
          <Box
            sx={{
              display: 'grid',
              gap: 3,
              gridTemplateColumns: { xs: '1fr', md: '7fr 5fr' },
              alignItems: 'stretch',
            }}
          >
            <Box>
              <Stack spacing={2}>
                <Typography variant="subtitle2" color="text.secondary">
                  BPMN 内容
                </Typography>
                <TextField
                  multiline
                  minRows={12}
                  value={bpmnContent}
                  onChange={(event) => setBpmnContent(event.target.value)}
                  placeholder="粘贴 BPMN XML 内容或点击下方上传 .bpmn 文件"
                  fullWidth
                />
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center">
                  <Button component="label" variant="outlined" startIcon={<FileUpload />} fullWidth>
                    上传 BPMN
                    <input
                      hidden
                      type="file"
                      accept=".bpmn,.xml"
                      onChange={(event) => handleFileUpload(event, setBpmnContent)}
                    />
                  </Button>
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AutoAwesome />}
                    onClick={handleGenerate}
                    fullWidth
                    disabled={loading === 'chaincode'}
                  >
                    生成 Chaincode & FFI
                  </Button>
                  <Button
                    variant="outlined"
                    color="primary"
                    startIcon={<Insights />}
                    onClick={handleInsights}
                    fullWidth
                    disabled={loading === 'insights'}
                  >
                    BPMN 洞察
                  </Button>
                </Stack>
              </Stack>
            </Box>
            <Box>
              <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardHeader
                  title="输出预览"
                  subheader="在 Tabs 中切换 Chaincode 与 FFI，支持复制到剪贴板。"
                  action={
                    <Tooltip title="复制当前视图">
                      <span>
                        <IconButton
                          onClick={() => copyToClipboard(
                            activeTab === 'chaincode'
                              ? chaincodeOutput?.bpmnContent || ''
                              : chaincodeOutput?.ffiContent || ''
                          )}
                          disabled={!chaincodeOutput}
                        >
                          <ContentCopy />
                        </IconButton>
                      </span>
                    </Tooltip>
                  }
                />
                <Divider />
                {chaincodeOutput ? (
                  <TabContext value={activeTab}>
                    <Tabs
                      value={activeTab}
                      onChange={(_, value) => setActiveTab(value)}
                      variant="fullWidth"
                    >
                      <Tab label="Chaincode" value="chaincode" />
                      <Tab label="FFI" value="ffi" />
                    </Tabs>
                    <TabPanel value="chaincode" sx={{ flex: 1, overflow: 'auto' }}>
                      <Box
                        component="pre"
                        sx={{
                          backgroundColor: '#0f172a',
                          color: '#e2e8f0',
                          borderRadius: 2,
                          p: 2,
                          fontSize: 13,
                          maxHeight: 360,
                          overflow: 'auto',
                        }}
                      >
                        {chaincodeOutput?.bpmnContent || '暂无输出'}
                      </Box>
                    </TabPanel>
                    <TabPanel value="ffi" sx={{ flex: 1, overflow: 'auto' }}>
                      <Box
                        component="pre"
                        sx={{
                          backgroundColor: '#0f172a',
                          color: '#e2e8f0',
                          borderRadius: 2,
                          p: 2,
                          fontSize: 13,
                          maxHeight: 360,
                          overflow: 'auto',
                        }}
                      >
                        {chaincodeOutput?.ffiContent || '暂无输出'}
                      </Box>
                    </TabPanel>
                  </TabContext>
                ) : (
                  <Stack spacing={2} alignItems="center" justifyContent="center" sx={{ flex: 1, p: 4 }}>
                    <CloudDownload color="primary" sx={{ fontSize: 48 }} />
                    <Typography variant="body2" color="text.secondary" align="center">
                      生成 Chaincode / FFI 后可在此查看内容
                    </Typography>
                  </Stack>
                )}
              </Card>
            </Box>
          </Box>
        </CardContent>
      </Card>

      <Box
        sx={{
          display: 'grid',
          gap: 3,
          gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
          alignItems: 'stretch',
        }}
      >
        <Box>
          <Card>
            {loading === 'insights' && <LinearProgress />}
            <CardHeader title="BPMN 洞察" subheader="参与者、消息与业务规则一览" />
            <CardContent>
              <Stack spacing={3}>
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    参与者 ({participantEntries.length})
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    {participantEntries.length ? (
                      participantEntries.map(([id, name]) => (
                        <Chip key={id} label={`${name || 'Unnamed'} (${id})`} color="primary" variant="outlined" />
                      ))
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        暂无数据
                      </Typography>
                    )}
                  </Stack>
                </Box>
                <Divider />
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    消息 ({messageEntries.length})
                  </Typography>
                  <Stack spacing={1}>
                    {messageEntries.length ? (
                      messageEntries.map(([id, meta]) => (
                        <Card key={id} variant="outlined">
                          <CardContent>
                            <Typography variant="subtitle2">{meta.name || 'Unnamed Message'}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              ID: {id}
                            </Typography>
                            {meta.documentation && (
                              <Typography variant="body2" sx={{ mt: 1 }}>
                                {meta.documentation}
                              </Typography>
                            )}
                          </CardContent>
                        </Card>
                      ))
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        暂无数据
                      </Typography>
                    )}
                  </Stack>
                </Box>
                <Divider />
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    业务规则 ({ruleEntries.length})
                  </Typography>
                  <Stack spacing={1}>
                    {ruleEntries.length ? (
                      ruleEntries.map(([id, rule]) => (
                        <Card key={id} variant="outlined">
                          <CardContent>
                            <Typography variant="subtitle2">{rule.name || 'Business Rule'}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              ID: {id}
                            </Typography>
                            {rule.documentation && (
                              <Typography variant="body2" sx={{ mt: 1 }}>
                                {rule.documentation}
                              </Typography>
                            )}
                          </CardContent>
                        </Card>
                      ))
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        暂无数据
                      </Typography>
                    )}
                  </Stack>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Box>

        <Box>
          <Card>
            {loading === 'decisions' && <LinearProgress />}
            <CardHeader
              title="DMN 决策洞察"
              subheader="上传 DMN 以查看每个决策点的输入、输出与主流程标记"
            />
            <CardContent>
              <Stack spacing={2}>
                <TextField
                  multiline
                  minRows={8}
                  value={dmnContent}
                  onChange={(event) => setDmnContent(event.target.value)}
                  placeholder="粘贴 DMN XML 内容或点击上传"
                  fullWidth
                />
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                  <Button component="label" variant="outlined" startIcon={<FileUpload />} fullWidth>
                    上传 DMN
                    <input
                      hidden
                      type="file"
                      accept=".dmn,.xml"
                      onChange={(event) => handleFileUpload(event, setDmnContent)}
                    />
                  </Button>
                  <Button
                    variant="contained"
                    color="secondary"
                    startIcon={<AutoAwesome />}
                    onClick={handleDecisions}
                    fullWidth
                    disabled={loading === 'decisions'}
                  >
                    解析决策
                  </Button>
                </Stack>
                {decisions.length ? (
                    <Table size="small" sx={{ minWidth: 300 }}>
                      <TableHead>
                      <TableRow>
                        <TableCell>决策</TableCell>
                        <TableCell>输入</TableCell>
                        <TableCell>输出</TableCell>
                        <TableCell>主流程</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {decisions.map((decision) => (
                        <TableRow key={decision.id}>
                          <TableCell>
                            <Typography variant="subtitle2">{decision.name || decision.id}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              ID: {decision.id}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Stack spacing={1}>
                              {decision.inputs.map((input) => (
                                <Typography key={input.id} variant="body2">
                                  {input.label || input.id} ({input.typeRef}) — {input.text}
                                </Typography>
                              ))}
                            </Stack>
                          </TableCell>
                          <TableCell>
                            <Stack spacing={1}>
                              {decision.outputs.map((output) => (
                                <Typography key={output.id} variant="body2">
                                  {output.name || output.id} ({output.type})
                                </Typography>
                              ))}
                            </Stack>
                          </TableCell>
                          <TableCell>
                            {decision.is_main ? <Chip label="主流程" color="secondary" size="small" /> : '—'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    尚未解析决策
                  </Typography>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Box>
      </Box>

      {feedback && (
        <Alert
          severity={feedback.severity}
          onClose={() => setFeedback(null)}
          sx={{ position: 'sticky', bottom: 16 }}
        >
          {feedback.message}
        </Alert>
      )}
    </Stack>
  );
}
