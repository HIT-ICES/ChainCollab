import React, { useEffect, useMemo, useState } from "react";
import { Modal, Button, Alert, Input, Switch } from "antd";
import { BindingDmnModal } from "./bindingDmnModal";
import { BindingParticipant } from "./bindingParticipantsModal";
import { useBpmnSvg } from "./hooks";
import { getMembership, retrieveFabricIdentity, retrieveEthereumIdentity } from "@/api/platformAPI";
import { getDmnContractDetailForEthEnv, getFireflyList, getIdentityContractDetail, getResourceSets } from "@/api/resourceAPI";
import { useAppSelector } from "@/redux/hooks";
import { useFireflyData, useParticipantsData } from "../hooks";
import { callFireflyContract, getFireflyVerify, invokeCreateInstance } from "@/api/executionAPI";
import { addBPMNInstance, retrieveBPMN, updateBPMNInstance } from "@/api/externalResource";
import { useBusinessRulesDataByBpmn } from "./hooks";

const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
const DEFAULT_DMN_EVAL_URL = "http://cdmn-node1:5000/api/dmn/evaluate";

const ParticipantDmnBindingModal = ({
	open,
	setOpen,
	bpmnId,
	bpmnInstanceId = "",
	syncExternalData,
}: {
	open: any;
	setOpen: any;
	bpmnId: any;
	bpmnInstanceId?: any;
	syncExternalData?: () => void;
}) => {
	const [showBindingParticipantMap, setShowBindingParticipantMap] = useState(
		new Map(),
	);
	const [showBindingParticipantValueMap, setShowBindingParticipantValueMap] =
		useState(new Map());

	const [DmnBindingInfo, setDmnBindingInfo] = useState({});
	const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
	const currentEnvType = useAppSelector((state) => state.env.currentEnvType);
	const currentConsortiumId = useAppSelector(
		(state) => state.consortium.currentConsortiumId,
	);
	const [effectiveEnvId, setEffectiveEnvId] = useState("");
	const [effectiveEnvType, setEffectiveEnvType] = useState("");
	const [errorMessage, setErrorMessage] = useState("");
	const [participants, syncParticipants] = useParticipantsData(bpmnId);
	const [businessRules] = useBusinessRulesDataByBpmn(bpmnId);
	const [identityContractAddress, setIdentityContractAddress] = useState("");
	const [dmnLiteAddress, setDmnLiteAddress] = useState("");
	const [dmnEvalUrl, setDmnEvalUrl] = useState(DEFAULT_DMN_EVAL_URL);
	const [enforceBusinessRuleCaller, setEnforceBusinessRuleCaller] =
		useState(false);

	const extractFireflyScalar = (payload: any): string | number | null => {
		if (payload === undefined || payload === null) {
			return null;
		}
		if (typeof payload === "string" || typeof payload === "number") {
			return payload;
		}
		if (Array.isArray(payload)) {
			for (const item of payload) {
				const resolved = extractFireflyScalar(item);
				if (resolved !== null) {
					return resolved;
				}
			}
			return null;
		}
		const candidates = [
			payload.ret0,
			payload.instanceId,
			payload.output?.ret0,
			payload.output?.instanceId,
			payload.input?.ret0,
			payload.input?.instanceId,
		];
		for (const candidate of candidates) {
			const resolved = extractFireflyScalar(candidate);
			if (resolved !== null) {
				return resolved;
			}
		}
		return null;
	};

	const persistEthereumInstance = async (
		bpmn: any,
		chaincodeUrl: string,
		createResult: any,
	) => {
		const queryResult = await callFireflyContract(
			chaincodeUrl,
			"currentInstanceId",
			{},
			"query",
		);
		const resolvedId =
			extractFireflyScalar(queryResult) ?? extractFireflyScalar(createResult);
		if (resolvedId === null || resolvedId === undefined || resolvedId === "") {
			throw new Error("Unable to resolve created instance id from FireFly");
		}
		const rawInstanceCounter = Number(resolvedId);
		if (!Number.isFinite(rawInstanceCounter)) {
			throw new Error(`Invalid instance id returned from FireFly: ${resolvedId}`);
		}
		// currentInstanceId() is the next available id after createInstance completes.
		const numericInstanceId = rawInstanceCounter > 0 ? rawInstanceCounter - 1 : 0;
		if (!Number.isFinite(numericInstanceId)) {
			throw new Error(`Invalid instance id returned from FireFly: ${resolvedId}`);
		}
		try {
			await callFireflyContract(
				chaincodeUrl,
				"getExecutionSnapshot",
				{ instanceId: numericInstanceId },
				"query",
			);
		} catch (error: any) {
			throw new Error(
				error?.message ||
					"createInstance did not produce a readable on-chain instance",
			);
		}

		let targetInstanceId = bpmnInstanceId || "";
		if (!targetInstanceId) {
			const generatedName = `${(bpmn?.name || "BPMN").replace(".bpmn", "")}-instance-${Date.now()}`;
			const created = await addBPMNInstance(
				bpmn.id,
				generatedName,
				effectiveEnvId || currentEnvId || "",
			);
			targetInstanceId = created?.id || created?.data?.id || "";
		}
		if (!targetInstanceId) {
			throw new Error("Failed to persist BPMN instance record");
		}

		const updated = await updateBPMNInstance(targetInstanceId, bpmn.id, {
			instance_chaincode_id: numericInstanceId,
			name: `${(bpmn?.name || "BPMN").replace(".bpmn", "")}-${numericInstanceId}`,
		});
		if (!updated) {
			throw new Error("Failed to update BPMN instance with chain instance id");
		}
		await syncExternalData?.();
		return { bpmnInstanceId: targetInstanceId, instanceChaincodeId: numericInstanceId };
	};

	const participantNameMap = useMemo(() => {
		const map = new Map();
		participants.forEach((participant) => {
			map.set(participant.id, participant.name || participant.id);
		});
		return map;
	}, [participants]);

	useEffect(() => {
		if (!open) {
			return;
		}
		let ignore = false;
		const loadBoundEnvironment = async () => {
			try {
				const bpmn = await retrieveBPMN(bpmnId, currentConsortiumId || "1");
				if (ignore || !bpmn) {
					return;
				}
				const nextEnvType = bpmn.eth_environment
					? "Ethereum"
					: bpmn.environment
						? "Fabric"
						: currentEnvType;
				const nextEnvId = bpmn.eth_environment || bpmn.environment || currentEnvId || "";
				setEffectiveEnvType(nextEnvType);
				setEffectiveEnvId(nextEnvId);

				if (nextEnvType !== "Ethereum" || !nextEnvId) {
					return;
				}

				const [identityDetail, dmnDetail] = await Promise.all([
					getIdentityContractDetail(nextEnvId, false),
					getDmnContractDetailForEthEnv(nextEnvId, false),
				]);
				if (ignore) {
					return;
				}
				setIdentityContractAddress(
					identityDetail?.deployment?.contract_address || "",
				);
				setDmnLiteAddress(dmnDetail?.contract?.address || "");
			} catch (error: any) {
				if (ignore) {
					return;
				}
				setErrorMessage(
					error?.message || "Failed to load BPMN environment defaults",
				);
			}
		};
		loadBoundEnvironment();
		return () => {
			ignore = true;
		};
	}, [open, bpmnId, currentConsortiumId, currentEnvId, currentEnvType]);

	const CreateInstance = async (onlyReturnParam = false) => {
		setErrorMessage("");
		const bpmn = await retrieveBPMN(bpmnId, currentConsortiumId || "1");
		if (!bpmn) {
			throw new Error("BPMN not found");
		}
		const chaincode_url = bpmn.firefly_url;
		if (!chaincode_url) {
			throw new Error("Firefly API URL is not configured for this BPMN");
		}

		const envTypeForInstance =
			effectiveEnvType || (bpmn?.eth_environment ? "Ethereum" : currentEnvType);
		if (envTypeForInstance === "Ethereum") {
			const createInstanceParam = await constructEthereumParam();
			const payload = { params: createInstanceParam };

			if (onlyReturnParam) {
				return {
					param: payload,
					url: chaincode_url,
					contract_name: bpmn.name.split(".")[0],
				};
			}

			const createResult = await callFireflyContract(
				chaincode_url,
				"createInstance",
				payload,
				"invoke",
			);
			await persistEthereumInstance(bpmn, chaincode_url, createResult);
			return;
		}

		const createInstanceParam = await constructFabricParam();
		const singleObject = {};
		for (const item of createInstanceParam) {
			Object.assign(singleObject, item);
		}

		if (onlyReturnParam) {
			return { param: singleObject, url: chaincode_url.slice(0,-4), contract_name:bpmn.name.split(".")[0], };
		}

		await invokeCreateInstance(chaincode_url, singleObject);

		async function constructFabricParam() {
			const createPromise = async (value, key) => {
				const selectedValidationType = value.selectedValidationType;
				if (selectedValidationType === "group") {
					let msp = "";
					if (value.selectedMembershipId) {
						let memberships = await getResourceSets(
							effectiveEnvId || currentEnvId,
							null,
							value.selectedMembershipId,
						);
						msp = memberships[0]?.msp || "";
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
							`Participant ${participantNameMap.get(key) || key} membership is null`,
						);
					}
					let memberships = await getResourceSets(
						effectiveEnvId || currentEnvId,
						null,
						value.selectedMembershipId,
					);
					msp = memberships[0]?.msp || "";
					if (!value.selectedUser) {
						setErrorMessage(
							`Participant ${participantNameMap.get(key) || key} user is null`,
						);
					}

					const fabricIdentity = await retrieveFabricIdentity(
						value.selectedUser,
					);
					const fireflyData = await getFireflyList(
						effectiveEnvId || currentEnvId,
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

		async function constructEthereumParam() {
			if (!dmnLiteAddress) {
				throw new Error("DMN Lite contract address is not available");
			}
			if (!dmnEvalUrl.trim()) {
				throw new Error("DMN evaluate URL is required");
			}

			const params: Record<string, any> = {
				identityContractAddress: identityContractAddress || ZERO_ADDRESS,
				dmnLiteAddress,
				dmnEvalUrl: dmnEvalUrl.trim(),
				enforceBusinessRuleCaller,
			};

			for (const [participantId, value] of showBindingParticipantValueMap.entries()) {
				const participantLabel = participantNameMap.get(participantId) || participantId;
				if (!value?.selectedMembershipId) {
					throw new Error(`Participant ${participantLabel} membership is required`);
				}
				if (value?.selectedValidationType !== "equal") {
					throw new Error(
						`Participant ${participantLabel} currently only supports 相等 binding in Ethereum mode`,
					);
				}
				if (!value?.selectedUser) {
					throw new Error(`Participant ${participantLabel} user is required`);
				}

				const [membership, ethereumIdentity] = await Promise.all([
					getMembership(value.selectedMembershipId, currentConsortiumId || "1"),
					retrieveEthereumIdentity(value.selectedUser),
				]);
				if (!ethereumIdentity?.address) {
					throw new Error(`Participant ${participantLabel} has no Ethereum address`);
				}
				params[`${participantId}_account`] = ethereumIdentity.address;
				params[`${participantId}_org`] =
					membership?.name || membership?.membershipName || "";
			}

			const businessRuleIds = Object.keys(businessRules || {});
			for (const businessRuleId of businessRuleIds) {
				const value = DmnBindingInfo?.[businessRuleId];
				if (!value?.isBinded) {
					throw new Error(`BusinessRule ${businessRuleId} is not bound to a DMN`);
				}
				const dmnContent = value[`${businessRuleId}_Content`] || "";
				const decisionId = value[`${businessRuleId}_DecisionID`] || "";
				if (!dmnContent) {
					throw new Error(`BusinessRule ${businessRuleId} DMN content is required`);
				}
				if (!decisionId) {
					throw new Error(`BusinessRule ${businessRuleId} decision id is required`);
				}
				params[businessRuleId] = {
					dmnContent,
					decisionId,
					callerRestricted: false,
					allowedCaller: ZERO_ADDRESS,
				};
			}

			return params;
		}
	};

	const handleOK = async () => {
		try {
			await CreateInstance();
			setOpen(false);
		} catch (error: any) {
			setErrorMessage(error?.message || "Create instance failed");
		}
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
					<div style={{ flex: "0 1 35%", paddingRight: "10px" }}>
						<h2>Binding BPMN businessRuleTasks and DMN</h2>
						<BindingDmnModal
							bpmnId={bpmnId}
							DmnBindingInfo={DmnBindingInfo}
							setDmnBindingInfo={setDmnBindingInfo}
						/>
					</div>
					<div
						style={{ flex: "0 1 65%", paddingLeft: "10px", height: "600px" }}
					>
						<h2>Binding Participants</h2>
						<BindingParticipant
							participants={participants}
							showBindingParticipantMap={showBindingParticipantMap}
							setShowBindingParticipantMap={setShowBindingParticipantMap}
							showBindingParticipantValueMap={showBindingParticipantValueMap}
							setShowBindingParticipantValueMap={
								setShowBindingParticipantValueMap
							}
							envId={effectiveEnvId}
							envType={effectiveEnvType}
						/>
					</div>
				</div>
				<Button
					type="primary"
					onClick={async () => {
						try {
							const { param, url, contract_name } = await CreateInstance(true);
							navigator.clipboard.writeText(
								`param=${JSON.stringify(param, null, 2).replaceAll("false", "False")}\n    url="${url}"\n    contract_name="${contract_name}"`,
							);
							alert("The parameter has been copied to the clipboard");
						} catch (error: any) {
							setErrorMessage(error?.message || "Build createInstance params failed");
						}
					}}
				>
					Get CreateInstance Param
				</Button>

				{effectiveEnvType === "Ethereum" && (
					<div style={{ textAlign: "left", marginTop: "16px" }}>
						<h3>Ethereum Instance Parameters</h3>
						<div style={{ marginBottom: "12px" }}>
							<label>Identity Contract Address</label>
							<Input
								value={identityContractAddress}
								onChange={(e) => setIdentityContractAddress(e.target.value)}
								placeholder="0x..."
							/>
						</div>
						<div style={{ marginBottom: "12px" }}>
							<label>DMN Lite Contract Address</label>
							<Input
								value={dmnLiteAddress}
								onChange={(e) => setDmnLiteAddress(e.target.value)}
								placeholder="0x..."
							/>
						</div>
						<div style={{ marginBottom: "12px" }}>
							<label>DMN Evaluate URL</label>
							<Input
								value={dmnEvalUrl}
								onChange={(e) => setDmnEvalUrl(e.target.value)}
								placeholder={DEFAULT_DMN_EVAL_URL}
							/>
						</div>
						<div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
							<Switch
								checked={enforceBusinessRuleCaller}
								onChange={setEnforceBusinessRuleCaller}
							/>
							<span>Enforce business rule caller</span>
						</div>
					</div>
				)}

				<div style={{ textAlign: "center", height: "400px" }}>
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
	const [svgContent, {}, refreshSvg] = useBpmnSvg(bpmnId);

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
