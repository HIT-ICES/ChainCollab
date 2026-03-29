import React, { useEffect, useMemo, useState } from "react";
import { Modal, Button, Alert, Input, Switch } from "antd";
import { BindingDmnModal } from "./bindingDmnModal";
import { BindingParticipant } from "./bindingParticipantsModal";
import { useBpmnSvg } from "./hooks";
import { getMembership, retrieveFabricIdentity, retrieveEthereumIdentity } from "@/api/platformAPI";
import { getDmnContractDetailForEthEnv, getFireflyList, getIdentityContractDetail, getResourceSets } from "@/api/resourceAPI";
import { useAppSelector } from "@/redux/hooks";
import { useFireflyData, useParticipantsData } from "../hooks";
import {
	callFireflyContract,
	fireflyBroadcastData,
	fireflyFileTransfer,
	getFireflyData,
	getFireflyVerify,
	invokeCreateInstance,
} from "@/api/executionAPI";
import {
	addBPMNInstance,
	retrieveBPMN,
	retrieveDmn,
	updateBPMNInstance,
	updateDmn,
} from "@/api/externalResource";
import { useBusinessRulesDataByBpmn } from "./hooks";

const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
const ZERO_BYTES32 = `0x${"0".repeat(64)}`;
const DEFAULT_DMN_EVAL_URL = "http://cdmn-node1:5000/api/dmn/evaluate";
const ETH_INSTANCE_POLL_ATTEMPTS = 15;
const ETH_INSTANCE_POLL_INTERVAL_MS = 2000;

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

	const sleep = (ms: number) =>
		new Promise((resolve) => {
			window.setTimeout(resolve, ms);
		});

	const normalizeHttpUrl = (value: string) => {
		if (!value) {
			return "";
		}
		return value.startsWith("http://") || value.startsWith("https://")
			? value
			: `http://${value}`;
	};

	const extractCidFromFireflyData = (payload: any) => {
		const publicUrl =
			payload?.blob?.public || payload?.blob?.url || payload?.blob?.href || "";
		if (!publicUrl) {
			return "";
		}
		const value = String(publicUrl).trim();
		const match = value.match(/\/ipfs\/([^/?#]+)/);
		if (match?.[1]) {
			return match[1];
		}
		if (/^(Qm[1-9A-HJ-NP-Za-km-z]{44}|bafy[1-9A-HJ-NP-Za-km-z]+)$/.test(value)) {
			return value;
		}
		return "";
	};

	const ensureDmnStoredForEthereum = async (
		dmnId: string,
		dmnContent: string,
	) => {
		if (!currentConsortiumId) {
			throw new Error("Consortium id is required for DMN storage");
		}
		if (!dmnId) {
			throw new Error("DMN id is required");
		}
		if (!dmnContent) {
			throw new Error(`DMN ${dmnId} content is empty`);
		}

		const existingDmn = await retrieveDmn(currentConsortiumId, dmnId);
		if (existingDmn?.cid) {
			return {
				dmnCid: existingDmn.cid,
				dmnHash: existingDmn.contentHash || ZERO_BYTES32,
				fireflyDataId: existingDmn.fireflyDataId || "",
			};
		}

		const fireflyList = await getFireflyList(
			effectiveEnvId || currentEnvId,
			null,
			null,
			"Ethereum",
		);
		const fireflyCoreUrl = normalizeHttpUrl(fireflyList?.[0]?.coreURL || "");
		if (!fireflyCoreUrl) {
			throw new Error("FireFly core is not available for DMN upload");
		}

		const uploadedFile = new File(
			[new Blob([dmnContent], { type: "application/xml" })],
			`${dmnId}.dmn`,
			{ type: "application/xml" },
		);
		const uploadResult = await fireflyFileTransfer(fireflyCoreUrl, uploadedFile);
		const dataId =
			uploadResult?.id ||
			uploadResult?.data?.id ||
			uploadResult?.data?.[0]?.id ||
			"";
		if (!dataId) {
			throw new Error(`Failed to upload DMN ${dmnId} to FireFly data manager`);
		}

		await fireflyBroadcastData(fireflyCoreUrl, dataId);
		let cid = "";
		for (let attempt = 0; attempt < 10; attempt++) {
			if (attempt > 0) {
				await sleep(1000);
			} else {
				await sleep(1500);
			}
			const fireflyData = await getFireflyData(fireflyCoreUrl, dataId);
			cid = extractCidFromFireflyData(fireflyData);
			if (cid) {
				break;
			}
		}
		if (!cid) {
			throw new Error(`Failed to resolve CID for DMN ${dmnId}`);
		}

		const updatedDmn = await updateDmn(currentConsortiumId, dmnId, {
			fireflyDataId: dataId,
			cid,
			dmnContent,
		});
		if (!updatedDmn) {
			throw new Error(`Failed to persist CID metadata for DMN ${dmnId}`);
		}

		return {
			dmnCid: updatedDmn.cid || cid,
			dmnHash: updatedDmn.contentHash || ZERO_BYTES32,
			fireflyDataId: updatedDmn.fireflyDataId || dataId,
		};
	};

	const waitForEthereumInstance = async (
		chaincodeUrl: string,
		createResult: any,
		startingCounter: number | null,
	) => {
		let lastError: any = null;
		for (let attempt = 0; attempt < ETH_INSTANCE_POLL_ATTEMPTS; attempt++) {
			try {
				const queryResult = await callFireflyContract(
					chaincodeUrl,
					"currentInstanceId",
					{},
					"query",
				);
				const resolvedCounter = extractFireflyScalar(queryResult);
				const numericCounter = Number(resolvedCounter);
				if (!Number.isFinite(numericCounter)) {
					throw new Error(
						`Invalid instance counter returned from FireFly: ${resolvedCounter}`,
					);
				}

				if (
					startingCounter !== null &&
					Number.isFinite(startingCounter) &&
					numericCounter <= startingCounter
				) {
					throw new Error("instance counter has not advanced yet");
				}

				const fallbackId = extractFireflyScalar(createResult);
				const numericInstanceId =
					numericCounter > 0 ? numericCounter - 1 : Number(fallbackId ?? 0);
				if (!Number.isFinite(numericInstanceId) || numericInstanceId < 0) {
					throw new Error(
						`Invalid instance id returned from FireFly: ${fallbackId}`,
					);
				}

				await callFireflyContract(
					chaincodeUrl,
					"getExecutionSnapshot",
					{ instanceId: numericInstanceId },
					"query",
				);
				return numericInstanceId;
			} catch (error: any) {
				lastError = error;
				if (attempt < ETH_INSTANCE_POLL_ATTEMPTS - 1) {
					await sleep(ETH_INSTANCE_POLL_INTERVAL_MS);
				}
			}
		}

		throw new Error(
			lastError?.message ||
				"createInstance did not produce a readable on-chain instance in time",
		);
	};

	const persistEthereumInstance = async (
		bpmn: any,
		chaincodeUrl: string,
		createResult: any,
		startingCounter: number | null,
		executionBindings: Record<string, any>,
	) => {
		const numericInstanceId = await waitForEthereumInstance(
			chaincodeUrl,
			createResult,
			startingCounter,
		);

		let targetInstanceId = bpmnInstanceId || "";
		if (!targetInstanceId) {
			const generatedName = `${(bpmn?.name || "BPMN").replace(".bpmn", "")}-instance-${Date.now()}`;
			const created = await addBPMNInstance(
				bpmn.id,
				generatedName,
				effectiveEnvId || currentEnvId || "",
				executionBindings,
			);
			targetInstanceId = created?.id || created?.data?.id || "";
		}
		if (!targetInstanceId) {
			throw new Error("Failed to persist BPMN instance record");
		}

		const updated = await updateBPMNInstance(targetInstanceId, bpmn.id, {
			instance_chaincode_id: numericInstanceId,
			name: `${(bpmn?.name || "BPMN").replace(".bpmn", "")}-${numericInstanceId}`,
			execution_bindings: executionBindings,
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
			const { params: createInstanceParam, executionBindings } =
				await constructEthereumParam();
			const payload = { params: createInstanceParam };

			if (onlyReturnParam) {
				return {
					param: payload,
					url: chaincode_url,
					contract_name: bpmn.name.split(".")[0],
				};
			}

			let startingCounter: number | null = null;
			try {
				const preCreateCounter = await callFireflyContract(
					chaincode_url,
					"currentInstanceId",
					{},
					"query",
				);
				const resolvedCounter = extractFireflyScalar(preCreateCounter);
				const numericCounter = Number(resolvedCounter);
				if (Number.isFinite(numericCounter)) {
					startingCounter = numericCounter;
				}
			} catch (error) {
				startingCounter = null;
			}

			const createResult = await callFireflyContract(
				chaincode_url,
				"createInstance",
				payload,
				"invoke",
			);
			await persistEthereumInstance(
				bpmn,
				chaincode_url,
				createResult,
				startingCounter,
				executionBindings,
			);
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
			const executionBindings: Record<string, any> = {
				participants: {},
				business_rules: {},
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
				executionBindings.participants[participantId] = {
					membership_id: value.selectedMembershipId,
					ethereum_identity_id: value.selectedUser,
					address: ethereumIdentity.address,
					org_name: membership?.name || membership?.membershipName || "",
				};
			}

			const businessRuleIds = Object.keys(businessRules || {});
			for (const businessRuleId of businessRuleIds) {
				const value = DmnBindingInfo?.[businessRuleId];
				if (!value?.isBinded) {
					throw new Error(`BusinessRule ${businessRuleId} is not bound to a DMN`);
				}
				const dmnId = value[`${businessRuleId}_DMNID`] || "";
				const dmnContent = value[`${businessRuleId}_Content`] || "";
				const decisionId = value[`${businessRuleId}_DecisionID`] || "";
				if (!dmnId) {
					throw new Error(`BusinessRule ${businessRuleId} DMN id is required`);
				}
				if (!dmnContent) {
					throw new Error(`BusinessRule ${businessRuleId} DMN content is required`);
				}
				if (!decisionId) {
					throw new Error(`BusinessRule ${businessRuleId} decision id is required`);
				}
				const dmnStorage = await ensureDmnStoredForEthereum(dmnId, dmnContent);
				params[businessRuleId] = {
					dmnCid: dmnStorage.dmnCid,
					dmnHash: dmnStorage.dmnHash,
					decisionId,
					callerRestricted: false,
					allowedCaller: ZERO_ADDRESS,
				};
				executionBindings.business_rules[businessRuleId] = {
					dmn_id: dmnId,
					dmn_cid: dmnStorage.dmnCid,
					dmn_hash: dmnStorage.dmnHash,
					firefly_data_id: dmnStorage.fireflyDataId,
					callerRestricted: false,
					allowedCaller: ZERO_ADDRESS,
					decisionId,
				};
			}

			return { params, executionBindings };
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
