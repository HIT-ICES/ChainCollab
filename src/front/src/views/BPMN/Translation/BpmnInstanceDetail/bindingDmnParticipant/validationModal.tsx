import React, { useState, useEffect } from "react";
import { Modal, Button, Descriptions, message, Alert, Table } from "antd";
import { useBpmnSvg } from "./hooks";
import { retrieveBPMN } from "@/api/externalResource";
import { fireflyAPI } from "@/api/apiConfig";

// 参与者信息接口
interface ParticipantInfo {
	participantId: string;       // 参与者 ID，如 "Participant_1auujox"
	x509Encoded: string;         // x509 字段中 @ 前面的 base64 编码部分
	x509Decoded: string;         // base64 解码后的内容
}

interface ValidationModalProps {
	open: boolean;
	setOpen: (open: boolean) => void;
	param: any;
	url: string;
	contract_name: string;
	bpmnId: string;
	consortiumId: string;
}

export const ValidationModal: React.FC<ValidationModalProps> = ({
	open,
	setOpen,
	param,
	url,
	contract_name,
	bpmnId,
	consortiumId,
}) => {
	const [svgContent] = useBpmnSvg(bpmnId);
	const [validationResult, setValidationResult] = useState<{
		success: boolean;
		message: string;
		dataObjectContractMap?: Record<string, string>;
		errors?: Array<{ dataObjectId: string; taskIds: string[]; contracts: string[] }>;
	} | null>(null);
	const [isValidating, setIsValidating] = useState(false);
	// 存储 Firefly API 列表中 chaincode 到 name 的映射
	const [chaincodeToNameMap, setChaincodeToNameMap] = useState<Record<string, string>>({});
	const [isLoadingApiList, setIsLoadingApiList] = useState(false);
	// 存储参与者信息列表
	const [participantInfoList, setParticipantInfoList] = useState<ParticipantInfo[]>([]);

	/**
	 * 从 param 中提取参与者信息
	 * 提取 Participant_xxx 字段，解析 x509 中 @ 前面的 base64 编码部分并解码
	 */
	const extractParticipantInfo = (paramData: any): ParticipantInfo[] => {
		const result: ParticipantInfo[] = [];
		const excludeKeys = ["ERCChaincodeNames", "BpmnId"];

		for (const key of Object.keys(paramData)) {
			// 跳过非参与者字段
			if (excludeKeys.includes(key)) continue;
			// 检查是否是参与者字段（以 Participant_ 开头）
			if (!key.startsWith("Participant_")) continue;

			const participantData = paramData[key];
			if (!participantData || !participantData.x509) continue;

			const x509Full = participantData.x509;
			// 提取 @ 前面的部分
			const atIndex = x509Full.indexOf("@");
			const x509Encoded = atIndex > -1 ? x509Full.substring(0, atIndex) : x509Full;

			// Base64 解码
			let x509Decoded = "";
			try {
				x509Decoded = atob(x509Encoded);
			} catch (e) {
				console.warn(`Failed to decode base64 for ${key}:`, e);
				x509Decoded = "[解码失败]";
			}

			result.push({
				participantId: key,
				x509Encoded,
				x509Decoded,
			});
		}

		return result;
	};

	// 组件打开时自动提取参与者信息
	useEffect(() => {
		if (!open || !param) return;

		console.log("=== 提取参与者信息 ===");
		const participantList = extractParticipantInfo(param);
		setParticipantInfoList(participantList);

		console.log("参与者信息列表:");
		participantList.forEach((info, index) => {
			console.log(`\n[${index + 1}] ${info.participantId}`);
			console.log(`    x509Encoded: ${info.x509Encoded}`);
			console.log(`    x509Decoded: ${info.x509Decoded}`);
		});
		console.log("\n=== 参与者信息提取完成 ===\n");
	}, [open, param]);

	// 组件打开时自动获取 Firefly API 列表
	useEffect(() => {
		const fetchFireflyApiList = async () => {
			if (!open || !url) return;

			setIsLoadingApiList(true);
			try {
				// 使用固定的 5001 端口
				const fireflyBaseUrl = "http://127.0.0.1:5001";
				console.log("=== 自动获取 Firefly API 列表 ===");
				console.log("Firefly Base URL:", fireflyBaseUrl);

				const result = await getFireflyApiList(fireflyBaseUrl);
				setChaincodeToNameMap(result);
				console.log("chaincodeToNameMap 已更新:", result);
				console.log("=== Firefly API 列表获取完成 ===\n");
			} catch (error) {
				console.error("获取 Firefly API 列表失败:", error);
			} finally {
				setIsLoadingApiList(false);
			}
		};

		fetchFireflyApiList();
	}, [open, url]);

	// 组件打开且数据加载完成后自动执行校验
	useEffect(() => {
		if (!open || isLoadingApiList || participantInfoList.length === 0) return;

		// 自动执行合并后的校验
		handleCombinedValidation();
	}, [open, isLoadingApiList, participantInfoList]);

	/**
	 * 调用合约函数的模板方法
	 * 参考 ERCAddMintAuthority 的调用方式，本质上是通过 Firefly API 调用链码
	 *
	 * @param methodName - 要调用的合约方法名 (如 "mint", "transfer", "burn" 等)
	 * @param chaincodeUrl - 链码的 Firefly URL (如 "http://127.0.0.1:5002/api/v1/namespaces/default/apis/test9-bdccb7")
	 * @param inputParams - 调用方法的输入参数
	 * @returns 调用结果
	 *
	 * 调用链说明:
	 * 1. ERCAddMintAuthority (externalResource.ts) 遍历 ercIdTokenMap
	 * 2. 调用 invokeAddAuthority (executionAPI.ts)
	 * 3. invokeAddAuthority 使用 fireflyAPI.post 发送请求到 Firefly
	 * 4. Firefly 将请求转发到区块链上的智能合约
	 */
	const invokeContractMethod = async (
		methodName: string,
		chaincodeUrl: string,
		inputParams: Record<string, any>
	) => {
		try {
			console.log(`[invokeContractMethod] 调用合约方法: ${methodName}`);
			console.log(`[invokeContractMethod] Chaincode URL: ${chaincodeUrl}`);
			console.log(`[invokeContractMethod] 输入参数:`, inputParams);

			// 构建请求 URL: 移除末尾的 /api 部分，添加 /query/{methodName}
			// 例如: http://127.0.0.1:5002/api/v1/namespaces/default/apis/test9-bdccb7
			//    -> http://127.0.0.1:5002/api/v1/namespaces/default/apis/test9-bdccb7/query/mint
			const invokeUrl = `${chaincodeUrl}/query/${methodName}`;

			// 构建请求体
			const requestBody = {
				input: inputParams
			};

			console.log(`[invokeContractMethod] 请求 URL: ${invokeUrl}`);
			console.log(`[invokeContractMethod] 请求体:`, requestBody);

			// 发送 POST 请求到 Firefly API
			const res = await fireflyAPI.post(invokeUrl, requestBody);

			console.log(`[invokeContractMethod] 调用成功，返回结果:`, res.data);
			message.success(`合约方法 ${methodName} 调用成功`);

			return res.data;
		} catch (error: any) {
			console.error(`[invokeContractMethod] 调用合约方法 ${methodName} 失败:`, error);
			message.error(`调用合约方法 ${methodName} 失败: ${error?.message || "未知错误"}`);
			throw error;
		}
	};

	/**
	 * 查询 FT (ERC20) 代币余额
	 * 根据 chaincodeName 和参与者的 base64 编码查询余额
	 *
	 * @param chaincodeName - 合约名称 (如 "ERC20")
	 * @param accountBase64 - 参与者的 base64 编码 (如 "eDUwOTo6Q049dXNlcjEsT1U9...")
	 * @returns 余额查询结果
	 */
	const FTqueryBalanceOf = async (chaincodeName: string, accountBase64: string) => {
		console.log(`[FTqueryBalanceOf] 开始查询余额`);
		console.log(`[FTqueryBalanceOf] chaincodeName: ${chaincodeName}`);
		console.log(`[FTqueryBalanceOf] accountBase64: ${accountBase64}`);

		// 1. 从 chaincodeToNameMap 中查找完整的 API 名称
		// chaincodeToNameMap 的结构是 { chaincode: apiName }，需要反向查找
		// 例如: { "ERC20-eda31c-chaincode": "ERC20-eda31c" }
		// 但实际上我们需要根据 chaincodeName (如 "ERC20") 匹配到 apiName (如 "ERC20-eda31c")
		let matchedApiName: string | null = null;

		for (const [, apiName] of Object.entries(chaincodeToNameMap)) {
			// 检查 apiName 是否以 chaincodeName 开头（如 "ERC20-eda31c" 以 "ERC20" 开头）
			if (apiName.startsWith(chaincodeName)) {
				matchedApiName = apiName;
				console.log(`[FTqueryBalanceOf] 匹配成功: ${chaincodeName} -> ${apiName}`);
				break;
			}
		}

		if (!matchedApiName) {
			const error = `未找到与 ${chaincodeName} 匹配的 API`;
			console.error(`[FTqueryBalanceOf] ${error}`);
			message.error(error);
			throw new Error(error);
		}

		// 2. 构建 chaincodeUrl
		// 使用固定的 5001 端口
		const chaincodeUrl = `http://127.0.0.1:5001/api/v1/namespaces/default/apis/${matchedApiName}`;
		console.log(`[FTqueryBalanceOf] chaincodeUrl: ${chaincodeUrl}`);

		// 3. 构建输入参数
		const inputParams = {
			account: accountBase64,
			instanceID: "0",
		};
		console.log(`[FTqueryBalanceOf] inputParams:`, inputParams);

		// 4. 调用合约方法
		return await invokeContractMethod("BalanceOf", chaincodeUrl, inputParams);
	};

	/**
	 * 查询 NFT 代币所有者
	 * 根据 chaincodeName 和 tokenId 查询 NFT 的当前所有者
	 *
	 * @param chaincodeName - 合约名称 (如 "ERC721")
	 * @param tokenId - NFT 的 tokenId
	 * @returns 所有者查询结果
	 */
	const NFTqueryOwnerOf = async (chaincodeName: string, tokenId: string) => {
		console.log(`[NFTqueryOwnerOf] 开始查询 NFT 所有者`);
		console.log(`[NFTqueryOwnerOf] chaincodeName: ${chaincodeName}`);
		console.log(`[NFTqueryOwnerOf] tokenId: ${tokenId}`);

		// 1. 从 chaincodeToNameMap 中查找完整的 API 名称
		let matchedApiName: string | null = null;

		for (const [, apiName] of Object.entries(chaincodeToNameMap)) {
			// 检查 apiName 是否以 chaincodeName 开头
			if (apiName.startsWith(chaincodeName)) {
				matchedApiName = apiName;
				console.log(`[NFTqueryOwnerOf] 匹配成功: ${chaincodeName} -> ${apiName}`);
				break;
			}
		}

		if (!matchedApiName) {
			const error = `未找到与 ${chaincodeName} 匹配的 API`;
			console.error(`[NFTqueryOwnerOf] ${error}`);
			message.error(error);
			throw new Error(error);
		}

		// 2. 构建 chaincodeUrl
		// 使用固定的 5001 端口
		const chaincodeUrl = `http://127.0.0.1:5001/api/v1/namespaces/default/apis/${matchedApiName}`;
		console.log(`[NFTqueryOwnerOf] chaincodeUrl: ${chaincodeUrl}`);

		// 3. 构建输入参数
		const inputParams = {
			tokenId: tokenId,
		};
		console.log(`[NFTqueryOwnerOf] inputParams:`, inputParams);

		// 4. 调用合约方法
		return await invokeContractMethod("OwnerOf", chaincodeUrl, inputParams);
	};

	/**
	 * 查询 Distributive NFT 余额
	 * @param chaincodeName - 链码名称
	 * @param tokenId - Token ID
	 * @param account - 账户地址
	 * @returns 余额查询结果
	 */
	const DisNFTquery = async (chaincodeName: string, tokenId: string, account: string) => {
		console.log(`[DisNFTquery] 开始查询 Distributive NFT 余额`);
		console.log(`[DisNFTquery] chaincodeName: ${chaincodeName}`);
		console.log(`[DisNFTquery] tokenId: ${tokenId}`);
		console.log(`[DisNFTquery] account: ${account}`);

		// 1. 从 chaincodeToNameMap 中查找完整的 API 名称
		let matchedApiName: string | null = null;

		for (const [, apiName] of Object.entries(chaincodeToNameMap)) {
			// 检查 apiName 是否以 chaincodeName 开头
			if (apiName.startsWith(chaincodeName)) {
				matchedApiName = apiName;
				console.log(`[DisNFTquery] 匹配成功: ${chaincodeName} -> ${apiName}`);
				break;
			}
		}

		if (!matchedApiName) {
			const error = `未找到与 ${chaincodeName} 匹配的 API`;
			console.error(`[DisNFTquery] ${error}`);
			message.error(error);
			throw new Error(error);
		}

		// 2. 构建 chaincodeUrl
		// 使用固定的 5001 端口
		const chaincodeUrl = `http://127.0.0.1:5001/api/v1/namespaces/default/apis/${matchedApiName}`;
		console.log(`[DisNFTquery] chaincodeUrl: ${chaincodeUrl}`);

		// 3. 构建输入参数
		const inputParams = {
			account: account,
			id: tokenId,
		};
		console.log(`[DisNFTquery] inputParams:`, inputParams);

		// 4. 调用合约方法
		return await invokeContractMethod("BalanceOf", chaincodeUrl, inputParams);
	};

	/**
	 * 获取 Firefly API 列表并提取 chaincode 和 name 的映射
	 * 调用 http://{host}/api/v1/namespaces/default/apis 获取所有注册的 API
	 *
	 * @param fireflyBaseUrl - Firefly 基础 URL (如 "http://127.0.0.1:5002")
	 * @returns chaincode 到 API name 的映射 { chaincode: name }
	 */
	const getFireflyApiList = async (fireflyBaseUrl: string) => {
		try {
			const apisUrl = `${fireflyBaseUrl}/api/v1/namespaces/default/apis`;
			console.log(`[getFireflyApiList] 请求 URL: ${apisUrl}`);

			const res = await fireflyAPI.get(apisUrl);
			const apisList = res.data;

			console.log(`[getFireflyApiList] 获取到 ${Array.isArray(apisList) ? apisList.length : 0} 个 API`);

			if (!Array.isArray(apisList)) {
				console.error(`[getFireflyApiList] 返回数据格式错误:`, apisList);
				return {};
			}

			// 提取 chaincode 和 name 的映射
			const chaincodeToNameMap: Record<string, string> = {};

			apisList.forEach((api: any) => {
				const chaincode = api.location?.chaincode;
				const name = api.name;

				if (chaincode && name) {
					chaincodeToNameMap[chaincode] = name;
				}
			});

			console.log(`[getFireflyApiList] 提取的 chaincode -> name 映射:`);
			console.table(chaincodeToNameMap);

			return chaincodeToNameMap;
		} catch (error: any) {
			console.error(`[getFireflyApiList] 获取 API 列表失败:`, error);
			return {};
		}
	};

	// 定义验证结果类型
	interface ValidationResult {
		dataObjectId: string;
		assetType: string;
		tokenType?: string;
		success: boolean;
		errors: string[];
		finalOwner?: string;
		finalUsageRights?: string[];
	}

	/**
	 * 基于资产类型的推理验证框架
	 * 扫描所有 DataObject 元素，收集关联的 Task 元素，并根据资产类型进行不同的推理验证
	 */
	const performAssetTypeBasedValidation = async () => {
		// 辅助函数：查找 documentation 元素（支持多种命名空间前缀）
		const findDocumentation = (element: any): HTMLCollectionOf<Element> | null => {
			// 尝试 bpmn: 前缀
			let doc = element.getElementsByTagName("bpmn:documentation");
			if (doc.length > 0) return doc;

			// 尝试 bpmn2: 前缀
			doc = element.getElementsByTagName("bpmn2:documentation");
			if (doc.length > 0) return doc;

			// 尝试无前缀
			doc = element.getElementsByTagName("documentation");
			if (doc.length > 0) return doc;

			return null;
		};

		try {
			// 获取 BPMN XML
			const bpmnData = await retrieveBPMN(bpmnId, consortiumId);
			if (!bpmnData) {
				throw new Error("Failed to retrieve BPMN data - API returned null");
			}

			const bpmnXml = bpmnData.bpmnContent;
			if (!bpmnXml) {
				throw new Error("BPMN data does not contain bpmnContent field");
			}

			// 解析 BPMN XML
			const parser = new DOMParser();
			const xmlDoc = parser.parseFromString(bpmnXml, "text/xml");

			// 检查解析错误
			const parseError = xmlDoc.getElementsByTagName("parsererror");
			if (parseError.length > 0) {
				console.error("XML Parse Error:", parseError[0].textContent);
				throw new Error("Failed to parse BPMN XML");
			}

			// 扫描所有 DataObject 元素
			// 注意：只查找 dataObjectReference 元素，不包括 dataObject 定义元素
			// dataObjectReference 元素才包含 documentation 信息
			const dataObjects = xmlDoc.querySelectorAll('dataObjectReference, bpmn\\:dataObjectReference, bpmn2\\:dataObjectReference');

			// 存储每个 DataObject 及其关联的 Tasks
			const dataObjectTaskMap: Record<string, {
				dataObjectId: string;
				assetType: string;
				tokenType?: string;
				tokenName?: string;
				tokenId?: string;
				tokenHasExistInERC?: boolean;  // Token 是否已存在于 ERC 合约中
				tasks: Array<{
					taskId: string;
					operation?: string;
					documentation?: string;  // Task 的完整 documentation 内容
					isInput: boolean;  // Task -> DataObject (input) or DataObject -> Task (output)
				}>;
			}> = {};

			// 遍历所有 DataObject，提取资产信息
			dataObjects.forEach((dataObj: any) => {
				const dataObjectId = dataObj.getAttribute("id");

				// 使用辅助函数查找 documentation
				const finalDocumentation = findDocumentation(dataObj);

				if (finalDocumentation && finalDocumentation.length > 0) {
					try {
						const docText = finalDocumentation[0].textContent;
						const assetInfo = JSON.parse(docText);

						dataObjectTaskMap[dataObjectId] = {
							dataObjectId,
							assetType: assetInfo.assetType || "",
							tokenType: assetInfo.tokenType,
							tokenName: assetInfo.tokenName,
							tokenId: assetInfo.tokenId,
							tokenHasExistInERC: assetInfo.tokenHasExistInERC || false,
							tasks: []
						};
					} catch (error) {
						console.warn(`Failed to parse documentation for ${dataObjectId}:`, error);
					}
				}
			});

			// 扫描所有关联关系（DataInputAssociation 和 DataOutputAssociation）
			const allElements = xmlDoc.getElementsByTagName("*");

			for (let i = 0; i < allElements.length; i++) {
				const el = allElements[i];
				const tagName = el.tagName.toLowerCase();

				// 处理 DataInputAssociation (DataObject -> Task)
				if (tagName.includes("datainputassociation")) {
					const sourceRef = el.querySelector("sourceRef")?.textContent?.trim();

					// 找到父 Task
					let taskElement = el.parentElement;
					let depth = 0;
					while (taskElement && !taskElement.tagName.toLowerCase().includes("task") && depth < 10) {
						taskElement = taskElement.parentElement;
						depth++;
					}

					if (taskElement && sourceRef && dataObjectTaskMap[sourceRef]) {
						const taskId = taskElement.getAttribute("id");
						const taskDoc = findDocumentation(taskElement);
						let operation = "";
						let documentation = "";

						if (taskDoc && taskDoc.length > 0) {
							try {
								documentation = taskDoc[0].textContent || "";
								const taskInfo = JSON.parse(documentation);
								operation = taskInfo.operation || "";
							} catch {}
						}

						dataObjectTaskMap[sourceRef].tasks.push({
							taskId,
							operation,
							documentation,
							isInput: false  // DataObject -> Task (Task 使用 DataObject 作为输入)
						});
					}
				}

				// 处理 DataOutputAssociation (Task -> DataObject)
				if (tagName.includes("dataoutputassociation")) {
					const targetRef = el.querySelector("targetRef")?.textContent?.trim();

					// 找到父 Task
					let taskElement = el.parentElement;
					let depth = 0;
					while (taskElement && !taskElement.tagName.toLowerCase().includes("task") && depth < 10) {
						taskElement = taskElement.parentElement;
						depth++;
					}

					if (taskElement && targetRef && dataObjectTaskMap[targetRef]) {
						const taskId = taskElement.getAttribute("id");
						const taskDoc = findDocumentation(taskElement);
						let operation = "";
						let documentation = "";

						if (taskDoc && taskDoc.length > 0) {
							try {
								documentation = taskDoc[0].textContent || "";
								const taskInfo = JSON.parse(documentation);
								operation = taskInfo.operation || "";
							} catch {}
						}

						dataObjectTaskMap[targetRef].tasks.push({
							taskId,
							operation,
							documentation,
							isInput: true  // Task -> DataObject (Task 产生 DataObject 作为输出)
						});
					}
				}
			}

			// 根据资产类型进行分支推理
			// 收集所有验证结果
			const allValidationResults: ValidationResult[] = [];

			for (const [dataObjectId, info] of Object.entries(dataObjectTaskMap)) {
				console.log(`\n=== Validating DataObject: ${dataObjectId} ===`);

				// 打印完整的 DataObject 信息对象
				console.log("DataObject 完整信息:", {
					dataObjectId: info.dataObjectId,
					assetType: info.assetType,
					tokenType: info.tokenType,
					tokenName: info.tokenName,
					tokenId: info.tokenId,
					tokenHasExistInERC: info.tokenHasExistInERC,
					tasks: info.tasks.map((task, index) => ({
						序号: index + 1,
						taskId: task.taskId,
						operation: task.operation || 'N/A',
					documentation: task.documentation || 'N/A',
						direction: task.isInput ? 'Task → DataObject (output)' : 'DataObject → Task (input)',
						isInput: task.isInput
					})),
					任务总数: info.tasks.length
				});

				// 确定应该进入哪个验证分支
				let targetBranch = "";
				if (info.assetType === "transferable" && info.tokenType === "FT") {
					targetBranch = "分支 1: Transferable FT";
				} else if (info.assetType === "transferable" && info.tokenType === "NFT") {
					targetBranch = "分支 2: Transferable NFT";
				} else if (info.assetType === "value-added") {
					targetBranch = "分支 3: Value-added NFT";
				} else if (info.assetType === "distributive") {
					targetBranch = "分支 4: Distributive NFT";
				} else {
					targetBranch = "未知分支 (Unknown asset type combination)";
				}

				console.log(`\n>>> 该 DataObject 将进入: ${targetBranch} <<<\n`);

				let result: ValidationResult | null = null;

				// 分支 1: Transferable FT
				if (info.assetType === "transferable" && info.tokenType === "FT") {
					console.log("Branch: Transferable FT");
					result = await validateTransferableFT(info);
				}
				// 分支 2: Transferable NFT
				else if (info.assetType === "transferable" && info.tokenType === "NFT") {
					console.log("Branch: Transferable NFT");
					result = await validateTransferableNFT(info);
				}
				// 分支 3: Value-added NFT
				else if (info.assetType === "value-added") {
					console.log("Branch: Value-added NFT");
					result = await validateValueAddedNFT(info);
				}
				// 分支 4: Distributive NFT
				else if (info.assetType === "distributive") {
					console.log("Branch: Distributive NFT");
					result = await validateDistributiveNFT(info);
				}
				else {
					console.warn(`Unknown asset type combination: ${info.assetType} / ${info.tokenType}`);
					result = {
						dataObjectId: info.dataObjectId,
						assetType: info.assetType,
						tokenType: info.tokenType,
						success: false,
						errors: [`未知资产类型组合: ${info.assetType} / ${info.tokenType}`],
					};
				}

				if (result) {
					allValidationResults.push(result);
				}
			}

			console.log("=== Asset Type Based Validation Complete ===");

			// 显示汇总弹窗
			const successResults = allValidationResults.filter(r => r.success);
			const failedResults = allValidationResults.filter(r => !r.success);

			if (failedResults.length > 0) {
				// 有失败的验证
				Modal.error({
					title: "资产类型推理验证结果",
					content: (
						<div style={{ maxHeight: "400px", overflow: "auto" }}>
							<p>共验证 {allValidationResults.length} 个 DataObject，其中 {failedResults.length} 个失败：</p>
							{failedResults.map((result, idx) => (
								<div key={idx} style={{ marginTop: "15px", padding: "10px", background: "#fff2f0", borderRadius: "4px" }}>
									<p style={{ fontWeight: "bold", color: "#ff4d4f" }}>
										{result.dataObjectId} ({result.assetType}{result.tokenType ? ` - ${result.tokenType}` : ""})
									</p>
									<ul style={{ paddingLeft: "20px", margin: "5px 0" }}>
										{result.errors.map((err, errIdx) => (
											<li key={errIdx} style={{ marginBottom: "3px" }}>{err}</li>
										))}
									</ul>
								</div>
							))}
							{successResults.length > 0 && (
								<div style={{ marginTop: "15px" }}>
									<p style={{ color: "#52c41a" }}>验证通过的 DataObject ({successResults.length} 个):</p>
									<ul style={{ paddingLeft: "20px", margin: "5px 0" }}>
										{successResults.map((result, idx) => (
											<li key={idx}>
												{result.dataObjectId} ({result.assetType}{result.tokenType ? ` - ${result.tokenType}` : ""})
												{result.finalOwner && ` - 最终所有者: ${result.finalOwner}`}
											</li>
										))}
									</ul>
								</div>
							)}
						</div>
					),
					width: 700,
				});
			} else if (allValidationResults.length > 0) {
				// 全部验证通过
				Modal.success({
					title: "资产类型推理验证通过",
					content: (
						<div style={{ maxHeight: "400px", overflow: "auto" }}>
							<p>共验证 {allValidationResults.length} 个 DataObject，全部通过：</p>
							{allValidationResults.map((result, idx) => (
								<div key={idx} style={{ marginTop: "10px", padding: "8px", background: "#f6ffed", borderRadius: "4px" }}>
									<p style={{ fontWeight: "bold", color: "#52c41a", margin: 0 }}>
										{result.dataObjectId} ({result.assetType}{result.tokenType ? ` - ${result.tokenType}` : ""})
									</p>
									{result.finalOwner && <p style={{ margin: "5px 0 0 0" }}>最终所有者: {result.finalOwner}</p>}
									{result.finalUsageRights && result.finalUsageRights.length > 0 && (
										<p style={{ margin: "5px 0 0 0" }}>使用权: [{result.finalUsageRights.join(", ")}]</p>
									)}
								</div>
							))}
						</div>
					),
					width: 600,
				});
			} else {
				message.info("没有找到需要验证的 DataObject");
			}

		} catch (error) {
			console.error("Asset type based validation error:", error);
			message.error("资产类型推理验证失败");
		}
	};

	/**
	 * 分支 1: Transferable FT 验证逻辑
	 * FT（同质化代币）使用余额追踪方案：
	 * - 每个参与者初始余额为 0
	 * - mint: 给 callee 增加 tokenNumber 数量
	 * - burn: 从 caller 减少 tokenNumber 数量（需检查余额）
	 * - Transfer: 从 caller 减少，给 callee 增加 tokenNumber 数量（需检查 caller 余额）
	 * - query: 不影响余额
	 */
	const validateTransferableFT = async (info: any): Promise<ValidationResult> => {
		console.log("Validating Transferable FT");
		// 可用操作: mint, burn, Transfer, query
		// 特点: 使用 tokenNumber, 不需要 tokenId
		// 注意: FT 不使用 tokenHasExistInERC 字段，因为 FT 没有单独的 tokenId

		// 获取 BPMN XML 用于解析 SequenceFlow
		const bpmnData = await retrieveBPMN(bpmnId, consortiumId);
		if (!bpmnData || !bpmnData.bpmnContent) {
			console.error("Failed to retrieve BPMN data for task ordering");
			return {
				dataObjectId: info.dataObjectId,
				assetType: info.assetType,
				tokenType: info.tokenType,
				success: false,
				errors: ["无法获取 BPMN 数据"],
			};
		}

		const parser = new DOMParser();
		const xmlDoc = parser.parseFromString(bpmnData.bpmnContent, "text/xml");

		// 构建 Task 执行顺序
		// 1. 收集所有 SequenceFlow
		const sequenceFlows: Array<{ sourceRef: string; targetRef: string }> = [];
		const allElements = xmlDoc.getElementsByTagName("*");

		for (let i = 0; i < allElements.length; i++) {
			const el = allElements[i];
			const tagName = el.tagName.toLowerCase();
			if (tagName.includes("sequenceflow")) {
				const sourceRef = el.getAttribute("sourceRef");
				const targetRef = el.getAttribute("targetRef");
				if (sourceRef && targetRef) {
					sequenceFlows.push({ sourceRef, targetRef });
				}
			}
		}

		console.log("SequenceFlows found:", sequenceFlows);

		// 2. 获取与此 DataObject 关联的 Task IDs
		const relatedTaskIds = info.tasks.map((t: any) => t.taskId);
		console.log("Related Task IDs:", relatedTaskIds);

		// 3. 构建 Task 之间的依赖关系图
		const taskOrder: Map<string, number> = new Map();
		const inDegree: Map<string, number> = new Map();
		const adjacencyList: Map<string, string[]> = new Map();

		// 初始化
		relatedTaskIds.forEach((taskId: string) => {
			inDegree.set(taskId, 0);
			adjacencyList.set(taskId, []);
		});

		// 构建图：只考虑相关 Task 之间的直接或间接连接
		sequenceFlows.forEach(({ sourceRef, targetRef }) => {
			if (relatedTaskIds.includes(sourceRef) && relatedTaskIds.includes(targetRef)) {
				adjacencyList.get(sourceRef)?.push(targetRef);
				inDegree.set(targetRef, (inDegree.get(targetRef) || 0) + 1);
			}
		});

		// 4. 拓扑排序确定执行顺序
		const sortedTasks: string[] = [];
		const queue: string[] = [];

		// 找到入度为 0 的节点
		relatedTaskIds.forEach((taskId: string) => {
			if (inDegree.get(taskId) === 0) {
				queue.push(taskId);
			}
		});

		while (queue.length > 0) {
			const current = queue.shift()!;
			sortedTasks.push(current);
			taskOrder.set(current, sortedTasks.length - 1);

			const neighbors = adjacencyList.get(current) || [];
			neighbors.forEach((neighbor) => {
				const newDegree = (inDegree.get(neighbor) || 1) - 1;
				inDegree.set(neighbor, newDegree);
				if (newDegree === 0) {
					queue.push(neighbor);
				}
			});
		}

		// 如果拓扑排序没有包含所有任务，说明可能存在环或者任务之间没有直接连接
		// 此时按照原始顺序补充
		relatedTaskIds.forEach((taskId: string) => {
			if (!sortedTasks.includes(taskId)) {
				sortedTasks.push(taskId);
				taskOrder.set(taskId, sortedTasks.length - 1);
			}
		});

		console.log("Sorted Task execution order:", sortedTasks);

		// 5. 按执行顺序排列 Task 信息
		const sortedTaskInfos = [...info.tasks].sort((a: any, b: any) => {
			const orderA = taskOrder.get(a.taskId) ?? Number.MAX_VALUE;
			const orderB = taskOrder.get(b.taskId) ?? Number.MAX_VALUE;
			return orderA - orderB;
		});

		console.log("Sorted Task infos:", sortedTaskInfos);

		// 6. 余额追踪验证
		// 使用 Map 记录每个参与者的余额，初始为 0
		const balances: Map<string, number> = new Map();
		const validationErrors: string[] = [];

		// 辅助函数：获取参与者余额（不存在则返回 0）
		const getBalance = (participant: string): number => {
			return balances.get(participant.trim()) || 0;
		};

		// 辅助函数：设置参与者余额
		const setBalance = (participant: string, amount: number) => {
			balances.set(participant.trim(), amount);
		};

		// 从 param 中获取所有参与者 ID，直接使用 ID 进行余额追踪
		// param 的 key 是参与者 ID（如 Participant_0bmf8tk），需要排除特殊 key
		const specialKeys = ["ERCChaincodeNames", "BpmnId"];
		const participantIds = Object.keys(param).filter(key => !specialKeys.includes(key));

		// 构建 name 到 ID 的映射（用于将 caller/callee 中的 name 转换为 ID）
		const participantElements = xmlDoc.querySelectorAll('participant, bpmn\\:participant, bpmn2\\:participant');
		const nameToIdMap: Map<string, string> = new Map();

		participantElements.forEach((participant: any) => {
			const id = (participant.getAttribute("id") || "").trim();
			const name = (participant.getAttribute("name") || "").trim();
			if (id && name) {
				nameToIdMap.set(name, id);
			}
		});

		// 1. 获取与此 DataObject 关联的 ERC 合约名
		// 从 info.tasks 中获取任意一个 taskId，然后从 param.ERCChaincodeNames 中获取合约名
		let ercContractName = "";
		const ercChaincodeNames = param?.ERCChaincodeNames || {};
		for (const task of info.tasks) {
			if (task.taskId && ercChaincodeNames[task.taskId]) {
				ercContractName = ercChaincodeNames[task.taskId];
				console.log(`[validateTransferableFT] 从 Task ${task.taskId} 获取到 ERC 合约名: ${ercContractName}`);
				break;
			}
		}

		if (!ercContractName) {
			console.warn("[validateTransferableFT] 未找到与此 DataObject 关联的 ERC 合约名，将使用默认余额 0");
		}

		// 2. 使用 param 中的参与者 ID 列表初始化余额
		// 通过 participantInfoList 获取每个参与者的 base64 编码，调用 FTqueryBalanceOf 查询初始余额
		const allParticipants: string[] = [];

		// 构建 participantId 到 x509Encoded (base64 编码) 的映射
		const participantIdToX509Map: Map<string, string> = new Map();
		participantInfoList.forEach((pInfo) => {
			participantIdToX509Map.set(pInfo.participantId, pInfo.x509Encoded);
		});

		console.log("[validateTransferableFT] participantIdToX509Map:", Object.fromEntries(participantIdToX509Map));

		// 3. 为每个参与者查询初始余额
		for (const participantId of participantIds) {
			if (!allParticipants.includes(participantId)) {
				allParticipants.push(participantId);

				// 获取该参与者的 x509Encoded (base64 编码)
				const x509Encoded = participantIdToX509Map.get(participantId);

				if (ercContractName && x509Encoded) {
					// 调用 FTqueryBalanceOf 查询余额
					try {
						console.log(`[validateTransferableFT] 查询 ${participantId} 的初始余额...`);
						const result = await FTqueryBalanceOf(ercContractName, x509Encoded);
						// 解析返回结果，获取余额值
						// 假设返回格式为 { output: { balance: "100" } } 或类似结构
						let balance = 0;
						if (result?.output?.balance !== undefined) {
							balance = parseFloat(result.output.balance) || 0;
						} else if (result?.output !== undefined && typeof result.output === "string") {
							balance = parseFloat(result.output) || 0;
						} else if (typeof result === "number") {
							balance = result;
						}
						console.log(`[validateTransferableFT] ${participantId} 初始余额: ${balance}`);
						setBalance(participantId, balance);
					} catch (error) {
						// 查询失败，默认余额为 0
						console.warn(`[validateTransferableFT] 查询 ${participantId} 余额失败，使用默认值 0:`, error);
						setBalance(participantId, 0);
					}
				} else {
					// 没有合约名或 x509Encoded，默认余额为 0
					console.log(`[validateTransferableFT] ${participantId} 无法查询余额（缺少合约名或 x509），使用默认值 0`);
					setBalance(participantId, 0);
				}
			}
		}

		// 辅助函数：将参与者 name 转换为 ID（如果是 name 的话）
		const convertNameToId = (value: string): string => {
			if (!value) return value;
			// 如果 value 是一个 name（存在于 nameToIdMap 中），则转换为 ID
			const id = nameToIdMap.get(value);
			return id || value;
		};

		console.log("\n=== 开始余额追踪验证 (Transferable FT) ===");
		console.log(`Token Name: ${info.tokenName}`);
		console.log(`所有参与者: [${allParticipants.join(", ")}]`);
		console.log(`初始余额状态:`, Object.fromEntries(balances));

		for (const taskInfo of sortedTaskInfos) {
			const { taskId, operation, documentation } = taskInfo;

			// 解析 documentation 获取 caller, callee, tokenNumber
			let caller = "";
			let callee = "";
			let tokenNumber = 0;

			if (documentation) {
				try {
					const docObj = JSON.parse(documentation);
					console.log(`  Task ${taskId} documentation 完整内容:`, docObj);

					caller = (docObj.caller || docObj.from || docObj.sender || "").trim();

					// callee 可能是数组或字符串
					let calleeValue = docObj.callee || docObj.to || docObj.recipient || docObj.receiver || "";
					if (Array.isArray(calleeValue)) {
						callee = (calleeValue[0] || "").trim();
					} else {
						callee = (calleeValue || "").trim();
					}

					// 解析 tokenNumber
					const tokenNumStr = docObj.tokenNumber || "0";
					tokenNumber = parseFloat(tokenNumStr) || 0;
				} catch (e) {
					console.warn(`Failed to parse documentation for task ${taskId}:`, e);
				}
			}

			// 将 caller 和 callee 从 name 转换为 ID（如果是 name 的话）
			caller = convertNameToId(caller);
			callee = convertNameToId(callee);

			console.log(`\n处理 Task: ${taskId}`);
			console.log(`  操作: ${operation}`);
			console.log(`  caller: "${caller}"`);
			console.log(`  callee: "${callee}"`);
			console.log(`  tokenNumber: ${tokenNumber}`);
			console.log(`  当前余额状态:`, Object.fromEntries(balances));

			const operationLower = (operation || "").toLowerCase().trim();

			if (operationLower === "mint") {
				// mint 操作：给 callee（接收者）增加 tokenNumber 数量
				if (tokenNumber <= 0) {
					const error = `Task ${taskId}: mint 操作失败 - tokenNumber 必须为正数，当前值: ${tokenNumber}`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					const receiver = callee || caller;
					if (!receiver) {
						const error = `Task ${taskId}: mint 操作失败 - 未指定接收者 (callee)`;
						validationErrors.push(error);
						console.error(`  ✗ ${error}`);
					} else {
						const currentBalance = getBalance(receiver);
						const newBalance = currentBalance + tokenNumber;
						setBalance(receiver, newBalance);
						console.log(`  ✓ mint 成功，${receiver} 余额: ${currentBalance} + ${tokenNumber} = ${newBalance}`);
					}
				}
			} else if (operationLower === "transfer") {
				// Transfer 操作：从 caller 减少，给 callee 增加 tokenNumber 数量
				if (tokenNumber <= 0) {
					const error = `Task ${taskId}: Transfer 操作失败 - tokenNumber 必须为正数，当前值: ${tokenNumber}`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else if (!caller) {
					const error = `Task ${taskId}: Transfer 操作失败 - 未指定发送者 (caller)`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else if (!callee) {
					const error = `Task ${taskId}: Transfer 操作失败 - 未指定接收者 (callee)`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					const senderBalance = getBalance(caller);
					if (senderBalance < tokenNumber) {
						const error = `Task ${taskId}: Transfer 操作失败 - ${caller} 余额不足 (当前: ${senderBalance}, 需要: ${tokenNumber})`;
						validationErrors.push(error);
						console.error(`  ✗ ${error}`);
					} else {
						// 扣除发送者余额
						const newSenderBalance = senderBalance - tokenNumber;
						setBalance(caller, newSenderBalance);
						// 增加接收者余额
						const receiverBalance = getBalance(callee);
						const newReceiverBalance = receiverBalance + tokenNumber;
						setBalance(callee, newReceiverBalance);
						console.log(`  ✓ Transfer 成功`);
						console.log(`    ${caller}: ${senderBalance} - ${tokenNumber} = ${newSenderBalance}`);
						console.log(`    ${callee}: ${receiverBalance} + ${tokenNumber} = ${newReceiverBalance}`);
					}
				}
			} else if (operationLower === "burn") {
				// burn 操作：从 caller 减少 tokenNumber 数量
				if (tokenNumber <= 0) {
					const error = `Task ${taskId}: burn 操作失败 - tokenNumber 必须为正数，当前值: ${tokenNumber}`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else if (!caller) {
					const error = `Task ${taskId}: burn 操作失败 - 未指定销毁者 (caller)`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					const burnerBalance = getBalance(caller);
					if (burnerBalance < tokenNumber) {
						const error = `Task ${taskId}: burn 操作失败 - ${caller} 余额不足 (当前: ${burnerBalance}, 需要: ${tokenNumber})`;
						validationErrors.push(error);
						console.error(`  ✗ ${error}`);
					} else {
						const newBalance = burnerBalance - tokenNumber;
						setBalance(caller, newBalance);
						console.log(`  ✓ burn 成功，${caller} 余额: ${burnerBalance} - ${tokenNumber} = ${newBalance}`);
					}
				}
			} else if (operationLower === "query") {
				// query 操作：不影响余额
				console.log(`  ✓ query 操作，不影响余额`);
			} else {
				console.warn(`  ? 未知操作类型: ${operation}`);
			}
		}

		console.log("\n=== 余额追踪验证完成 (Transferable FT) ===");
		console.log("最终余额状态:", Object.fromEntries(balances));

		// 7. 返回验证结果
		if (validationErrors.length > 0) {
			console.error("\n验证失败，发现以下错误:");
			validationErrors.forEach((err, idx) => {
				console.error(`  ${idx + 1}. ${err}`);
			});
		} else {
			console.log("\n✓ 验证通过：所有操作的余额变更逻辑正确");
		}

		// 构建最终余额信息字符串
		const finalBalanceInfo = Array.from(balances.entries())
			.map(([participant, balance]) => `${participant}: ${balance}`)
			.join(", ");

		return {
			dataObjectId: info.dataObjectId,
			assetType: info.assetType,
			tokenType: info.tokenType,
			success: validationErrors.length === 0,
			errors: validationErrors,
			finalOwner: finalBalanceInfo || "无余额记录",
		};
	};

	/**
	 * 分支 2: Transferable NFT 验证逻辑
	 */
	const validateTransferableNFT = async (info: any): Promise<ValidationResult> => {
		console.log("Validating Transferable NFT");
		// 可用操作: mint, burn, Transfer, query
		// 特点: 需要 tokenId, 不需要 tokenNumber

		const tokenHasExistInERC = info.tokenHasExistInERC || false;

		// 获取 BPMN XML 用于解析 SequenceFlow
		const bpmnData = await retrieveBPMN(bpmnId, consortiumId);
		if (!bpmnData || !bpmnData.bpmnContent) {
			console.error("Failed to retrieve BPMN data for task ordering");
			return {
				dataObjectId: info.dataObjectId,
				assetType: info.assetType,
				tokenType: info.tokenType,
				success: false,
				errors: ["无法获取 BPMN 数据"],
			};
		}

		const parser = new DOMParser();
		const xmlDoc = parser.parseFromString(bpmnData.bpmnContent, "text/xml");

		// 初始化所有者变量
		let currentOwner: string = "none";

		// 根据 tokenHasExistInERC 决定初始所有者
		if (tokenHasExistInERC) {
			console.log("Sub-branch: Token already exists in ERC contract");
			// 子分支 2.1: Token 已存在于 ERC 合约中
			// 需要查询区块链获取当前所有者

			// 1. 获取 tokenId
			const tokenId = info.tokenId;
			if (!tokenId) {
				console.warn("[validateTransferableNFT] tokenHasExistInERC=true 但未找到 tokenId，将使用默认所有者 none");
			} else {
				// 2. 获取 ERC 合约名（参考 FT 的获取逻辑）
				let ercContractName = "";
				const ercChaincodeNames = param?.ERCChaincodeNames || {};
				for (const task of info.tasks) {
					if (task.taskId && ercChaincodeNames[task.taskId]) {
						ercContractName = ercChaincodeNames[task.taskId];
						console.log(`[validateTransferableNFT] 从 Task ${task.taskId} 获取到 ERC 合约名: ${ercContractName}`);
						break;
					}
				}

				if (!ercContractName) {
					console.warn("[validateTransferableNFT] 未找到与此 DataObject 关联的 ERC 合约名，将使用默认所有者 none");
				} else {
					// 3. 调用 NFTqueryOwnerOf 查询当前所有者
					try {
						console.log(`[validateTransferableNFT] 查询 NFT (tokenId: ${tokenId}) 的当前所有者...`);
						const result = await NFTqueryOwnerOf(ercContractName, tokenId);

						// 解析返回结果，获取所有者信息
						// 打印完整的返回结果以便调试
						console.log(`[validateTransferableNFT] NFTqueryOwnerOf 返回结果:`, result);
						console.log(`[validateTransferableNFT] 返回结果类型:`, typeof result);

						let ownerX509 = "";

						// 尝试多种可能的返回格式
						if (typeof result === "string") {
							// 直接返回字符串
							ownerX509 = result;
						} else if (result?.output !== undefined) {
							if (typeof result.output === "string") {
								// { output: "x509::..." }
								ownerX509 = result.output;
							} else if (result.output?.owner) {
								// { output: { owner: "x509::..." } }
								ownerX509 = result.output.owner;
							} else if (result.output?.value) {
								// { output: { value: "x509::..." } }
								ownerX509 = result.output.value;
							}
						} else if (result?.owner) {
							// { owner: "x509::..." }
							ownerX509 = result.owner;
						} else if (result?.value) {
							// { value: "x509::..." }
							ownerX509 = result.value;
						} else if (result?.data) {
							// { data: "x509::..." }
							if (typeof result.data === "string") {
								ownerX509 = result.data;
							} else if (result.data?.output) {
								ownerX509 = typeof result.data.output === "string" ? result.data.output : "";
							}
						}

						console.log(`[validateTransferableNFT] 解析后的所有者 x509: ${ownerX509}`);

						if (ownerX509) {
							// 4. 将 x509 结果与 participantInfoList 中的 x509Decoded 进行匹配
							let matchedParticipantId: string | null = null;
							for (const pInfo of participantInfoList) {
								// 比较 x509Decoded 是否与查询结果匹配
								// 查询结果可能是完整的 x509 字符串，需要进行包含匹配
								if (ownerX509.includes(pInfo.x509Decoded) || pInfo.x509Decoded.includes(ownerX509)) {
									matchedParticipantId = pInfo.participantId;
									console.log(`[validateTransferableNFT] 匹配成功: ${ownerX509} -> ${pInfo.participantId}`);
									break;
								}
							}

							if (matchedParticipantId) {
								currentOwner = matchedParticipantId;
								console.log(`[validateTransferableNFT] 初始所有者设置为: ${currentOwner}`);
							} else {
								console.warn(`[validateTransferableNFT] 未找到匹配的参与者，所有者设置为 none`);
								currentOwner = "none";
							}
						} else {
							console.warn(`[validateTransferableNFT] 查询结果为空，所有者设置为 none`);
							currentOwner = "none";
						}
					} catch (error) {
						console.warn(`[validateTransferableNFT] 查询 NFT 所有者失败，使用默认所有者 none:`, error);
						currentOwner = "none";
					}
				}
			}
		} else {
			console.log("Sub-branch: Token needs to be minted");
			// 子分支 2.2: Token 需要被铸造
			// 初始所有者为 "none"
			currentOwner = "none";
		}

		// ========== 以下是共用的验证逻辑 ==========

		// 构建 Task 执行顺序
		// 1. 收集所有 SequenceFlow
		const sequenceFlows: Array<{ sourceRef: string; targetRef: string }> = [];
		const allElements = xmlDoc.getElementsByTagName("*");

		for (let i = 0; i < allElements.length; i++) {
			const el = allElements[i];
			const tagName = el.tagName.toLowerCase();
			if (tagName.includes("sequenceflow")) {
				const sourceRef = el.getAttribute("sourceRef");
				const targetRef = el.getAttribute("targetRef");
				if (sourceRef && targetRef) {
					sequenceFlows.push({ sourceRef, targetRef });
				}
			}
		}

		console.log("SequenceFlows found:", sequenceFlows);

		// 2. 获取与此 DataObject 关联的 Task IDs
		const relatedTaskIds = info.tasks.map((t: any) => t.taskId);
		console.log("Related Task IDs:", relatedTaskIds);

		// 3. 构建 Task 之间的依赖关系图
		const taskOrder: Map<string, number> = new Map();
		const inDegree: Map<string, number> = new Map();
		const adjacencyList: Map<string, string[]> = new Map();

		// 初始化
		relatedTaskIds.forEach((taskId: string) => {
			inDegree.set(taskId, 0);
			adjacencyList.set(taskId, []);
		});

		// 构建图：只考虑相关 Task 之间的直接或间接连接
		sequenceFlows.forEach(({ sourceRef, targetRef }) => {
			if (relatedTaskIds.includes(sourceRef) && relatedTaskIds.includes(targetRef)) {
				adjacencyList.get(sourceRef)?.push(targetRef);
				inDegree.set(targetRef, (inDegree.get(targetRef) || 0) + 1);
			}
		});

		// 4. 拓扑排序确定执行顺序
		const sortedTasks: string[] = [];
		const queue: string[] = [];

		// 找到入度为 0 的节点
		relatedTaskIds.forEach((taskId: string) => {
			if (inDegree.get(taskId) === 0) {
				queue.push(taskId);
			}
		});

		while (queue.length > 0) {
			const current = queue.shift()!;
			sortedTasks.push(current);
			taskOrder.set(current, sortedTasks.length - 1);

			const neighbors = adjacencyList.get(current) || [];
			neighbors.forEach((neighbor) => {
				const newDegree = (inDegree.get(neighbor) || 1) - 1;
				inDegree.set(neighbor, newDegree);
				if (newDegree === 0) {
					queue.push(neighbor);
				}
			});
		}

		// 如果拓扑排序没有包含所有任务，说明可能存在环或者任务之间没有直接连接
		// 此时按照原始顺序补充
		relatedTaskIds.forEach((taskId: string) => {
			if (!sortedTasks.includes(taskId)) {
				sortedTasks.push(taskId);
				taskOrder.set(taskId, sortedTasks.length - 1);
			}
		});

		console.log("Sorted Task execution order:", sortedTasks);

		// 5. 按执行顺序排列 Task 信息
		const sortedTaskInfos = [...info.tasks].sort((a: any, b: any) => {
			const orderA = taskOrder.get(a.taskId) ?? Number.MAX_VALUE;
			const orderB = taskOrder.get(b.taskId) ?? Number.MAX_VALUE;
			return orderA - orderB;
		});

		console.log("Sorted Task infos:", sortedTaskInfos);

		// 6. 所有权追踪验证
		const validationErrors: string[] = [];

		console.log("\n=== 开始所有权追踪验证 ===");
		console.log(`初始所有者: ${currentOwner}`);

		for (const taskInfo of sortedTaskInfos) {
			const { taskId, operation, documentation } = taskInfo;

			// 解析 documentation 获取 caller 和 callee
			let caller = "";
			let callee = "";

			if (documentation) {
				try {
					const docObj = JSON.parse(documentation);
					// 打印完整的 docObj 以便调试
					console.log(`  Task ${taskId} documentation 完整内容:`, docObj);
					console.log(`  docObj 的所有字段:`, Object.keys(docObj));

					// 使用 trim() 去除可能的空白字符
					// 尝试多种可能的字段名
					caller = (docObj.caller || docObj.from || docObj.sender || "").trim();

					// callee 可能是数组或字符串，需要处理两种情况
					let calleeValue = docObj.callee || docObj.to || docObj.recipient || docObj.receiver || "";
					if (Array.isArray(calleeValue)) {
						// 如果是数组，取第一个元素
						callee = (calleeValue[0] || "").trim();
					} else {
						callee = (calleeValue || "").trim();
					}
				} catch (e) {
					console.warn(`Failed to parse documentation for task ${taskId}:`, e);
				}
			}

			// 确保 currentOwner 也是干净的字符串
			currentOwner = currentOwner.trim();

			console.log(`\n处理 Task: ${taskId}`);
			console.log(`  操作: ${operation}`);
			console.log(`  caller: "${caller}" (length: ${caller.length})`);
			console.log(`  callee: "${callee}" (length: ${callee.length})`);
			console.log(`  当前所有者: "${currentOwner}" (length: ${currentOwner.length})`);

			const operationLower = (operation || "").toLowerCase().trim();

			if (operationLower === "mint") {
				// mint 操作：只有当所有者为 none 时才能执行
				if (currentOwner !== "none") {
					const error = `Task ${taskId}: mint 操作失败 - token 已存在，当前所有者为 ${currentOwner}`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					// mint 成功，所有者变为 callee（接收者）
					currentOwner = (callee || caller || "unknown").trim();
					console.log(`  ✓ mint 成功，所有者变更为: ${currentOwner}`);
				}
			} else if (operationLower === "transfer") {
				// transfer 操作：先验证 caller 是当前所有者，再更改为 callee
				if (currentOwner === "none") {
					const error = `Task ${taskId}: transfer 操作失败 - token 尚未被铸造`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else if (caller && caller !== currentOwner) {
					const error = `Task ${taskId}: transfer 操作失败 - caller(${caller}) 不是当前所有者(${currentOwner})`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					// transfer 成功，所有者变为 callee
					const previousOwner = currentOwner;
					currentOwner = (callee || "unknown").trim();
					console.log(`  ✓ transfer 成功，所有者从 ${previousOwner} 变更为: ${currentOwner}`);
				}
			} else if (operationLower === "burn") {
				// burn 操作：先验证 caller 是当前所有者，然后所有者变为 none
				if (currentOwner === "none") {
					const error = `Task ${taskId}: burn 操作失败 - token 尚未被铸造或已被销毁`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else if (caller && caller !== currentOwner) {
					const error = `Task ${taskId}: burn 操作失败 - caller(${caller}) 不是当前所有者(${currentOwner})`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					// burn 成功，所有者变为 none
					console.log(`  ✓ burn 成功，所有者从 ${currentOwner} 变更为: none`);
					currentOwner = "none";
				}
			} else if (operationLower === "query") {
				// query 操作：不影响所有权
				console.log(`  ✓ query 操作，不影响所有权`);
			} else {
				console.warn(`  ? 未知操作类型: ${operation}`);
			}
		}

		console.log("\n=== 所有权追踪验证完成 ===");
		console.log(`最终所有者: ${currentOwner}`);

		// 7. 返回验证结果
		if (validationErrors.length > 0) {
			console.error("\n验证失败，发现以下错误:");
			validationErrors.forEach((err, idx) => {
				console.error(`  ${idx + 1}. ${err}`);
			});
		} else {
			console.log("\n✓ 验证通过：所有操作的所有权转移逻辑正确");
		}

		return {
			dataObjectId: info.dataObjectId,
			assetType: info.assetType,
			tokenType: info.tokenType,
			success: validationErrors.length === 0,
			errors: validationErrors,
			finalOwner: currentOwner,
		};
	};

	/**
	 * 分支 3: Value-added NFT 验证逻辑
	 */
	const validateValueAddedNFT = async (info: any): Promise<ValidationResult> => {
		console.log("Validating Value-added NFT");
		// 可用操作: branch, merge, Transfer, query
		// 特点: 需要 tokenId, refTokenIds (merge 必须非空)

		const tokenHasExistInERC = info.tokenHasExistInERC || false;

		// 获取 BPMN XML 用于解析 SequenceFlow
		const bpmnData = await retrieveBPMN(bpmnId, consortiumId);
		if (!bpmnData || !bpmnData.bpmnContent) {
			console.error("Failed to retrieve BPMN data for task ordering");
			return {
				dataObjectId: info.dataObjectId,
				assetType: info.assetType,
				tokenType: info.tokenType,
				success: false,
				errors: ["无法获取 BPMN 数据"],
			};
		}

		const parser = new DOMParser();
		const xmlDoc = parser.parseFromString(bpmnData.bpmnContent, "text/xml");

		// 初始化所有者变量
		let currentOwner: string = "none";

		// 根据 tokenHasExistInERC 决定初始所有者
		if (tokenHasExistInERC) {
			console.log("Sub-branch: Token already exists in ERC contract");
			// 子分支 3.1: Token 已存在于 ERC 合约中
			// 需要查询区块链获取当前所有者

			// 1. 获取 tokenId
			const tokenId = info.tokenId;
			if (!tokenId) {
				console.warn("[validateValueAddedNFT] tokenHasExistInERC=true 但未找到 tokenId，将使用默认所有者 none");
			} else {
				// 2. 获取 ERC 合约名（参考 FT 的获取逻辑）
				let ercContractName = "";
				const ercChaincodeNames = param?.ERCChaincodeNames || {};
				for (const task of info.tasks) {
					if (task.taskId && ercChaincodeNames[task.taskId]) {
						ercContractName = ercChaincodeNames[task.taskId];
						console.log(`[validateValueAddedNFT] 从 Task ${task.taskId} 获取到 ERC 合约名: ${ercContractName}`);
						break;
					}
				}

				if (!ercContractName) {
					console.warn("[validateValueAddedNFT] 未找到与此 DataObject 关联的 ERC 合约名，将使用默认所有者 none");
				} else {
					// 3. 调用 NFTqueryOwnerOf 查询当前所有者
					try {
						console.log(`[validateValueAddedNFT] 查询 NFT (tokenId: ${tokenId}) 的当前所有者...`);
						const result = await NFTqueryOwnerOf(ercContractName, tokenId);

						// 解析返回结果，获取所有者信息
						console.log(`[validateValueAddedNFT] NFTqueryOwnerOf 返回结果:`, result);
						console.log(`[validateValueAddedNFT] 返回结果类型:`, typeof result);

						let ownerX509 = "";

						// 尝试多种可能的返回格式
						if (typeof result === "string") {
							ownerX509 = result;
						} else if (result?.output !== undefined) {
							if (typeof result.output === "string") {
								ownerX509 = result.output;
							} else if (result.output?.owner) {
								ownerX509 = result.output.owner;
							} else if (result.output?.value) {
								ownerX509 = result.output.value;
							}
						} else if (result?.owner) {
							ownerX509 = result.owner;
						} else if (result?.value) {
							ownerX509 = result.value;
						} else if (result?.data) {
							if (typeof result.data === "string") {
								ownerX509 = result.data;
							} else if (result.data?.output) {
								ownerX509 = typeof result.data.output === "string" ? result.data.output : "";
							}
						}

						console.log(`[validateValueAddedNFT] 解析后的所有者 x509: ${ownerX509}`);

						if (ownerX509) {
							// 4. 将 x509 结果与 participantInfoList 中的 x509Decoded 进行匹配
							let matchedParticipantId: string | null = null;
							for (const pInfo of participantInfoList) {
								if (ownerX509.includes(pInfo.x509Decoded) || pInfo.x509Decoded.includes(ownerX509)) {
									matchedParticipantId = pInfo.participantId;
									console.log(`[validateValueAddedNFT] 匹配成功: ${ownerX509} -> ${pInfo.participantId}`);
									break;
								}
							}

							if (matchedParticipantId) {
								currentOwner = matchedParticipantId;
								console.log(`[validateValueAddedNFT] 初始所有者设置为: ${currentOwner}`);
							} else {
								console.warn(`[validateValueAddedNFT] 未找到匹配的参与者，所有者设置为 none`);
								currentOwner = "none";
							}
						} else {
							console.warn(`[validateValueAddedNFT] 查询结果为空，所有者设置为 none`);
							currentOwner = "none";
						}
					} catch (error) {
						console.warn(`[validateValueAddedNFT] 查询 NFT 所有者失败，使用默认所有者 none:`, error);
						currentOwner = "none";
					}
				}
			}
		} else {
			console.log("Sub-branch: Token needs to be created via branch/merge");
			// 子分支 3.2: Token 需要通过 branch/merge 创建
			// 初始所有者为 "none"
			currentOwner = "none";
		}

		// ========== 以下是共用的验证逻辑 ==========

		// 构建 Task 执行顺序
		// 1. 收集所有 SequenceFlow
		const sequenceFlows: Array<{ sourceRef: string; targetRef: string }> = [];
		const allElements = xmlDoc.getElementsByTagName("*");

		for (let i = 0; i < allElements.length; i++) {
			const el = allElements[i];
			const tagName = el.tagName.toLowerCase();
			if (tagName.includes("sequenceflow")) {
				const sourceRef = el.getAttribute("sourceRef");
				const targetRef = el.getAttribute("targetRef");
				if (sourceRef && targetRef) {
					sequenceFlows.push({ sourceRef, targetRef });
				}
			}
		}

		console.log("SequenceFlows found:", sequenceFlows);

		// 2. 获取与此 DataObject 关联的 Task IDs
		const relatedTaskIds = info.tasks.map((t: any) => t.taskId);
		console.log("Related Task IDs:", relatedTaskIds);

		// 3. 构建 Task 之间的依赖关系图
		const taskOrder: Map<string, number> = new Map();
		const inDegree: Map<string, number> = new Map();
		const adjacencyList: Map<string, string[]> = new Map();

		// 初始化
		relatedTaskIds.forEach((taskId: string) => {
			inDegree.set(taskId, 0);
			adjacencyList.set(taskId, []);
		});

		// 构建图：只考虑相关 Task 之间的直接或间接连接
		sequenceFlows.forEach(({ sourceRef, targetRef }) => {
			if (relatedTaskIds.includes(sourceRef) && relatedTaskIds.includes(targetRef)) {
				adjacencyList.get(sourceRef)?.push(targetRef);
				inDegree.set(targetRef, (inDegree.get(targetRef) || 0) + 1);
			}
		});

		// 4. 拓扑排序确定执行顺序
		const sortedTasks: string[] = [];
		const queue: string[] = [];

		// 找到入度为 0 的节点
		relatedTaskIds.forEach((taskId: string) => {
			if (inDegree.get(taskId) === 0) {
				queue.push(taskId);
			}
		});

		while (queue.length > 0) {
			const current = queue.shift()!;
			sortedTasks.push(current);
			taskOrder.set(current, sortedTasks.length - 1);

			const neighbors = adjacencyList.get(current) || [];
			neighbors.forEach((neighbor) => {
				const newDegree = (inDegree.get(neighbor) || 1) - 1;
				inDegree.set(neighbor, newDegree);
				if (newDegree === 0) {
					queue.push(neighbor);
				}
			});
		}

		// 如果拓扑排序没有包含所有任务，说明可能存在环或者任务之间没有直接连接
		// 此时按照原始顺序补充
		relatedTaskIds.forEach((taskId: string) => {
			if (!sortedTasks.includes(taskId)) {
				sortedTasks.push(taskId);
				taskOrder.set(taskId, sortedTasks.length - 1);
			}
		});

		console.log("Sorted Task execution order:", sortedTasks);

		// 5. 按执行顺序排列 Task 信息
		const sortedTaskInfos = [...info.tasks].sort((a: any, b: any) => {
			const orderA = taskOrder.get(a.taskId) ?? Number.MAX_VALUE;
			const orderB = taskOrder.get(b.taskId) ?? Number.MAX_VALUE;
			return orderA - orderB;
		});

		console.log("Sorted Task infos:", sortedTaskInfos);

		// 6. 所有权追踪验证
		const validationErrors: string[] = [];

		console.log("\n=== 开始所有权追踪验证 (Value-added NFT) ===");
		console.log(`初始所有者: ${currentOwner}`);

		for (const taskInfo of sortedTaskInfos) {
			const { taskId, operation, documentation, isInput } = taskInfo;

			// 解析 documentation 获取 caller 和 callee
			let caller = "";
			let callee = "";

			if (documentation) {
				try {
					const docObj = JSON.parse(documentation);
					// 打印完整的 docObj 以便调试
					console.log(`  Task ${taskId} documentation 完整内容:`, docObj);
					console.log(`  docObj 的所有字段:`, Object.keys(docObj));

					// 使用 trim() 去除可能的空白字符
					caller = (docObj.caller || docObj.from || docObj.sender || "").trim();

					// callee 可能是数组或字符串，需要处理两种情况
					let calleeValue = docObj.callee || docObj.to || docObj.recipient || docObj.receiver || "";
					if (Array.isArray(calleeValue)) {
						// 如果是数组，取第一个元素
						callee = (calleeValue[0] || "").trim();
					} else {
						callee = (calleeValue || "").trim();
					}
				} catch (e) {
					console.warn(`Failed to parse documentation for task ${taskId}:`, e);
				}
			}

			// 确保 currentOwner 也是干净的字符串
			currentOwner = currentOwner.trim();

			console.log(`\n处理 Task: ${taskId}`);
			console.log(`  操作: ${operation}`);
			console.log(`  caller: "${caller}" (length: ${caller.length})`);
			console.log(`  callee: "${callee}" (length: ${callee.length})`);
			console.log(`  当前所有者: "${currentOwner}" (length: ${currentOwner.length})`);
			console.log(`  isInput (Task→DataObject): ${isInput}`);

			const operationLower = (operation || "").toLowerCase().trim();

			if (operationLower === "branch" || operationLower === "merge") {
				// branch/merge 操作：
				// - 只有 Task → DataObject (isInput: true) 才能真正改变所有权
				// - DataObject → Task (isInput: false) 只是引用，不改变所有权（类似 query）
				if (!isInput) {
					// DataObject → Task：只是引用输入，不改变所有权
					console.log(`  ✓ ${operation} 操作（作为输入引用），不影响所有权`);
				} else {
					// Task → DataObject：创建新 token，改变所有权
					if (currentOwner !== "none") {
						const error = `Task ${taskId}: ${operation} 操作失败 - token 已存在，当前所有者为 ${currentOwner}`;
						validationErrors.push(error);
						console.error(`  ✗ ${error}`);
					} else {
						// branch/merge 成功，所有者变为 caller（Brancher/Merger）
						currentOwner = (caller || "unknown").trim();
						console.log(`  ✓ ${operation} 成功，所有者变更为: ${currentOwner}`);
					}
				}
			} else if (operationLower === "transfer") {
				// transfer 操作：先验证 caller 是当前所有者，再更改为 callee
				if (currentOwner === "none") {
					const error = `Task ${taskId}: transfer 操作失败 - token 尚未被铸造`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else if (caller && caller !== currentOwner) {
					const error = `Task ${taskId}: transfer 操作失败 - caller(${caller}) 不是当前所有者(${currentOwner})`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					// transfer 成功，所有者变为 callee
					const previousOwner = currentOwner;
					currentOwner = (callee || "unknown").trim();
					console.log(`  ✓ transfer 成功，所有者从 ${previousOwner} 变更为: ${currentOwner}`);
				}
			} else if (operationLower === "burn") {
				// burn 操作：先验证 caller 是当前所有者，然后所有者变为 none
				if (currentOwner === "none") {
					const error = `Task ${taskId}: burn 操作失败 - token 尚未被铸造或已被销毁`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else if (caller && caller !== currentOwner) {
					const error = `Task ${taskId}: burn 操作失败 - caller(${caller}) 不是当前所有者(${currentOwner})`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					// burn 成功，所有者变为 none
					console.log(`  ✓ burn 成功，所有者从 ${currentOwner} 变更为: none`);
					currentOwner = "none";
				}
			} else if (operationLower === "query") {
				// query 操作：不影响所有权
				console.log(`  ✓ query 操作，不影响所有权`);
			} else {
				console.warn(`  ? 未知操作类型: ${operation}`);
			}
		}

		console.log("\n=== 所有权追踪验证完成 (Value-added NFT) ===");
		console.log(`最终所有者: ${currentOwner}`);

		// 7. 返回验证结果
		if (validationErrors.length > 0) {
			console.error("\n验证失败，发现以下错误:");
			validationErrors.forEach((err, idx) => {
				console.error(`  ${idx + 1}. ${err}`);
			});
		} else {
			console.log("\n✓ 验证通过：所有操作的所有权转移逻辑正确");
		}

		return {
			dataObjectId: info.dataObjectId,
			assetType: info.assetType,
			tokenType: info.tokenType,
			success: validationErrors.length === 0,
			errors: validationErrors,
			finalOwner: currentOwner,
		};
	};

	/**
	 * 分支 4: Distributive NFT 验证逻辑
	 */
	const validateDistributiveNFT = async (info: any): Promise<ValidationResult> => {
		console.log("Validating Distributive NFT");
		// 可用操作: mint, burn, grant usage rights, revoke usage rights, transfer, query
		// 特点: burn 需要 tokenId

		const tokenHasExistInERC = info.tokenHasExistInERC || false;

		// 获取 BPMN XML 用于解析 SequenceFlow
		const bpmnData = await retrieveBPMN(bpmnId, consortiumId);
		if (!bpmnData || !bpmnData.bpmnContent) {
			console.error("Failed to retrieve BPMN data for task ordering");
			return {
				dataObjectId: info.dataObjectId,
				assetType: info.assetType,
				tokenType: info.tokenType,
				success: false,
				errors: ["无法获取 BPMN 数据"],
			};
		}

		const parser = new DOMParser();
		const xmlDoc = parser.parseFromString(bpmnData.bpmnContent, "text/xml");

		// 初始化所有者变量
		let currentOwner: string = "none";

		// 根据 tokenHasExistInERC 决定初始所有者
		if (tokenHasExistInERC) {
			console.log("Sub-branch: Token already exists in ERC contract");
			// 子分支 4.1: Token 已存在于 ERC 合约中
			// 需要查询区块链获取当前所有者

			// 1. 获取 tokenId 并拼接 "_owner"
			const baseTokenId = info.tokenId;
			if (!baseTokenId) {
				console.warn("[validateDistributiveNFT] tokenHasExistInERC=true 但未找到 tokenId，将使用默认所有者 none");
			} else {
				const tokenIdWithOwner = `${baseTokenId}_owner`;
				console.log(`[validateDistributiveNFT] 使用 tokenId: ${tokenIdWithOwner}`);

				// 2. 获取 ERC 合约名（参考 FT 的获取逻辑）
				let ercContractName = "";
				const ercChaincodeNames = param?.ERCChaincodeNames || {};
				for (const task of info.tasks) {
					if (task.taskId && ercChaincodeNames[task.taskId]) {
						ercContractName = ercChaincodeNames[task.taskId];
						console.log(`[validateDistributiveNFT] 从 Task ${task.taskId} 获取到 ERC 合约名: ${ercContractName}`);
						break;
					}
				}

				if (!ercContractName) {
					console.warn("[validateDistributiveNFT] 未找到与此 DataObject 关联的 ERC 合约名，将使用默认所有者 none");
				} else {
					// 3. 遍历所有参与者，调用 DisNFTquery 查询余额
					// 如果返回 1，则该参与者是所有者
					console.log(`[validateDistributiveNFT] 开始遍历参与者查询所有者...`);

					for (const pInfo of participantInfoList) {
						try {
							console.log(`[validateDistributiveNFT] 查询参与者 ${pInfo.participantId} 的余额...`);
							console.log(`[validateDistributiveNFT] account (x509Encoded): ${pInfo.x509Encoded.substring(0, 50)}...`);

							const result = await DisNFTquery(ercContractName, tokenIdWithOwner, pInfo.x509Encoded);

							// 解析返回结果
							console.log(`[validateDistributiveNFT] DisNFTquery 返回结果:`, result);
							console.log(`[validateDistributiveNFT] 返回结果类型:`, typeof result);

							let balance = 0;

							// 尝试多种可能的返回格式
							if (typeof result === "number") {
								balance = result;
							} else if (typeof result === "string") {
								balance = parseInt(result, 10) || 0;
							} else if (result?.output !== undefined) {
								if (typeof result.output === "number") {
									balance = result.output;
								} else if (typeof result.output === "string") {
									balance = parseInt(result.output, 10) || 0;
								} else if (result.output?.balance !== undefined) {
									balance = parseInt(result.output.balance, 10) || 0;
								}
							} else if (result?.balance !== undefined) {
								balance = parseInt(result.balance, 10) || 0;
							} else if (result?.value !== undefined) {
								balance = parseInt(result.value, 10) || 0;
							}

							console.log(`[validateDistributiveNFT] 解析后的余额: ${balance}`);

							if (balance === 1) {
								currentOwner = pInfo.participantId;
								console.log(`[validateDistributiveNFT] 找到所有者: ${currentOwner}`);
								break;
							}
						} catch (error) {
							console.warn(`[validateDistributiveNFT] 查询参与者 ${pInfo.participantId} 余额失败:`, error);
							// 继续查询下一个参与者
						}
					}

					if (currentOwner === "none") {
						console.warn(`[validateDistributiveNFT] 未找到任何参与者拥有该 token，所有者设置为 none`);
					} else {
						console.log(`[validateDistributiveNFT] 初始所有者设置为: ${currentOwner}`);
					}
				}
			}
		} else {
			console.log("Sub-branch: Token needs to be minted");
			// 子分支 4.2: Token 需要被铸造
			// 初始所有者为 "none"
			currentOwner = "none";
		}

		// ========== 以下是共用的验证逻辑 ==========

		// 构建 Task 执行顺序
		// 1. 收集所有 SequenceFlow
		const sequenceFlows: Array<{ sourceRef: string; targetRef: string }> = [];
		const allElements = xmlDoc.getElementsByTagName("*");

			for (let i = 0; i < allElements.length; i++) {
				const el = allElements[i];
				const tagName = el.tagName.toLowerCase();
				if (tagName.includes("sequenceflow")) {
					const sourceRef = el.getAttribute("sourceRef");
					const targetRef = el.getAttribute("targetRef");
					if (sourceRef && targetRef) {
						sequenceFlows.push({ sourceRef, targetRef });
					}
				}
			}

			console.log("SequenceFlows found:", sequenceFlows);

			// 2. 获取与此 DataObject 关联的 Task IDs
			const relatedTaskIds = info.tasks.map((t: any) => t.taskId);
			console.log("Related Task IDs:", relatedTaskIds);

			// 3. 构建 Task 之间的依赖关系图
			const taskOrder: Map<string, number> = new Map();
			const inDegree: Map<string, number> = new Map();
			const adjacencyList: Map<string, string[]> = new Map();

			// 初始化
			relatedTaskIds.forEach((taskId: string) => {
				inDegree.set(taskId, 0);
				adjacencyList.set(taskId, []);
			});

			// 构建图：只考虑相关 Task 之间的直接或间接连接
			sequenceFlows.forEach(({ sourceRef, targetRef }) => {
				if (relatedTaskIds.includes(sourceRef) && relatedTaskIds.includes(targetRef)) {
					adjacencyList.get(sourceRef)?.push(targetRef);
					inDegree.set(targetRef, (inDegree.get(targetRef) || 0) + 1);
				}
			});

			// 4. 拓扑排序确定执行顺序
			const sortedTasks: string[] = [];
			const queue: string[] = [];

			// 找到入度为 0 的节点
			relatedTaskIds.forEach((taskId: string) => {
				if (inDegree.get(taskId) === 0) {
					queue.push(taskId);
				}
			});

			while (queue.length > 0) {
				const current = queue.shift()!;
				sortedTasks.push(current);
				taskOrder.set(current, sortedTasks.length - 1);

				const neighbors = adjacencyList.get(current) || [];
				neighbors.forEach((neighbor) => {
					const newDegree = (inDegree.get(neighbor) || 1) - 1;
					inDegree.set(neighbor, newDegree);
					if (newDegree === 0) {
						queue.push(neighbor);
					}
				});
			}

			// 如果拓扑排序没有包含所有任务，说明可能存在环或者任务之间没有直接连接
			// 此时按照原始顺序补充
			relatedTaskIds.forEach((taskId: string) => {
				if (!sortedTasks.includes(taskId)) {
					sortedTasks.push(taskId);
					taskOrder.set(taskId, sortedTasks.length - 1);
				}
			});

			console.log("Sorted Task execution order:", sortedTasks);

			// 5. 按执行顺序排列 Task 信息
			const sortedTaskInfos = [...info.tasks].sort((a: any, b: any) => {
				const orderA = taskOrder.get(a.taskId) ?? Number.MAX_VALUE;
				const orderB = taskOrder.get(b.taskId) ?? Number.MAX_VALUE;
				return orderA - orderB;
			});

		console.log("Sorted Task infos:", sortedTaskInfos);

		// 6. 所有权和使用权追踪验证
		// 使用权用数组记录，初始为空
		let usageRights: string[] = [];  // 记录有使用权的参与者
		const validationErrors: string[] = [];

		console.log("\n=== 开始所有权和使用权追踪验证 ===");
		console.log(`初始所有者: ${currentOwner}`);
		console.log(`初始使用权: [${usageRights.join(", ")}]`);

		for (const taskInfo of sortedTaskInfos) {
			const { taskId, operation, documentation } = taskInfo;

			// 解析 documentation 获取 caller 和 callee
			let caller = "";
			let callee = "";
			let calleeArray: string[] = [];

			if (documentation) {
				try {
					const docObj = JSON.parse(documentation);
					// 打印完整的 docObj 以便调试
					console.log(`  Task ${taskId} documentation 完整内容:`, docObj);
					console.log(`  docObj 的所有字段:`, Object.keys(docObj));

					// 使用 trim() 去除可能的空白字符
					caller = (docObj.caller || docObj.from || docObj.sender || "").trim();

					// callee 可能是数组或字符串，需要处理两种情况
					let calleeValue = docObj.callee || docObj.to || docObj.recipient || docObj.receiver || "";
					if (Array.isArray(calleeValue)) {
						// 保存完整的数组用于 grant/revoke 操作
						calleeArray = calleeValue.map((v: string) => (v || "").trim());
						// 取第一个元素作为单一 callee
						callee = (calleeValue[0] || "").trim();
					} else {
						callee = (calleeValue || "").trim();
						calleeArray = callee ? [callee] : [];
					}
				} catch (e) {
					console.warn(`Failed to parse documentation for task ${taskId}:`, e);
				}
			}

			// 确保 currentOwner 也是干净的字符串
			currentOwner = currentOwner.trim();

			console.log(`\n处理 Task: ${taskId}`);
			console.log(`  操作: ${operation}`);
			console.log(`  caller: "${caller}" (length: ${caller.length})`);
			console.log(`  callee: "${callee}" (length: ${callee.length})`);
			console.log(`  calleeArray: [${calleeArray.join(", ")}]`);
			console.log(`  当前所有者: "${currentOwner}" (length: ${currentOwner.length})`);
			console.log(`  当前使用权: [${usageRights.join(", ")}]`);

			const operationLower = (operation || "").toLowerCase().trim();

			if (operationLower === "mint") {
				// mint 操作：只有当所有者为 none 时才能执行
				if (currentOwner !== "none") {
					const error = `Task ${taskId}: mint 操作失败 - token 已存在，当前所有者为 ${currentOwner}`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					// mint 成功，所有者变为 callee（接收者）
					currentOwner = (callee || caller || "unknown").trim();
					console.log(`  ✓ mint 成功，所有者变更为: ${currentOwner}`);
				}
			} else if (operationLower === "transfer") {
				// transfer 操作：先验证 caller 是当前所有者，再更改为 callee
				if (currentOwner === "none") {
					const error = `Task ${taskId}: transfer 操作失败 - token 尚未被铸造`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else if (caller && caller !== currentOwner) {
					const error = `Task ${taskId}: transfer 操作失败 - caller(${caller}) 不是当前所有者(${currentOwner})`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					// transfer 成功，所有者变为 callee
					const previousOwner = currentOwner;
					currentOwner = (callee || "unknown").trim();
					console.log(`  ✓ transfer 成功，所有者从 ${previousOwner} 变更为: ${currentOwner}`);
				}
			} else if (operationLower === "burn") {
				// burn 操作：先验证 caller 是当前所有者，然后所有者变为 none
				if (currentOwner === "none") {
					const error = `Task ${taskId}: burn 操作失败 - token 尚未被铸造或已被销毁`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else if (caller && caller !== currentOwner) {
					const error = `Task ${taskId}: burn 操作失败 - caller(${caller}) 不是当前所有者(${currentOwner})`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					// burn 成功，所有者变为 none，同时清空使用权
					console.log(`  ✓ burn 成功，所有者从 ${currentOwner} 变更为: none，使用权清空`);
					currentOwner = "none";
					usageRights = [];
				}
			} else if (operationLower === "grant usage rights") {
				// grant usage rights 操作：caller 必须是所有者，将 callee 加入使用权数组
				if (currentOwner === "none") {
					const error = `Task ${taskId}: grant usage rights 操作失败 - token 尚未被铸造`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else if (caller && caller !== currentOwner) {
					const error = `Task ${taskId}: grant usage rights 操作失败 - caller(${caller}) 不是当前所有者(${currentOwner})，无权授予使用权`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					// grant 成功，将 callee 加入使用权数组
					const newGrantees: string[] = [];
					calleeArray.forEach((grantee) => {
						if (grantee && !usageRights.includes(grantee)) {
							usageRights.push(grantee);
							newGrantees.push(grantee);
						}
					});
					console.log(`  ✓ grant usage rights 成功，新增使用权: [${newGrantees.join(", ")}]`);
					console.log(`  当前使用权列表: [${usageRights.join(", ")}]`);
				}
			} else if (operationLower === "revoke usage rights") {
				// revoke usage rights 操作：caller 必须是所有者，将 callee 从使用权数组中移除
				if (currentOwner === "none") {
					const error = `Task ${taskId}: revoke usage rights 操作失败 - token 尚未被铸造`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else if (caller && caller !== currentOwner) {
					const error = `Task ${taskId}: revoke usage rights 操作失败 - caller(${caller}) 不是当前所有者(${currentOwner})，无权撤销使用权`;
					validationErrors.push(error);
					console.error(`  ✗ ${error}`);
				} else {
					// revoke 成功，将 callee 从使用权数组中移除
					const revokedGrantees: string[] = [];
					calleeArray.forEach((grantee) => {
						const index = usageRights.indexOf(grantee);
						if (index > -1) {
							usageRights.splice(index, 1);
							revokedGrantees.push(grantee);
						}
					});
					console.log(`  ✓ revoke usage rights 成功，移除使用权: [${revokedGrantees.join(", ")}]`);
					console.log(`  当前使用权列表: [${usageRights.join(", ")}]`);
				}
			} else if (operationLower === "query") {
				// query 操作：不影响所有权和使用权
				console.log(`  ✓ query 操作，不影响所有权和使用权`);
			} else {
				console.warn(`  ? 未知操作类型: ${operation}`);
			}
		}

		console.log("\n=== 所有权和使用权追踪验证完成 ===");
		console.log(`最终所有者: ${currentOwner}`);
		console.log(`最终使用权: [${usageRights.join(", ")}]`);

		// 7. 返回验证结果
		if (validationErrors.length > 0) {
			console.error("\n验证失败，发现以下错误:");
			validationErrors.forEach((err, idx) => {
				console.error(`  ${idx + 1}. ${err}`);
			});
		} else {
			console.log("\n✓ 验证通过：所有操作的所有权和使用权转移逻辑正确");
		}

		return {
			dataObjectId: info.dataObjectId,
			assetType: info.assetType,
			tokenType: info.tokenType,
			success: validationErrors.length === 0,
			errors: validationErrors,
			finalOwner: currentOwner,
			finalUsageRights: usageRights,
		};
	};

	const handleValidation = async (): Promise<boolean> => {
		setIsValidating(true);
		setValidationResult(null);

		try {
			// 打印数据到控制台
			console.log("=== Validation Data ===");
			console.log("param:", param);
			console.log("ERCChaincodeNames:", param.ERCChaincodeNames);
			console.log("bpmnId:", bpmnId);
			console.log("chaincodeToNameMap (from state):", chaincodeToNameMap);

			// 获取 BPMN 内容
			console.log("Fetching BPMN data...");
			console.log("Using consortiumId:", consortiumId);
			const bpmnData = await retrieveBPMN(bpmnId, consortiumId);
			console.log("BPMN data retrieved:", bpmnData ? "Yes" : "No");
			console.log("Full BPMN data object:", bpmnData);
			console.log("BPMN data keys:", bpmnData ? Object.keys(bpmnData) : "null");

			if (!bpmnData) {
				throw new Error("Failed to retrieve BPMN data - API returned null");
			}

			const bpmnXml = bpmnData.bpmnContent;
			console.log("BPMN XML length:", bpmnXml ? bpmnXml.length : 0);
			console.log("BPMN XML first 500 chars:", bpmnXml ? bpmnXml.substring(0, 500) : "NULL");

			if (!bpmnXml) {
				throw new Error("BPMN data does not contain bpmnContent field");
			}

			// 解析 BPMN XML
			const parser = new DOMParser();
			const xmlDoc = parser.parseFromString(bpmnXml, "text/xml");

			// 检查解析错误
			const parseError = xmlDoc.getElementsByTagName("parsererror");
			if (parseError.length > 0) {
				console.error("XML Parse Error:", parseError[0].textContent);
				throw new Error("Failed to parse BPMN XML");
			}
			console.log("XML parsed successfully");

			// 获取 ERCChaincodeNames 映射 (Task ID -> Contract Name)
			const ercChaincodeNames = param.ERCChaincodeNames || {};
			console.log("ERC Chaincode Names:", ercChaincodeNames);
			console.log("Number of tasks with ERC bindings:", Object.keys(ercChaincodeNames).length);

			// 构建 DataObject -> Tasks 映射
			const dataObjectToTasks: Record<string, Set<string>> = {};

			// 查找所有元素
			const allElements = xmlDoc.getElementsByTagName("*");
			console.log("Total XML elements:", allElements.length);

			// 统计找到的关联数量
			let inputAssocCount = 0;
			let outputAssocCount = 0;

			// 遍历所有元素，查找 DataInputAssociation 和 DataOutputAssociation
			for (let i = 0; i < allElements.length; i++) {
				const el = allElements[i];
				const tagName = el.tagName.toLowerCase();

				// 处理 DataInputAssociation (DataObject -> Task)
				if (tagName.includes("datainputassociation")) {
					inputAssocCount++;
					console.log(`Found DataInputAssociation #${inputAssocCount}`);

					// 找到父 Task
					let taskElement = el.parentElement;
					let depth = 0;
					while (taskElement && !taskElement.tagName.toLowerCase().includes("task") && depth < 10) {
						taskElement = taskElement.parentElement;
						depth++;
					}

					if (taskElement) {
						const taskId = taskElement.getAttribute("id");
						console.log(`  Parent Task ID: ${taskId}`);
						console.log(`  Has ERC binding: ${taskId && ercChaincodeNames[taskId] ? 'Yes' : 'No'}`);

						if (taskId && ercChaincodeNames[taskId]) {
							// 查找 sourceRef (DataObject ID) - 只查找直接子元素
							for (let j = 0; j < el.children.length; j++) {
								const child = el.children[j];
								if (child.tagName.toLowerCase().includes("sourceref")) {
									const sourceRef = child.textContent?.trim();
									console.log(`  Found sourceRef: ${sourceRef}`);
									if (sourceRef) {
										console.log(`  ✓ Mapping: DataObject ${sourceRef} -> Task ${taskId} (${ercChaincodeNames[taskId]})`);
										if (!dataObjectToTasks[sourceRef]) {
											dataObjectToTasks[sourceRef] = new Set();
										}
										dataObjectToTasks[sourceRef].add(taskId);
									}
								}
							}
						}
					} else {
						console.log(`  ✗ No parent Task found`);
					}
				}

				// 处理 DataOutputAssociation (Task -> DataObject)
				if (tagName.includes("dataoutputassociation")) {
					outputAssocCount++;
					console.log(`Found DataOutputAssociation #${outputAssocCount}`);

					// 找到父 Task
					let taskElement = el.parentElement;
					let depth = 0;
					while (taskElement && !taskElement.tagName.toLowerCase().includes("task") && depth < 10) {
						taskElement = taskElement.parentElement;
						depth++;
					}

					if (taskElement) {
						const taskId = taskElement.getAttribute("id");
						console.log(`  Parent Task ID: ${taskId}`);
						console.log(`  Has ERC binding: ${taskId && ercChaincodeNames[taskId] ? 'Yes' : 'No'}`);

						if (taskId && ercChaincodeNames[taskId]) {
							// 查找 targetRef (DataObject ID) - 只查找直接子元素
							for (let j = 0; j < el.children.length; j++) {
								const child = el.children[j];
								if (child.tagName.toLowerCase().includes("targetref")) {
									const targetRef = child.textContent?.trim();
									console.log(`  Found targetRef: ${targetRef}`);
									if (targetRef) {
										console.log(`  ✓ Mapping: Task ${taskId} (${ercChaincodeNames[taskId]}) -> DataObject ${targetRef}`);
										if (!dataObjectToTasks[targetRef]) {
											dataObjectToTasks[targetRef] = new Set();
										}
										dataObjectToTasks[targetRef].add(taskId);
									}
								}
							}
						}
					} else {
						console.log(`  ✗ No parent Task found`);
					}
				}
			}

			console.log("=== Summary ===");
			console.log(`Total DataInputAssociations found: ${inputAssocCount}`);
			console.log(`Total DataOutputAssociations found: ${outputAssocCount}`);
			console.log("DataObject to Tasks mapping:", dataObjectToTasks);
			console.log("Number of DataObjects found:", Object.keys(dataObjectToTasks).length);

			// 校验：检查每个 DataObject 连接的所有 Tasks 是否使用相同的合约名
			const errors: Array<{ dataObjectId: string; taskIds: string[]; contracts: string[] }> = [];
			const dataObjectContractMap: Record<string, string> = {};

			for (const [dataObjectId, taskIds] of Object.entries(dataObjectToTasks)) {
				const taskIdArray = Array.from(taskIds);
				const contracts = taskIdArray.map(taskId => ercChaincodeNames[taskId]).filter(Boolean);
				const uniqueContracts = Array.from(new Set(contracts));

				if (uniqueContracts.length > 1) {
					// 发现不一致：同一个 DataObject 连接的 Tasks 使用了不同的合约
					errors.push({
						dataObjectId,
						taskIds: taskIdArray,
						contracts: uniqueContracts,
					});
				} else if (uniqueContracts.length === 1) {
					// 校验通过：所有 Tasks 使用相同的合约
					dataObjectContractMap[dataObjectId] = uniqueContracts[0];
				}
			}

			if (errors.length > 0) {
				setValidationResult({
					success: false,
					message: `发现 ${errors.length} 个 DataObject 的 Task 合约名不一致`,
					errors,
				});
				message.error("校验失败：存在 DataObject 连接的 Tasks 使用了不同的合约名");
				return false;
			} else {
				setValidationResult({
					success: true,
					message: "校验通过：所有 DataObject 连接的 Tasks 使用了一致的合约名",
					dataObjectContractMap,
				});
				console.log("DataObject -> Contract mapping:", dataObjectContractMap);
				message.success("校验通过！");
				return true;
			}
		} catch (error) {
			console.error("Validation error:", error);
			message.error("校验过程中发生错误");
			setValidationResult({
				success: false,
				message: `校验错误: ${error.message}`,
			});
			return false;
		} finally {
			setIsValidating(false);
		}
	};

	const handleCancel = () => {
		setOpen(false);
	};

	// 合并后的验证函数：先执行校验，通过后执行资产类型推理验证
	const handleCombinedValidation = async () => {
		const validationPassed = await handleValidation();
		if (validationPassed) {
			await performAssetTypeBasedValidation();
		}
	};

	return (
		<Modal
			title="参数校验"
			open={open}
			onCancel={handleCancel}
			footer={[
				<Button key="cancel" onClick={handleCancel}>
					关闭
				</Button>,
			]}
			width={1200}
		>
			<div style={{ marginBottom: "20px" }}>
				<Descriptions title="校验数据" bordered column={1}>
					<Descriptions.Item label="Contract Name">{contract_name}</Descriptions.Item>
					<Descriptions.Item label="URL">{url}</Descriptions.Item>
					<Descriptions.Item label="Parameters">
						<pre style={{ maxHeight: "300px", overflow: "auto", background: "#f5f5f5", padding: "10px" }}>
							{JSON.stringify(param, null, 2)}
						</pre>
					</Descriptions.Item>
				</Descriptions>
			</div>

			<div style={{ marginBottom: "20px" }}>
				<h3 style={{ marginBottom: "10px" }}>BPMN 流程图</h3>
				<div
					style={{
						border: "1px solid #d9d9d9",
						borderRadius: "4px",
						padding: "10px",
						maxHeight: "400px",
						overflow: "auto",
						background: "#fafafa",
					}}
					dangerouslySetInnerHTML={{ __html: svgContent }}
				/>
			</div>

			{/* 校验结果显示 */}
			{validationResult && (
				<div style={{ marginBottom: "20px" }}>
					<Alert
						message={validationResult.success ? "校验成功" : "校验失败"}
						description={validationResult.message}
						type={validationResult.success ? "success" : "error"}
						showIcon
					/>

					{/* 显示错误详情 */}
					{!validationResult.success && validationResult.errors && validationResult.errors.length > 0 && (
						<div style={{ marginTop: "16px" }}>
							<h4>错误详情：</h4>
							<Table
								dataSource={validationResult.errors.map((error, index) => ({
									key: index,
									dataObjectId: error.dataObjectId,
									taskIds: error.taskIds.join(", "),
									contracts: error.contracts.join(", "),
								}))}
								columns={[
									{
										title: "DataObject ID",
										dataIndex: "dataObjectId",
										key: "dataObjectId",
									},
									{
										title: "关联的 Task IDs",
										dataIndex: "taskIds",
										key: "taskIds",
									},
									{
										title: "使用的合约名（不一致）",
										dataIndex: "contracts",
										key: "contracts",
									},
								]}
								pagination={false}
								size="small"
							/>
						</div>
					)}

					{/* 显示成功的 DataObject -> Contract 映射 */}
					{validationResult.success && validationResult.dataObjectContractMap && (
						<div style={{ marginTop: "16px" }}>
							<h4>DataObject → 合约名映射：</h4>
							<Table
								dataSource={Object.entries(validationResult.dataObjectContractMap).map(([dataObjectId, contractName], index) => ({
									key: index,
									dataObjectId,
									contractName,
								}))}
								columns={[
									{
										title: "DataObject ID",
										dataIndex: "dataObjectId",
										key: "dataObjectId",
									},
									{
										title: "合约名",
										dataIndex: "contractName",
										key: "contractName",
									},
								]}
								pagination={false}
								size="small"
							/>
						</div>
					)}
				</div>
			)}

			<div style={{ padding: "10px", background: "#f0f0f0", borderRadius: "4px" }}>
				<p style={{ margin: 0, color: "#666" }}>
					<strong>说明：</strong>点击"执行校验"按钮将会校验 BPMN 图中的 DataObject 与 Task 的合约绑定关系。
					校验逻辑会检查连接到同一个 DataObject 的所有 Tasks 是否使用了相同的 ERC 合约名。
					如果校验通过，将生成 DataObject → 合约名的映射关系供后续使用。
				</p>
			</div>
		</Modal>
	);
};