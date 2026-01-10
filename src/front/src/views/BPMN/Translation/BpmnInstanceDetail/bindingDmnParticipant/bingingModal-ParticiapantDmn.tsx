import React, { useEffect, useRef, useState } from "react";
import { Modal, Button, Alert, message } from "antd";
import { BindingDmnModal } from "./bindingDmnModal";
import { BindingParticipant } from "./bindingParticipantsModal";
import { useBpmnSvg } from "./hooks";
import { getMembership, retrieveFabricIdentity } from "@/api/platformAPI";
import { getFireflyList, getResourceSets } from "@/api/resourceAPI";
import { useAppSelector } from "@/redux/hooks";
import { useFireflyData, useParticipantsData } from "../hooks";
import { getFireflyVerify, invokeCreateInstance } from "@/api/executionAPI";
import { bindTokensToERCs, ERCAddMintAuthority, getMaxInstanceChaincodeId, retrieveBPMN } from "@/api/externalResource";
import { BindingTaskERC } from "./bindingERCModal";
import { validateInstance, formatValidationErrors } from "./validator/InstanceValidator";

const ParticipantDmnBindingModal = ({ open, setOpen, bpmnId }) => {
	const [showBindingParticipantMap, setShowBindingParticipantMap] = useState(
		new Map(),
	);
	const [showBindingParticipantValueMap, setShowBindingParticipantValueMap] =
		useState(new Map());

	const [DmnBindingInfo, setDmnBindingInfo] = useState({});
	const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
	const [errorMessage, setErrorMessage] = useState("");
	const [participants, syncParticipants] = useParticipantsData(bpmnId);
	const consortiumId = useAppSelector(state => state.consortium.currentConsortiumId);
	const [showTaskERCMap, setShowTaskERCMap] = useState<Record<string, any>>({});
	const [isValidating, setIsValidating] = useState(false);
	const [validationErrors, setValidationErrors] = useState<any[]>([]);
	const [showValidationResult, setShowValidationResult] = useState(false);
	useEffect(() => {
		console.log("父组件收到的 showTaskERCMap:", showTaskERCMap);
	}, [showTaskERCMap]);

	const showTaskERCRef = useRef(showTaskERCMap);
	useEffect(() => {
		showTaskERCRef.current = showTaskERCMap;
	}, [showTaskERCMap]);
	const CreateInstance = async (onlyReturnParam = false) => {
		const createInstanceParam = await constructParam();

		// 创建一个空对象
		const singleObject = {};

		// 遍历数组中的每个元素，并将其合并到singleObject中
		for (const item of createInstanceParam) {
			Object.assign(singleObject, item);
		}
		//处理ERCbind参数
		if (Object.keys(showTaskERCMap).length > 0) {
			const tokenElementsMap: Record<string, string> = {};
			Object.entries(showTaskERCMap).forEach(([taskId, value]) => {
				// 动态生成 ERCName 的 key
				const ercNameKey = Object.keys(value).find(k => k.endsWith("_ERCName"));
				tokenElementsMap[taskId] = ercNameKey ? value[ercNameKey] : "";
			});

			// 将生成的 map 加入创建参数
			singleObject["ERCChaincodeNames"] = tokenElementsMap;
			singleObject["BpmnId"] =bpmnId;
		}


		const bpmn = await retrieveBPMN(bpmnId);
		const chaincode_url = bpmn.firefly_url;

		if (onlyReturnParam) {
			return { param: singleObject, url: chaincode_url.slice(0, -4), contract_name: bpmn.name.split(".")[0], };
		}

		await invokeCreateInstance(chaincode_url, singleObject);
		const ercIdTokenMap = await extractErcIdTokenMap(showTaskERCMap);
		const msps = extractMsps(singleObject);//暂时没用
		await bindTokensToERCs(ercIdTokenMap, chaincode_url,consortiumId);
		const instanceid = await getMaxInstanceChaincodeId(bpmnId)
		//console.log("得到的instanceid为",instanceid) 
		await ERCAddMintAuthority(ercIdTokenMap,chaincode_url,consortiumId,instanceid.toString(),msps)


		async function constructParam() {
			const createPromise = async (value, key) => {
				const selectedValidationType = value.selectedValidationType;
				if (selectedValidationType === "group") {
					let msp = "";
					if (value.selectedMembershipId) {
						let memberships = await getResourceSets(
							currentEnvId,
							null,
							value.selectedMembershipId,
						);
						msp = memberships[0].msp;
					}
					let attr = value.Attr;
					if (attr) {
						attr = attr
							.map(({ attr, value }) => ({ [attr]: value }))
							.reduce((acc, obj) => {
								return { ...acc, ...obj };
							}, {});
					} else {
						attr = {};
					}
					createInstanceParam.push({
						[key]: {
							msp: msp,
							attributes: attr,
							isMulti: true,
							multiMaximum: 0,
							multiMinimum: 0,
							x509: "",
						},
					});
				} else if (selectedValidationType === "equal") {
					let msp = "";
					if (!value.selectedMembershipId) {
						setErrorMessage(
							`Participant ${participants.find(key)} membership is null`,
						);
					}
					let memberships = await getResourceSets(
						currentEnvId,
						null,
						value.selectedMembershipId,
					);
					msp = memberships[0].msp;
					if (!value.selectedUser) {
						setErrorMessage(
							`Participant ${participants.find(key)} user is null`,
						);
					}
					const fabricIdentity = await retrieveFabricIdentity(
						value.selectedUser,
					);
					const fireflyData = await getFireflyList(
						currentEnvId,
						null,
						fabricIdentity.membership,
					);
					const fireflyCoreUrl = fireflyData[0].coreURL;
					const verify = await getFireflyVerify(
						fireflyCoreUrl,
						fabricIdentity.firefly_identity_id,
					);
					const x509 = verify[0].value.split("::").slice(1).join("::");
					createInstanceParam.push({
						[key]: {
							msp: msp,
							attributes: {},
							isMulti: false,
							multiMaximum: 0,
							multiMinimum: 0,
							x509: `${btoa(x509)}@${msp}`,
						},
					});
				}
			};

			const createInstanceParam = [];

			const promises = [];
			showBindingParticipantValueMap.forEach((value, key) => {
				promises.push(createPromise(value, key));
			});
			await Promise.all(promises);

			for (const [key, value] of Object.entries(DmnBindingInfo)) {
				const newObj = {};
				newObj[`${key}_DecisionID`] = value[`${key}_DecisionID`];
				createInstanceParam.push(newObj);

				newObj[`${key}_ParamMapping`] = value[`${key}_ParamMapping`];
				createInstanceParam.push({ ...newObj });

				newObj[`${key}_Content`] = value[`${key}_Content`];
				createInstanceParam.push({ ...newObj });
			}
			
			return createInstanceParam;
		}


		function extractErcIdTokenMap(taskERCMap: Record<string, any>) {
			const ercIdTokenMap: Record<string, string> = {};

			Object.values(taskERCMap).forEach((value: any) => {
				const ercIdKey = Object.keys(value).find(k => k.endsWith("_ERCID"));
				if (ercIdKey) {
					const ercId = value[ercIdKey];
					const tokenName = value.tokenName || "";
					if (ercId) {
						ercIdTokenMap[ercId] = tokenName;
					}
				}
			});

			return ercIdTokenMap;
		}

		//token权限控制获得MSPs
		function extractMsps(param: Record<string, any>): string[] {
			const msps = Object.entries(param)
				.filter(([key]) => key.startsWith("Participant_"))
				.map(([, value]) => value.msp)
				.filter(Boolean);

			return Array.from(new Set(msps));
		}

	};

	// Validation handler
	const handleValidation = async () => {
		console.log('[Validation] Button clicked, starting validation...');
		setIsValidating(true);
		setValidationErrors([]);
		setShowValidationResult(false);

		try {
			console.log('[Validation] Retrieving BPMN with ID:', bpmnId);
			// Get BPMN XML content
			const bpmn = await retrieveBPMN(bpmnId);
			console.log('[Validation] BPMN retrieved:', bpmn);
			console.log('[Validation] BPMN keys:', Object.keys(bpmn || {}));

			// Try different possible field names for the BPMN content
			const bpmnXml = bpmn.content || bpmn.bpmnContent || bpmn.xml || bpmn.xmlContent || bpmn.bpmn_content;
			console.log('[Validation] BPMN XML extracted:', bpmnXml ? `${bpmnXml.substring(0, 100)}...` : 'NULL');

			if (!bpmnXml) {
				throw new Error('BPMN content is empty. Available fields: ' + Object.keys(bpmn || {}).join(', '));
			}

			// Extract firefly URL for blockchain queries
			const fireflyUrl = bpmn.firefly_url;
			console.log('[Validation] Firefly URL:', fireflyUrl);

			console.log('[Validation] Participant bindings:', showBindingParticipantValueMap);
			console.log('[Validation] Task ERC map:', showTaskERCMap);

			// Run validation
			console.log('[Validation] Running validateInstance...');
			const result = await validateInstance(
				bpmnXml,
				showBindingParticipantValueMap,
				showTaskERCMap,
				fireflyUrl
			);

			console.log('[Validation] Validation result:', result);
			setValidationErrors(result.errors);
			setShowValidationResult(true);

			// Show validation result message
			if (result.isValid) {
				message.success('验证通过！所有代币操作和参与者绑定都是有效的。');
			} else {
				const errorCount = result.errors.filter(e => e.severity === 'error').length;
				const warningCount = result.errors.filter(e => e.severity === 'warning').length;
				message.warning(`验证完成：发现 ${errorCount} 个错误和 ${warningCount} 个警告。请查看下方详情。`);
			}
		} catch (error) {
			console.error('[Validation] Error occurred:', error);
			console.error('[Validation] Error stack:', error.stack);
			message.error(`验证失败: ${error.message || '未知错误'}`);
			setShowValidationResult(false);
		} finally {
			console.log('[Validation] Validation finished, resetting loading state');
			setIsValidating(false);
		}
	};

	const handleOK = async () => {
		await CreateInstance();
		setOpen(false);
	};

	const handleCancel = () => {
		setOpen(false);
	};

	return (
		<Modal
			title="Binding Dmns and Participants"
			open={open}
			onOk={handleOK}
			onCancel={handleCancel}
			style={{ minWidth: "1600px", textAlign: "center" }}
		>
			<div>
				<div style={{ display: "flex", marginBottom: "20px", height: "600px" }}>
					<div style={{ flex: "0 1 35%", paddingRight: "10px", display: "flex", flexDirection: "column" }}>

						<div style={{ flex: "0 1 auto", marginBottom: "10px" }}>
							<h2>Binding BPMN businessRuleTasks and DMN</h2>
							<BindingDmnModal
								bpmnId={bpmnId}
								DmnBindingInfo={DmnBindingInfo}
								setDmnBindingInfo={setDmnBindingInfo}
							/>
						</div>

						<div style={{ flex: "0 1 200px", overflowY: "auto" }}>
							<h2>Binding Tasks to ERC</h2>
							<div style={{ padding: "0 5px" }}>
								<BindingTaskERC
									bpmnId={bpmnId}
									taskERCMap={showTaskERCMap}
									setTaskERCMap={setShowTaskERCMap}
								/>
							</div>
						</div>
					</div>


					<div style={{ flex: "0 1 65%", paddingLeft: "10px", height: "600px", overflow: "auto" }}>
						<h2>Binding Participants</h2>
						<BindingParticipant
							participants={participants}
							showBindingParticipantMap={showBindingParticipantMap}
							setShowBindingParticipantMap={setShowBindingParticipantMap}
							showBindingParticipantValueMap={showBindingParticipantValueMap}
							setShowBindingParticipantValueMap={setShowBindingParticipantValueMap}
						/>
					</div>
				</div>

				<div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
					<Button
						type="default"
						onClick={handleValidation}
						loading={isValidating}
						icon={<span style={{ marginRight: '4px' }}>🔍</span>}
					>
						Validate Instance
					</Button>

					<Button
						type="primary"
						onClick={async () => {
							const { param, url, contract_name } = await CreateInstance(true);
							navigator.clipboard.writeText(
								`param=${JSON.stringify(param, null, 2).replaceAll("false", "False")}\n    url="${url}"\n    contract_name="${contract_name}"`,
							);
							alert("The parameter has been copied to the clipboard");
						}}
					>
						Get CreateInstance Param
					</Button>
				</div>

				{/* Validation Errors Display */}
				{showValidationResult && validationErrors.length > 0 && (
					<div style={{ marginBottom: '20px', maxHeight: '300px', overflowY: 'auto' }}>
						<Alert
							message={`验证结果: ${validationErrors.filter(e => e.severity === 'error').length} 个错误, ${validationErrors.filter(e => e.severity === 'warning').length} 个警告`}
							description={
								<div>
									{validationErrors.map((error, index) => (
										<div
											key={index}
											style={{
												padding: '8px',
												marginBottom: '8px',
												borderLeft: `4px solid ${error.severity === 'error' ? '#ff4d4f' : '#faad14'}`,
												backgroundColor: error.severity === 'error' ? '#fff2f0' : '#fffbe6'
											}}
										>
											<div style={{ fontWeight: 'bold' }}>
												{error.severity === 'error' ? '❌' : '⚠️'} {error.taskName}
											</div>
											<div style={{ marginTop: '4px', fontSize: '13px' }}>
												{error.message}
											</div>
										</div>
									))}
								</div>
							}
							type={validationErrors.some(e => e.severity === 'error') ? 'error' : 'warning'}
							closable
							onClose={() => {
								setValidationErrors([]);
								setShowValidationResult(false);
							}}
						/>
					</div>
				)}

				{/* Validation Success Display */}
				{showValidationResult && validationErrors.length === 0 && (
					<div style={{ marginBottom: '20px' }}>
						<Alert
							message="✅ 验证通过！"
							description={
								<div>
									<div style={{ marginBottom: '8px' }}>
										所有代币操作和参与者绑定都是有效的。
									</div>
									<div style={{ fontSize: '12px', color: '#52c41a' }}>
										<div>✓ 所有参与者已正确绑定</div>
										<div>✓ 代币所有权合法</div>
										<div>✓ 操作权限验证通过</div>
									</div>
								</div>
							}
							type="success"
							showIcon
							closable
							onClose={() => setShowValidationResult(false)}
						/>
					</div>
				)}

				<div style={{ textAlign: "center", height: "400px", marginTop: "-250px", marginBottom: "400px" }}>
					<SVGDisplayComponent bpmnId={bpmnId} />
				</div>
				{errorMessage && (
					<Alert
						message={errorMessage}
						description="Error Description Error Description Error Description Error Description Error Description Error Description"
						type="error"
						closable
						onClose={() => setErrorMessage("")}
					/>
				)}
			</div>
		</Modal>
	);
};

// TODO 调整SVG大小到固定尺寸
const SVGDisplayComponent = ({ bpmnId }) => {
	const [svgContent, { }, refreshSvg] = useBpmnSvg(bpmnId);

	return (
		<div
			style={{
				width: "100 %" /* 或者具体的px值 */,
				height: "auto" /* 保持SVG的宽高比 */,
			}}
			dangerouslySetInnerHTML={{ __html: svgContent }}
		/>
	);
};

export default ParticipantDmnBindingModal;
