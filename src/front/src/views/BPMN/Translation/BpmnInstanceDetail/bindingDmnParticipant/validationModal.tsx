import React, { useState } from "react";
import { Modal, Button, Descriptions, message, Alert, Table } from "antd";
import { useBpmnSvg } from "./hooks";
import { retrieveBPMN } from "@/api/externalResource";

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

	/**
	 * 调用合约函数的模板方法
	 * @param methodName - 要调用的合约方法名
	 * @param contractName - 合约名称
	 * @param additionalParams - 额外的参数对象
	 *
	 * 参考 ERCAddMintAuthority 的调用方式:
	 * await ERCAddMintAuthority(ercIdTokenMap, chaincode_url, consortiumId, instanceid.toString(), msps)
	 */
	const invokeContractMethod = async (
		methodName: string,
		contractName: string,
		additionalParams?: Record<string, any>
	) => {
		try {
			console.log(`Invoking contract method: ${methodName}`);
			console.log(`Contract name: ${contractName}`);
			console.log(`Consortium ID: ${consortiumId}`);
			console.log(`Additional params:`, additionalParams);

			// TODO: 实现具体的合约调用逻辑
			// 这里可以根据 methodName 动态调用不同的 API 方法
			// 例如: await someAPI[methodName](contractName, consortiumId, ...additionalParams)

			message.info(`合约方法 ${methodName} 调用准备就绪`);
		} catch (error) {
			console.error(`Error invoking contract method ${methodName}:`, error);
			message.error(`调用合约方法 ${methodName} 失败`);
		}
	};

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
			console.log("=== Asset Type Based Validation ===");
			console.log("Using bpmnId:", bpmnId);
			console.log("Using consortiumId:", consortiumId);

			// 获取 BPMN XML
			console.log("Fetching BPMN data...");
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

			// 扫描所有 DataObject 元素
			const dataObjects = xmlDoc.querySelectorAll('[id^="DataObjectReference"]');
			console.log(`Found ${dataObjects.length} DataObject elements`);
			console.log("DataObject elements:", dataObjects);

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
					isInput: boolean;  // Task -> DataObject (input) or DataObject -> Task (output)
				}>;
			}> = {};

			// 遍历所有 DataObject，提取资产信息
			dataObjects.forEach((dataObj: any) => {
				const dataObjectId = dataObj.getAttribute("id");
				console.log(`\nProcessing DataObject: ${dataObjectId}`);
				console.log(`  DataObject tag name:`, dataObj.tagName);
				console.log(`  DataObject innerHTML (first 500 chars):`, dataObj.innerHTML?.substring(0, 500));
				console.log(`  DataObject children count:`, dataObj.children.length);
				console.log(`  DataObject children:`, Array.from(dataObj.children).map((c: any) => c.tagName));

				// 使用辅助函数查找 documentation
				const finalDocumentation = findDocumentation(dataObj);
				console.log(`  Found ${finalDocumentation ? finalDocumentation.length : 0} documentation elements`);

				if (finalDocumentation && finalDocumentation.length > 0) {
					try {
						const docText = finalDocumentation[0].textContent;
						console.log(`  Documentation text:`, docText);

						const assetInfo = JSON.parse(docText);
						console.log(`  Parsed asset info:`, assetInfo);

						dataObjectTaskMap[dataObjectId] = {
							dataObjectId,
							assetType: assetInfo.assetType || "",
							tokenType: assetInfo.tokenType,
							tokenName: assetInfo.tokenName,
							tokenId: assetInfo.tokenId,
							tokenHasExistInERC: assetInfo.tokenHasExistInERC || false,
							tasks: []
						};

						console.log(`  ✓ DataObject ${dataObjectId} added to map`);
					} catch (error) {
						console.warn(`  ✗ Failed to parse documentation for ${dataObjectId}:`, error);
					}
				} else {
					console.warn(`  ✗ No documentation found for ${dataObjectId}`);
				}
			});

			console.log(`\nTotal DataObjects in map: ${Object.keys(dataObjectTaskMap).length}`);
			console.log("DataObject Task Map:", dataObjectTaskMap);

			// 扫描所有关联关系（DataInputAssociation 和 DataOutputAssociation）
			console.log("\n=== Scanning for Data Associations ===");
			const allElements = xmlDoc.getElementsByTagName("*");
			console.log(`Total XML elements to scan: ${allElements.length}`);

			let inputAssocCount = 0;
			let outputAssocCount = 0;

			for (let i = 0; i < allElements.length; i++) {
				const el = allElements[i];
				const tagName = el.tagName.toLowerCase();

				// 处理 DataInputAssociation (DataObject -> Task)
				if (tagName.includes("datainputassociation")) {
					inputAssocCount++;
					console.log(`\nFound DataInputAssociation #${inputAssocCount}`);

					const sourceRef = el.querySelector("sourceRef")?.textContent?.trim();
					console.log(`  sourceRef: ${sourceRef}`);

					// 找到父 Task
					let taskElement = el.parentElement;
					let depth = 0;
					while (taskElement && !taskElement.tagName.toLowerCase().includes("task") && depth < 10) {
						taskElement = taskElement.parentElement;
						depth++;
					}

					if (taskElement && sourceRef && dataObjectTaskMap[sourceRef]) {
						const taskId = taskElement.getAttribute("id");
						console.log(`  Parent Task ID: ${taskId}`);

						const taskDoc = findDocumentation(taskElement);
						let operation = "";

						if (taskDoc && taskDoc.length > 0) {
							try {
								const taskInfo = JSON.parse(taskDoc[0].textContent);
								operation = taskInfo.operation || "";
								console.log(`  Task operation: ${operation}`);
							} catch {}
						}

						dataObjectTaskMap[sourceRef].tasks.push({
							taskId,
							operation,
							isInput: false  // DataObject -> Task (Task 使用 DataObject 作为输入)
						});
						console.log(`  ✓ Added to DataObject ${sourceRef}`);
					} else {
						console.log(`  ✗ Skipped: taskElement=${!!taskElement}, sourceRef=${sourceRef}, inMap=${sourceRef ? !!dataObjectTaskMap[sourceRef] : false}`);
					}
				}

				// 处理 DataOutputAssociation (Task -> DataObject)
				if (tagName.includes("dataoutputassociation")) {
					outputAssocCount++;
					console.log(`\nFound DataOutputAssociation #${outputAssocCount}`);

					const targetRef = el.querySelector("targetRef")?.textContent?.trim();
					console.log(`  targetRef: ${targetRef}`);

					// 找到父 Task
					let taskElement = el.parentElement;
					let depth = 0;
					while (taskElement && !taskElement.tagName.toLowerCase().includes("task") && depth < 10) {
						taskElement = taskElement.parentElement;
						depth++;
					}

					if (taskElement && targetRef && dataObjectTaskMap[targetRef]) {
						const taskId = taskElement.getAttribute("id");
						console.log(`  Parent Task ID: ${taskId}`);

						const taskDoc = findDocumentation(taskElement);
						let operation = "";

						if (taskDoc && taskDoc.length > 0) {
							try {
								const taskInfo = JSON.parse(taskDoc[0].textContent);
								operation = taskInfo.operation || "";
								console.log(`  Task operation: ${operation}`);
							} catch {}
						}

						dataObjectTaskMap[targetRef].tasks.push({
							taskId,
							operation,
							isInput: true  // Task -> DataObject (Task 产生 DataObject 作为输出)
						});
						console.log(`  ✓ Added to DataObject ${targetRef}`);
					} else {
						console.log(`  ✗ Skipped: taskElement=${!!taskElement}, targetRef=${targetRef}, inMap=${targetRef ? !!dataObjectTaskMap[targetRef] : false}`);
					}
				}
			}

			console.log("\n=== Association Scan Summary ===");
			console.log(`Total DataInputAssociations found: ${inputAssocCount}`);
			console.log(`Total DataOutputAssociations found: ${outputAssocCount}`);

			// 根据资产类型进行分支推理
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

				// 分支 1: Transferable FT
				if (info.assetType === "transferable" && info.tokenType === "FT") {
					console.log("Branch: Transferable FT");
					await validateTransferableFT(info);
				}
				// 分支 2: Transferable NFT
				else if (info.assetType === "transferable" && info.tokenType === "NFT") {
					console.log("Branch: Transferable NFT");
					await validateTransferableNFT(info);
				}
				// 分支 3: Value-added NFT
				else if (info.assetType === "value-added") {
					console.log("Branch: Value-added NFT");
					await validateValueAddedNFT(info);
				}
				// 分支 4: Distributive NFT
				else if (info.assetType === "distributive") {
					console.log("Branch: Distributive NFT");
					await validateDistributiveNFT(info);
				}
				else {
					console.warn(`Unknown asset type combination: ${info.assetType} / ${info.tokenType}`);
				}
			}

			console.log("=== Asset Type Based Validation Complete ===");
			message.success("资产类型推理验证完成");

		} catch (error) {
			console.error("Asset type based validation error:", error);
			message.error("资产类型推理验证失败");
		}
	};

	/**
	 * 分支 1: Transferable FT 验证逻辑
	 */
	const validateTransferableFT = async (info: any) => {
		console.log("TODO: Implement Transferable FT validation logic");
		// 可用操作: mint, burn, Transfer, query
		// 特点: 使用 tokenNumber, 不需要 tokenId
		// 注意: FT 不使用 tokenHasExistInERC 字段，因为 FT 没有单独的 tokenId
		// TODO: 添加具体的验证逻辑
	};

	/**
	 * 分支 2: Transferable NFT 验证逻辑
	 */
	const validateTransferableNFT = async (info: any) => {
		console.log("Validating Transferable NFT");
		// 可用操作: mint, burn, Transfer, query
		// 特点: 需要 tokenId, 不需要 tokenNumber

		const tokenHasExistInERC = info.tokenHasExistInERC || false;

		if (tokenHasExistInERC) {
			console.log("Sub-branch: Token already exists in ERC contract");
			// 子分支 2.1: Token 已存在于 ERC 合约中
			// 逻辑: 跳过 mint 操作，假设 token 已经被铸造
			// TODO: 添加具体的验证逻辑
			// - 验证不应该有 mint 操作
			// - 可以有 burn, Transfer, query 操作
		} else {
			console.log("Sub-branch: Token needs to be minted");
			// 子分支 2.2: Token 需要被铸造
			// 逻辑: 需要先执行 mint 操作
			// TODO: 添加具体的验证逻辑
			// - 验证应该有 mint 操作
			// - mint 操作应该在其他操作之前
		}
	};

	/**
	 * 分支 3: Value-added NFT 验证逻辑
	 */
	const validateValueAddedNFT = async (info: any) => {
		console.log("Validating Value-added NFT");
		// 可用操作: branch, merge, Transfer, query
		// 特点: 需要 tokenId, refTokenIds (merge 必须非空)

		const tokenHasExistInERC = info.tokenHasExistInERC || false;

		if (tokenHasExistInERC) {
			console.log("Sub-branch: Token already exists in ERC contract");
			// 子分支 3.1: Token 已存在于 ERC 合约中
			// 逻辑: 跳过 branch/merge 操作中的 mint 部分
			// TODO: 添加具体的验证逻辑
			// - 验证 branch/merge 操作时不需要铸造新 token
			// - 可以直接进行 Transfer, query 操作
		} else {
			console.log("Sub-branch: Token needs to be created via branch/merge");
			// 子分支 3.2: Token 需要通过 branch/merge 创建
			// 逻辑: 需要通过 branch 或 merge 操作创建新的增值型 token
			// TODO: 添加具体的验证逻辑
			// - 验证应该有 branch 或 merge 操作
			// - branch/merge 操作会创建新的 token
		}
	};

	/**
	 * 分支 4: Distributive NFT 验证逻辑
	 */
	const validateDistributiveNFT = async (info: any) => {
		console.log("Validating Distributive NFT");
		// 可用操作: mint, burn, grant usage rights, revoke usage rights, transfer, query
		// 特点: burn 需要 tokenId

		const tokenHasExistInERC = info.tokenHasExistInERC || false;

		if (tokenHasExistInERC) {
			console.log("Sub-branch: Token already exists in ERC contract");
			// 子分支 4.1: Token 已存在于 ERC 合约中
			// 逻辑: 跳过 mint 操作，假设 token 已经被铸造
			// TODO: 添加具体的验证逻辑
			// - 验证不应该有 mint 操作
			// - 可以有 burn, grant usage rights, revoke usage rights, transfer, query 操作
		} else {
			console.log("Sub-branch: Token needs to be minted");
			// 子分支 4.2: Token 需要被铸造
			// 逻辑: 需要先执行 mint 操作
			// TODO: 添加具体的验证逻辑
			// - 验证应该有 mint 操作
			// - mint 操作应该在其他操作之前
		}
	};

	const handleValidation = async () => {
		setIsValidating(true);
		setValidationResult(null);

		try {
			// 打印数据到控制台
			console.log("=== Validation Data ===");
			console.log("param:", param);
			console.log("ERCChaincodeNames:", param.ERCChaincodeNames);
			console.log("bpmnId:", bpmnId);

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
			} else {
				setValidationResult({
					success: true,
					message: "校验通过：所有 DataObject 连接的 Tasks 使用了一致的合约名",
					dataObjectContractMap,
				});
				console.log("DataObject -> Contract mapping:", dataObjectContractMap);
				message.success("校验通过！");
			}
		} catch (error) {
			console.error("Validation error:", error);
			message.error("校验过程中发生错误");
			setValidationResult({
				success: false,
				message: `校验错误: ${error.message}`,
			});
		} finally {
			setIsValidating(false);
		}
	};

	const handleCancel = () => {
		setOpen(false);
	};

	const handleDownloadBpmnXml = async () => {
		try {
			console.log("Downloading BPMN XML...");
			console.log("Using bpmnId:", bpmnId);
			console.log("Using consortiumId:", consortiumId);

			const bpmnData = await retrieveBPMN(bpmnId, consortiumId);
			console.log("BPMN data retrieved:", bpmnData ? "Yes" : "No");
			console.log("Full BPMN data object:", bpmnData);
			console.log("BPMN data keys:", bpmnData ? Object.keys(bpmnData) : "null");

			if (!bpmnData || !bpmnData.bpmnContent) {
				message.error("无法获取 BPMN XML 内容");
				console.error("BPMN data is null or missing bpmnContent");
				console.error("Available fields:", bpmnData ? Object.keys(bpmnData).join(", ") : "none");
				return;
			}

			const bpmnXml = bpmnData.bpmnContent;
			console.log("BPMN XML retrieved, length:", bpmnXml.length);

			// 创建 Blob 对象
			const blob = new Blob([bpmnXml], { type: "text/xml" });

			// 创建下载链接
			const url = window.URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			link.download = `bpmn_${bpmnId}_${new Date().getTime()}.xml`;

			// 触发下载
			document.body.appendChild(link);
			link.click();

			// 清理
			document.body.removeChild(link);
			window.URL.revokeObjectURL(url);

			message.success("BPMN XML 已下载");
			console.log("BPMN XML downloaded successfully");
		} catch (error) {
			console.error("Download error:", error);
			message.error("下载 BPMN XML 时发生错误");
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
				<Button
					key="download"
					onClick={handleDownloadBpmnXml}
				>
					下载 BPMN XML
				</Button>,
				<Button
					key="assetValidation"
					type="default"
					onClick={performAssetTypeBasedValidation}
				>
					资产类型推理验证
				</Button>,
				<Button
					key="validate"
					type="primary"
					onClick={handleValidation}
					loading={isValidating}
				>
					执行校验
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