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
			// 注意：各分支验证函数内部已经显示了具体的验证结果消息
			// 这里不再显示额外的成功消息，避免弹窗重复

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
			// 逻辑: 需要先执行 mint 操作，然后根据所有权追踪验证后续操作

			// 获取 BPMN XML 用于解析 SequenceFlow
			const bpmnData = await retrieveBPMN(bpmnId, consortiumId);
			if (!bpmnData || !bpmnData.bpmnContent) {
				console.error("Failed to retrieve BPMN data for task ordering");
				return;
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

			// 6. 所有权追踪验证
			// 初始所有者为 "none"，表示 token 尚未被铸造
			let currentOwner: string = "none";
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

			// 7. 输出验证结果
			if (validationErrors.length > 0) {
				console.error("\n验证失败，发现以下错误:");
				validationErrors.forEach((err, idx) => {
					console.error(`  ${idx + 1}. ${err}`);
				});
				// 使用 Modal.error 弹窗显示详细错误信息
				Modal.error({
					title: "Transferable NFT 验证失败",
					content: (
						<div>
							<p>发现 {validationErrors.length} 个错误:</p>
							<ul style={{ paddingLeft: "20px", margin: "10px 0" }}>
								{validationErrors.map((err, idx) => (
									<li key={idx} style={{ marginBottom: "5px" }}>{err}</li>
								))}
							</ul>
						</div>
					),
					width: 600,
				});
			} else {
				console.log("\n✓ 验证通过：所有操作的所有权转移逻辑正确");
				Modal.success({
					title: "Transferable NFT 验证通过",
					content: "所有操作的所有权转移逻辑正确",
				});
			}
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
			// 逻辑: 需要先执行 mint 操作，然后根据所有权和使用权追踪验证后续操作

			// 获取 BPMN XML 用于解析 SequenceFlow
			const bpmnData = await retrieveBPMN(bpmnId, consortiumId);
			if (!bpmnData || !bpmnData.bpmnContent) {
				console.error("Failed to retrieve BPMN data for task ordering");
				return;
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

			// 6. 所有权和使用权追踪验证
			// 初始所有者为 "none"，表示 token 尚未被铸造
			// 使用权用数组记录，初始为空
			let currentOwner: string = "none";
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

			// 7. 输出验证结果
			if (validationErrors.length > 0) {
				console.error("\n验证失败，发现以下错误:");
				validationErrors.forEach((err, idx) => {
					console.error(`  ${idx + 1}. ${err}`);
				});
				// 使用 Modal.error 弹窗显示详细错误信息
				Modal.error({
					title: "Distributive NFT 验证失败",
					content: (
						<div>
							<p>发现 {validationErrors.length} 个错误:</p>
							<ul style={{ paddingLeft: "20px", margin: "10px 0" }}>
								{validationErrors.map((err, idx) => (
									<li key={idx} style={{ marginBottom: "5px" }}>{err}</li>
								))}
							</ul>
						</div>
					),
					width: 600,
				});
			} else {
				console.log("\n✓ 验证通过：所有操作的所有权和使用权转移逻辑正确");
				Modal.success({
					title: "Distributive NFT 验证通过",
					content: (
						<div>
							<p>所有操作的所有权和使用权转移逻辑正确</p>
							<p style={{ marginTop: "10px" }}>最终状态:</p>
							<ul style={{ paddingLeft: "20px", margin: "5px 0" }}>
								<li>所有者: {currentOwner}</li>
								<li>使用权: [{usageRights.join(", ")}]</li>
							</ul>
						</div>
					),
				});
			}
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