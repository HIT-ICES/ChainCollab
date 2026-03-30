import { useEffect, useMemo, useRef, useState } from "react";
import { css } from "@emotion/css";
import { useLocation } from "react-router-dom";
import {
	Button,
	Input,
	Form,
	Upload,
	Tag,
	Typography,
	Select,
	Space,
	Switch,
	Alert,
	Slider,
	Progress,
	message,
} from "antd";
import { UploadOutlined } from "@ant-design/icons";
import {
	useBPMNIntanceDetailData,
	useBPMNDetailData,
} from "./hook";
import {
	getFireflyIdentity,
} from "@/api/externalResource.ts";
import TestComponentV2 from "./testComponent.jsx";

import {
	getMessageWithId,
	getBatchWithId,
	getOperationWithId,
	getEventWithTX,
} from "@/api/fireflyAPI.ts";

// 定义Flex容器样式
const flexContainerStyle = css`
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: flex-start; // Adjusted for a more consistent alignment
  gap: 10px; // Spacing between form items
  flex-wrap: wrap; // Allow wrapping for smaller screens or many items
`;
const sleep = async (ms) => {
	return new Promise((resolve) => setTimeout(resolve, ms));
};

import {
	invokeEventAction,
	invokeGatewayAction,
	invokeBusinessRuleAction,
	fireflyFileTransfer,
	fireflyDataTransfer,
	invokeMessageAction,
	callFireflyContract,
} from "@/api/executionAPI.ts";

type ActionPhase = "start" | "success" | "error";
type ActionKind = "event" | "gateway" | "message" | "businessRule";

type ActionRecordEvent = {
	traceId: string;
	phase: ActionPhase;
	type: ActionKind;
	action: string;
	elementId: string;
	detail?: string;
	timestamp?: string;
	txId?: string;
	fireflyId?: string;
	error?: string;
	payload?: any;
};

type ActionRecord = {
	traceId: string;
	type: ActionKind;
	action: string;
	elementId: string;
	status: "running" | "success" | "failed";
	startedAt: string;
	endedAt: string | null;
	detail: string;
	txId?: string;
	fireflyId?: string;
	error?: string;
	payload?: any;
};

type ExecutionMode = "real" | "mock";

const getElementId = (element: any): string =>
	element?.EventID ||
	element?.GatewayID ||
	element?.MessageID ||
	element?.BusinessRuleID ||
	"";

const parseMockElementsFromSvg = (svgContent?: string) => {
	if (!svgContent) return [];
	const seen = new Set<string>();
	const matches = Array.from(svgContent.matchAll(/data-element-id="([^"]+)"/g));
	const ids = matches
		.map((match) => match?.[1] || "")
		.filter((id) => {
			if (!id || id.endsWith("_label")) return false;
			if (
				id.startsWith("Message_") ||
				id.startsWith("Gateway_") ||
				id.startsWith("Event_") ||
				id.startsWith("StartEvent_") ||
				id.startsWith("EndEvent_") ||
				id.startsWith("Intermediate") ||
				id.startsWith("Activity_")
			) {
				if (seen.has(id)) return false;
				seen.add(id);
				return true;
			}
			return false;
		});
	return ids.map((id, index) => {
		const type = id.startsWith("Message_")
			? "message"
			: id.startsWith("Gateway_")
			? "gateway"
			: id.startsWith("Activity_")
			? "businessRule"
			: "event";
		const field =
			type === "message"
				? "MessageID"
				: type === "gateway"
				? "GatewayID"
				: type === "businessRule"
				? "BusinessRuleID"
				: "EventID";
		return {
			type,
			state: index === 0 ? 1 : 0,
			[field]: id,
		};
	});
};

const createTraceId = (prefix: string) =>
	`${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;

const InputComponentForMessage = ({
	currentElement,
	contractName,
	coreURL,
	bpmnName,
	contractMethodDes,
	bpmn,
	bpmnInstance,
	instanceId,
	the_identity,
	onActionRecord,
}) => {
	const format = JSON.parse(currentElement.Format);

	const transValue = (key, value) => {
		if (format.properties[key]?.type === "string") return value;
		if (format.properties[key]?.type === "number") return parseInt(value);
		if (format.properties[key]?.type === "boolean") return value === "true";
		return value;
	};

	const formRef = useRef(null);
	const isSender = currentElement.state === 1;
	const methodName =
		currentElement.MessageID + (isSender ? "_Send" : "_Complete");

	const confirmMessage = async () => {
		const traceId = createTraceId("message-confirm");
		onActionRecord?.({
			traceId,
			phase: "start",
			type: "message",
			action: methodName,
			elementId: currentElement.MessageID,
			detail: "Confirm message",
		});
		try {
			const res = await invokeMessageAction(
				coreURL,
				contractName,
				methodName,
				{},
				instanceId,
				the_identity?.identity?.data?.[0]?.value,
			);
			onActionRecord?.({
				traceId,
				phase: "success",
				type: "message",
				action: methodName,
				elementId: currentElement.MessageID,
				detail: "Message confirmed",
				fireflyId: currentElement.FireflyTranID,
				txId: res?.tx,
				payload: res,
			});
			message.success("Message confirmed");
		} catch (error: any) {
			onActionRecord?.({
				traceId,
				phase: "error",
				type: "message",
				action: methodName,
				elementId: currentElement.MessageID,
				detail: "Confirm failed",
				error: String(error?.message || error || "Unknown error"),
			});
			message.error(error?.message || "Message confirm failed");
		}
	};
	const [messageToConfirm, setMessageToConfirm] = useState([]);

	const TestResultColumns = [
		{
			title: "Index",
			dataIndex: "index",
			key: "index",
		},
		{
			title: "fileCostTime",
			dataIndex: "fileCostTime",
			key: "fileCostTime",
			render: (text, record, index) => {
				// show list
				return (
					<div>
						{text.map((item, index) => {
							return (
								<Tag key={index} color="blue">
									{item}
								</Tag>
							);
						})}
					</div>
				);
			},
		},
		{
			title: "messageCostTime",
			dataIndex: "messageCostTime",
			key: "messageCostTime",
		},
		{
			title: "chainCodeCostTime",
			dataIndex: "chainCodeCostTime",
			key: "chainCodeCostTime",
		},
	];

	const TestConfirmResultColumns = [
		{
			title: "Index",
			dataIndex: "index",
			key: "index",
		},
		{
			title: "TimeCost",
			dataIndex: "timeCost",
			key: "timeCost",
		},
	];

	useEffect(() => {
		if (isSender) {
			// setMessageToConfirm("Please confirm the message to send");
			return;
		}
		const fetchData = async () => {
			//http://127.0.0.1:5000/api/v1/namespaces/default/messages/{currentElement.fireflyTranID}/data
			try {
				const res = await axios.get(
					`${coreURL}/api/v1/namespaces/default/messages/${currentElement.FireflyTranID}/data`,
				);
				const messageToShow = res.data
					.map((item) => {
						return Object.keys(item.value).map((key) => ({
							name: key,
							value: item.value[key],
						}));
					})
					.reduce((acc, cur) => {
						return [...acc, ...cur];
					}, []);
				setMessageToConfirm(messageToShow);
			} catch (error: any) {
				message.error(error?.message || "Failed to load message data");
				setMessageToConfirm([]);
			}
		};
		fetchData();
	}, [currentElement]);

	if (!isSender) {
		return (
			<div
				style={{
					display: "flex",
					flexDirection: "column",
				}}
			>
				{/* Status */}
				<Typography.Text>
						{messageToConfirm.map((item) => {
							return (
								<Tag key={`${item.name}-${item.value}`} color="green">
									{item.name}: {item.value.toString()}
								</Tag>
							);
						})}
				</Typography.Text>
				<Button
					style={{ backgroundColor: "mediumspringgreen", marginTop: "10px" }}
					onClick={() => {
						confirmMessage();
					}}
				>
					Confirm
				</Button>
			</div>
		);
	}

	const onHandleMessage = async (values, output_obj = {}) => {
		const traceId = createTraceId("message-send");
		onActionRecord?.({
			traceId,
			phase: "start",
			type: "message",
			action: methodName,
			elementId: currentElement.MessageID,
			detail: "Send message and invoke contract",
		});
		try {
			const Identity = "did:firefly:" + the_identity?.name;

			let file_ids = [];
			for (let key in format.files) {
				const file = values[key];
				if (file) {
					const res = await TimeDecorator(
						fireflyFileTransfer,
						"File",
						"default/data",
					)(coreURL, file.file);
					file_ids.push(res.id);
				}
			}
			if (file_ids.length > 0) {
				await new Promise((resolve) => setTimeout(resolve, 2000));
			}

			const datatype = {
				name: bpmnName.split(".")[0] + "_" + currentElement.MessageID,
				version: "1",
			};
			let value = {};
			for (let key in format.properties) {
				value[key] = transValue(key, values[key]);
			}
			const dataItem1 = {
				datatype: datatype,
				value: value,
				validator: "json",
			};
			let dataItem2 = file_ids.map((id) => {
				return {
					id: id,
				};
			});
			const data = {
				data: [dataItem1, ...dataItem2],
				group: {
					members: [
						{
							identity: Identity,
						},
					],
				},
				header: {
					tag: "private",
					topics: [bpmnName + "_" + currentElement.MessageID],
				},
			};
			const res = await TimeDecorator(
				fireflyDataTransfer,
				"Data",
				"default/messages",
				output_obj,
			)(coreURL, data);
			output_obj["message_id"] = res.header.id;
			output_obj["message_create_time"] = res.header.created;
			const fireflyMessageID = res.header.id;

			const methodParams = (contractMethodDes.methods || [])
				.find((item) => {
					return item.name === methodName;
				})
				?.params?.filter((item) => {
					return item.name !== "fireflyTranID";
				}) || [];
			const otherKeyValuePair = methodParams
				.map((item) => {
					return {
						[item.name]: transValue(item.name, values[item.name]),
					};
				})
				.reduce((acc, cur) => {
					return { ...acc, ...cur };
				}, {});
			const res2 = await TimeDecorator(
				invokeMessageAction,
				"Message",
				"invoke/Message",
				output_obj,
			)(
				coreURL,
				contractName,
				methodName,
				{
					input: {
						...otherKeyValuePair,
						FireFlyTran: fireflyMessageID,
					},
				},
				instanceId,
				the_identity?.identity?.data?.[0]?.value,
			);
			output_obj["invoke_id"] = res2.id;
			output_obj["invoke_start_time"] = res2.created;
			onActionRecord?.({
				traceId,
				phase: "success",
				type: "message",
				action: methodName,
				elementId: currentElement.MessageID,
				detail: "Message sent and contract invoked",
				fireflyId: fireflyMessageID,
				txId: res2?.tx,
				payload: {
					message: res,
					invoke: res2,
				},
			});
			message.success("Message sent and contract invoked");
		} catch (error: any) {
			onActionRecord?.({
				traceId,
				phase: "error",
				type: "message",
				action: methodName,
				elementId: currentElement.MessageID,
				detail: "Message invoke failed",
				error: String(error?.message || error || "Unknown error"),
			});
			message.error(error?.message || "Message action failed");
			throw error;
		}
	};

	return (
		<div
			style={{
				display: "flex",
				flexDirection: "column",
			}}
		>
				<TestComponentV2
					processFunc={async () => {
						const output_obj = {};
						try {
							await onHandleMessage(formRef.current.getFieldsValue(), output_obj);
						} catch (error) {
							return {};
						}
						const core_url = coreURL;
					await sleep(3000);
					const message = await getMessageWithId(
						core_url,
						output_obj["message_id"],
					);
					const batch_id = message["batch"];
					const batch = await getBatchWithId(core_url, batch_id);
					const batch_time = batch["created"];
					const invoke = await getOperationWithId(
						core_url,
						output_obj["invoke_id"],
					);
					const txid = invoke["tx"];
					const events = await getEventWithTX(core_url, txid);
					const event_time = events[0]["created"];

					output_obj["batch_time"] = batch_time;
					output_obj["event_time"] = event_time;
					// 格式化为毫秒时间戳
					for (const key in output_obj) {
						output_obj[key] = TimeStampHandler(output_obj[key]);
					}
					return output_obj;
				}}
				calcFunc={(timeList) => {
					const res = [
						{
							step: "Private Data Bus",
							start_time: timeList["Data_start_time"],
							end_time: timeList["Data_end_time"],
						},
						{
							step: "IPFS",
							start_time: timeList["message_create_time"],
							end_time: timeList["batch_time"],
						},
						{
							step: "API Invoker",
							start_time: timeList["Message_start_time"],
							end_time: timeList["invoke_start_time"],
						},
						{
							step: "BPMN SC",
							start_time: timeList["invoke_start_time"],
							end_time: timeList["event_time"],
						},
					];
					return res;
				}}
			/>
			<Form
				layout="horizontal"
				className={flexContainerStyle}
				labelCol={{ span: 8 }}
				wrapperCol={{ span: 16 }}
				ref={formRef}
				onFinish={onHandleMessage}
			>
				<h1>LOGRES</h1>
				{Object.keys(format.properties).map((key) => {
					return (
						<Form.Item
							label={key}
							name={key}
							key={key}
							rules={[
								{
									required: format.required.includes(key),
									message: `${key} is required!`,
								},
							]}
						>
							<div>
								<Tag>{format.properties[key].type}</Tag>
								<Input placeholder={format.properties[key].description} />
							</div>
						</Form.Item>
					);
				})}
				{Object.keys(format.files).map((key) => {
					return (
						<Form.Item
							label={key}
							name={key}
							key={key}
							rules={[
								{
									required: format["file required"].includes(key),
									message: `${key} is required!`,
								},
							]}
						>
							<Upload
								beforeUpload={(file) => {
									return false;
								}}
							>
								<Button icon={<UploadOutlined />}>Upload</Button>
							</Upload>
						</Form.Item>
					);
				})}
				<Form.Item>
					<Button
						style={{ backgroundColor: "mediumspringgreen" }}
						htmlType="submit"
					>
						Submit
					</Button>
				</Form.Item>
			</Form>
			{/* Message Related Experiment */}
			<h1>LOGRES</h1>
		</div>
	);
};

const TimeDecorator = (func, label, url_pattern, output_obj = {}) => {
	return async (...args) => {
		const theRes = {};
		const observer = new PerformanceObserver((list) => {
			for (const entry of list.getEntries()) {
				const resourceEntry = entry as PerformanceResourceTiming;
				if (resourceEntry.name.includes(url_pattern)) {
					const navigationStart = performance.timing.navigationStart;
					theRes["start_time"] = navigationStart + resourceEntry.fetchStart;
					theRes["timeCost"] = resourceEntry.responseStart - resourceEntry.requestStart;
					theRes["end_time"] = navigationStart + resourceEntry.responseEnd;
				}
			}
		});
		observer.observe({ entryTypes: ["resource"] });
		const res = await func(...args);
		await sleep(300);
		observer.disconnect();
		output_obj[`${label}_start_time`] = theRes["start_time"];
		output_obj[`${label}_end_time`] = theRes["end_time"];
		return res;
	};
};

const TimeStampHandler = (time) => {
	if (!time) return "";
	if (typeof time === "number" || time.startsWith("17")) return Math.round(time);
	if (typeof time === "string") return new Date(time).getTime();
};

const ControlPanel = ({
	currentElement,
	contractName,
	coreURL,
	bpmnName,
	contractMethodDes,
	bpmnInstance,
	bpmn,
	instanceId,
	identity,
	onActionRecord,
	executionMode,
	onMockAction,
	mockProcessingElementId,
}) => {
	const type = currentElement?.type;
	const elementId = getElementId(currentElement);
	const isYourTurn = (() => {
		if (type === "event" || type === "gateway" || type === "businessRule")
			return currentElement?.state === 1;
		if (type === "message")
			return (
				currentElement?.state === 1 ||
				currentElement?.state === 2
			);
	})();
	const showTransactionId = type === "message" && currentElement?.state === 2;

	if (!isYourTurn) return null;

	if (executionMode === "mock") {
		const isMessageConfirm = type === "message" && currentElement?.state === 2;
		const isProcessing = mockProcessingElementId === elementId;
		return (
			<div
				style={{
					display: "flex",
					flexDirection: "column",
					border: "1px solid #dbeafe",
					borderRadius: 10,
					padding: 12,
					background: "#f8fafc",
					minWidth: 220,
					gap: 8,
				}}
			>
				<Typography.Text strong>
					{type} · {elementId}
				</Typography.Text>
				<Tag color={isMessageConfirm ? "orange" : "blue"}>
					{isMessageConfirm ? "WAIT_CONFIRM" : "READY"}
				</Tag>
				<Button
					type="primary"
					loading={isProcessing}
					onClick={() =>
						onMockAction?.(currentElement, isMessageConfirm ? "confirm" : "execute")
					}
				>
					{isMessageConfirm ? "Mock Confirm" : "Mock Execute"}
				</Button>
			</div>
		);
	}

	// EVENT

	const onHandleEvent = async () => {
		const traceId = createTraceId("event");
		onActionRecord?.({
			traceId,
			phase: "start",
			type: "event",
			action: "invokeEvent",
			elementId: currentElement.EventID,
			detail: "Invoke event",
		});
		try {
			const res = await TimeDecorator(invokeEventAction, "Event", "invoke/Event")(
				coreURL,
				contractName,
				currentElement.EventID,
				instanceId,
			);
			onActionRecord?.({
				traceId,
				phase: "success",
				type: "event",
				action: "invokeEvent",
				elementId: currentElement.EventID,
				detail: "Event invoked",
				txId: res?.tx,
				payload: res,
			});
			message.success("Event invoked");
		} catch (error: any) {
			onActionRecord?.({
				traceId,
				phase: "error",
				type: "event",
				action: "invokeEvent",
				elementId: currentElement.EventID,
				detail: "Event invoke failed",
				error: String(error?.message || error || "Unknown error"),
			});
			message.error(error?.message || "Event invoke failed");
		}
	};

	if (type === "event")
		return (
			<div
				style={{
					display: "flex",
					flexDirection: "column",
				}}
			>
				<Button
					style={{ backgroundColor: "mediumspringgreen" }}
					onClick={() => {
						onHandleEvent();
					}}
				>
					Next
				</Button>
			</div>
		);

	const onHandleGateway = async () => {
		const traceId = createTraceId("gateway");
		onActionRecord?.({
			traceId,
			phase: "start",
			type: "gateway",
			action: "invokeGateway",
			elementId: currentElement.GatewayID,
			detail: "Invoke gateway",
		});
		try {
			const res = await TimeDecorator(invokeGatewayAction, "Gateway", "invoke/Gateway")(
				coreURL,
				contractName,
				currentElement.GatewayID,
				instanceId,
			);
			onActionRecord?.({
				traceId,
				phase: "success",
				type: "gateway",
				action: "invokeGateway",
				elementId: currentElement.GatewayID,
				detail: "Gateway invoked",
				txId: res?.tx,
				payload: res,
			});
			message.success("Gateway invoked");
		} catch (error: any) {
			onActionRecord?.({
				traceId,
				phase: "error",
				type: "gateway",
				action: "invokeGateway",
				elementId: currentElement.GatewayID,
				detail: "Gateway invoke failed",
				error: String(error?.message || error || "Unknown error"),
			});
			message.error(error?.message || "Gateway invoke failed");
		}
	};

	if (type === "gateway")
		return (
			<div
				style={{
					display: "flex",
					flexDirection: "column",
				}}
			>
				<Button
					style={{ backgroundColor: "mediumspringgreen" }}
					onClick={() => {
						onHandleGateway();
					}}
				>
					Next
				</Button>
			</div>
		);

	const onHandleBusinessRule = async (output={}) => {
		const traceId = createTraceId("business-rule");
		onActionRecord?.({
			traceId,
			phase: "start",
			type: "businessRule",
			action: "invokeBusinessRule",
			elementId: currentElement.BusinessRuleID,
			detail: "Invoke business rule",
		});
		try {
			const res = await TimeDecorator(invokeBusinessRuleAction, "BusinessRule", "invoke/Activity", output)(
				coreURL,
				contractName,
				currentElement.BusinessRuleID,
				instanceId,
			);
			onActionRecord?.({
				traceId,
				phase: "success",
				type: "businessRule",
				action: "invokeBusinessRule",
				elementId: currentElement.BusinessRuleID,
				detail: "Business rule invoked",
				txId: res?.tx,
				payload: res,
			});
			return res;
		} catch (error: any) {
			onActionRecord?.({
				traceId,
				phase: "error",
				type: "businessRule",
				action: "invokeBusinessRule",
				elementId: currentElement.BusinessRuleID,
				detail: "Business rule invoke failed",
				error: String(error?.message || error || "Unknown error"),
			});
			throw error;
		}
	};

	if (type === "businessRule")
		return (
			<div
				style={{
					display: "flex",
					flexDirection: "column",
				}}
			>
				<Button
					style={{ backgroundColor: "mediumspringgreen" }}
					onClick={() => {
						onHandleBusinessRule().catch((error: any) => {
							message.error(error?.message || "Business rule invoke failed");
						});
					}}
				>
					Next
				</Button>
				<TestComponentV2
					processFunc={async (readFromRedis) => {
						const output = {};
						const data = await onHandleBusinessRule(output);
						await sleep(5000);
						const txid = data.tx;
						const invoke_start_time = data.created;
						output["invoke_start_time"] = invoke_start_time;
						const events = await getEventWithTX(coreURL, txid);
						const event_time = events[0].created; 
						output["event_time"] = event_time;

						output["executor_end"] = await readFromRedis("executor_end");
						output["executor_start"] = await readFromRedis("executor_start");
						output["executor_ipfsEnd"] = await readFromRedis("executor_ipfsEnd");
						output["executor_ipfsStart"] = await readFromRedis("executor_ipfsStart");
						output["executor_invokeStart"] = await readFromRedis("executor_invokeStart");
						const executor_op = await readFromRedis("executor_op");
						const operation = await getOperationWithId(coreURL, executor_op);
						const executor_tx = operation.tx;
						const events2 = await getEventWithTX(coreURL, executor_tx);
						output["event_time_2"] =  events2[0].created
						for (const key in output) {
							output[key] = TimeStampHandler(output[key]);
						}
						return output;
					}}
					calcFunc={(time_obj) => {
						// API Invoker, BPMN SC, Event Bus, Executor, IPFS, API Invoker, DMN SC
						const res = [
							{
								"step": "API Invoker",
								"start_time": time_obj["BusinessRule_start_time"],
								"end_time": time_obj["BusinessRule_end_time"],
							},
							{
								"step": "BPMN SC",
								"start_time": time_obj["invoke_start_time"],
								"end_time": time_obj["event_time"],
							},
							{
								"step": "Event Bus",
								"start_time": time_obj["event_time"],
								"end_time": time_obj["executor_start"],
							},
							{
								"step": "Executor",
								"start_time": time_obj["executor_start"],
								"end_time": time_obj["executor_end"],
							},
						    {
								"step": "IPFS",
								"start_time": time_obj["executor_ipfsStart"],
								"end_time": time_obj["executor_ipfsEnd"],
							},
							{
								"step": "API Invoker2",
								"start_time": time_obj["executor_ipfsEnd"],
								"end_time": time_obj["executor_end"],
							},
							{
								"step": "DMN SC",
								"start_time": time_obj["executor_invokeStart"],
								"end_time": time_obj["event_time_2"],
							}
						]
						return res;
					}}
				/>
			</div>
		);

	if (type === "message")
		return (
			<div>
				{showTransactionId ? (
					<div>Transaction ID: {currentElement.FireflyTranID}</div>
				) : null}
				{currentElement.Format && currentElement.Format !== "{}" ? (
						<InputComponentForMessage
							currentElement={currentElement}
							contractName={contractName}
							coreURL={coreURL}
							bpmnName={bpmnName}
							contractMethodDes={contractMethodDes}
							bpmn={bpmn}
							bpmnInstance={bpmnInstance}
						instanceId={instanceId}
						the_identity={identity}
						onActionRecord={onActionRecord}
					/>
				) : null}
			</div>
		);
};

import { useAvailableEthereumIdentity, useAvailableIdentity } from "./hook.ts";

const IdentitySelector = ({ identity, setIdentity }) => {
	// 1. get all membership and participant based on user identity
	const [currentMembership, setCurrentMembership] = useState("");
	const [availableIdentities, isLoading, refetch] = useAvailableIdentity();
	const normalizedIdentities = Array.isArray(availableIdentities)
		? availableIdentities
		: [];

	useEffect(() => {
		if (!currentMembership && normalizedIdentities.length > 0) {
			setCurrentMembership(normalizedIdentities[0].membership_id);
		}
	}, [currentMembership, normalizedIdentities]);

	if (isLoading) {
		return <div>Loading</div>;
	}


	return (
		<div>
			<div>Select Your Identity</div>
			<Button onClick={() => refetch()}>Refresh</Button>
			<Select
				key="membership"
				onChange={(value) => {
					setCurrentMembership(value);
				}}
				value={currentMembership}
				style={{ width: 200 }}
			>
				{normalizedIdentities.map((item) => {
					return (
						<Select.Option key={item.membership_id} value={item.membership_id}>
							{item.membership_name}
						</Select.Option>
					);
				})}
			</Select>
			<Select
				key="identity"
				style={{ width: 200 }}
				value={identity.idInFirefly}
				onChange={async (value) => {
					const the_one = normalizedIdentities
						.find((item) => item.membership_id === currentMembership)
						?.identities.find((item) => item.firefly_identity_id === value);
					if (!the_one) {
						return;
					}
					const identity = await getFireflyIdentity(
						"http://" + the_one.core_url,
						value,
					);

					setIdentity({
						name: the_one.name,
						membership: currentMembership,
						idInFirefly: value,
						core_url: the_one.core_url,
						identity: identity,
						msp: the_one.firefly_msp,
					});
				}}
			>
				{normalizedIdentities
					.find((item) => item.membership_id === currentMembership)
					?.identities.map((item) => {
						return (
							<Select.Option
								key={item.firefly_identity_id}
								value={item.firefly_identity_id}
							>
								{item.name}
							</Select.Option>
						);
					})}
			</Select>
		</div>
	);
};

const EthereumIdentitySelector = ({
	ethEnvironmentId,
	selectedKey,
	onSelect,
}: {
	ethEnvironmentId: string;
	selectedKey: string;
	onSelect: (identity: any) => void;
}) => {
	const [availableIdentities, isLoading, refetch] =
		useAvailableEthereumIdentity(ethEnvironmentId);

	useEffect(() => {
		if (!selectedKey && availableIdentities.length > 0) {
			onSelect(availableIdentities[0]);
		}
	}, [availableIdentities, onSelect, selectedKey]);

	return (
		<div style={{ marginBottom: 12 }}>
			<Space wrap size={12}>
				<Typography.Text strong>Ethereum Signer</Typography.Text>
				<Button size="small" onClick={() => refetch()}>
					Refresh
				</Button>
				<Select
					loading={isLoading}
					style={{ minWidth: 360 }}
					value={selectedKey || undefined}
					placeholder="Select Ethereum identity"
					onChange={(value) => {
						const matched = availableIdentities.find(
							(item: any) => item?.address === value,
						);
						if (matched) {
							onSelect(matched);
						}
					}}
					options={availableIdentities.map((item: any) => ({
						value: item?.address || "",
						label: `${item?.name || "Identity"} (${item?.address || "-"})`,
					}))}
				/>
			</Space>
		</div>
	);
};

const inferEthereumParamType = (param: any) => {
	const raw = String(
		param?.schema?.details?.type ||
			param?.schema?.type ||
			param?.type ||
			param?.internalType ||
			"",
	).toLowerCase();
	if (raw.includes("bool")) return "boolean";
	if (raw.includes("int")) return "number";
	return "string";
};

const getEthereumParamDefaultValue = (
	param: any,
	instanceId: any,
	element?: any,
) => {
	const name = String(param?.name || "");
	const paramType = inferEthereumParamType(param);
	const lowerName = name.toLowerCase();
	const messageFormat = element?.type === "message" ? element?.Format || {} : {};
	const propertyDef =
		messageFormat?.properties?.[name] ||
		messageFormat?.properties?.[lowerName] ||
		messageFormat?.files?.[name] ||
		messageFormat?.files?.[lowerName] ||
		null;

	if (name === "instanceId" || name === "InstanceID") {
		return Number(instanceId || 0);
	}
	if (lowerName.includes("fireflytran")) {
		const elementId = getElementId(element) || "action";
		return `ff-${instanceId || 0}-${elementId}`;
	}
	if (paramType === "boolean") {
		return false;
	}
	if (paramType === "number") {
		return 1;
	}
	if (messageFormat?.files?.[name] || messageFormat?.files?.[lowerName]) {
		return `${name || "file"}.dat`;
	}
	if (lowerName.endsWith("id") || lowerName.includes("requestid")) {
		const elementId = getElementId(element) || "item";
		return `${elementId}-${instanceId || 0}`;
	}
	const description = String(propertyDef?.description || "").trim();
	if (description) {
		return description.length > 40 ? description.slice(0, 40) : description;
	}
	return `sample-${name || "value"}`;
};

const buildEthereumMethodPayload = (method: any, instanceId: any) => {
	const payload: Record<string, any> = {};
	for (const param of method?.params || []) {
		const name = param?.name;
		if (!name) continue;
		payload[name] = getEthereumParamDefaultValue(param, instanceId);
	}
	return payload;
};

const safeParseJsonText = (value: string) => {
	if (!value || typeof value !== "string") return null;
	try {
		return JSON.parse(value);
	} catch {
		return null;
	}
};

const getBpmnDocumentationText = (element: Element) => {
	const docNode = Array.from(element.children).find(
		(child) => child.localName === "documentation",
	);
	return docNode?.textContent?.trim() || "";
};

const parseBpmnExecutionMeta = (bpmnContent?: string) => {
	const meta = {
		messages: {} as Record<string, any>,
		gateways: {} as Record<string, any>,
		events: {} as Record<string, any>,
		businessRules: {} as Record<string, any>,
	};
	if (!bpmnContent || typeof DOMParser === "undefined") {
		return meta;
	}
	try {
		const doc = new DOMParser().parseFromString(bpmnContent, "text/xml");
		const nodes = Array.from(doc.querySelectorAll("[id]"));
		nodes.forEach((node) => {
			const id = node.getAttribute("id") || "";
			if (!id) return;
			const name = node.getAttribute("name") || id;
			const documentation = getBpmnDocumentationText(node);
			const parsedDoc = safeParseJsonText(documentation);
			const entry = {
				id,
				name,
				documentation,
				parsedDoc,
				type: node.localName,
			};
			if (id.startsWith("Message_")) {
				meta.messages[id] = {
					...entry,
					format: parsedDoc,
				};
				return;
			}
			if (id.startsWith("Gateway_")) {
				meta.gateways[id] = entry;
				return;
			}
			if (
				id.startsWith("Event_") ||
				id.startsWith("StartEvent_") ||
				id.startsWith("EndEvent_") ||
				id.startsWith("Intermediate")
			) {
				meta.events[id] = entry;
				return;
			}
			if (id.startsWith("Activity_") && node.localName === "businessRuleTask") {
				meta.businessRules[id] = {
					...entry,
					inputs: Array.isArray(parsedDoc?.inputs) ? parsedDoc.inputs : [],
					outputs: Array.isArray(parsedDoc?.outputs) ? parsedDoc.outputs : [],
				};
			}
		});
	} catch (error) {
		console.error("Failed to parse BPMN execution metadata", error);
	}
	return meta;
};

const getEthereumEnumIds = (methods: any[], executionLayout?: any) => {
	const layoutMessages = Array.isArray(executionLayout?.messages)
		? executionLayout.messages
				.map((item: any) => (typeof item === "string" ? item : item?.id))
				.filter(Boolean)
		: [];
	const layoutGateways = Array.isArray(executionLayout?.gateways)
		? executionLayout.gateways
				.map((item: any) => (typeof item === "string" ? item : item?.id))
				.filter(Boolean)
		: [];
	const layoutEvents = Array.isArray(executionLayout?.events)
		? executionLayout.events
				.map((item: any) => (typeof item === "string" ? item : item?.id))
				.filter(Boolean)
		: [];
	const layoutBusinessRules = Array.isArray(executionLayout?.businessRules)
		? executionLayout.businessRules
				.map((item: any) => (typeof item === "string" ? item : item?.id))
				.filter(Boolean)
		: [];
	const messageIds = layoutMessages.length > 0 ? layoutMessages : methods
		.filter((method: any) => /^Message_.+_Send$/.test(method?.name || ""))
		.map((method: any) => String(method.name).replace(/_Send$/, ""));
	const gatewayIds = layoutGateways.length > 0 ? layoutGateways : methods
		.filter((method: any) => /^Gateway_/.test(method?.name || ""))
		.map((method: any) => String(method.name));
	const eventIds = layoutEvents.length > 0 ? layoutEvents : methods
		.filter((method: any) => /^Event_/.test(method?.name || ""))
		.map((method: any) => String(method.name));
	const businessRuleIds = layoutBusinessRules.length > 0 ? layoutBusinessRules : methods
		.filter(
			(method: any) =>
				/^Activity_/.test(method?.name || "") &&
				!String(method.name).endsWith("_Continue"),
		)
		.map((method: any) => String(method.name));
	return {
		messageIds,
		gatewayIds,
		eventIds,
		businessRuleIds,
	};
};

const normalizeArray = (value: any): any[] => {
	if (Array.isArray(value)) {
		return value;
	}
	if (value == null) {
		return [];
	}
	if (typeof value === "object") {
		if (Array.isArray(value.value)) {
			return value.value;
		}
		if (Array.isArray(value.items)) {
			return value.items;
		}
	}
	return [];
};

const extractSnapshotOutput = (response: any) => {
	const output = response?.output ?? response?.data?.output ?? response?.data ?? response ?? {};
	return {
		messageStates: normalizeArray(
			output?.messageStates ?? output?.MessageStates ?? output?.ret0,
		),
		messageFireflyTranIds: normalizeArray(
			output?.messageFireflyTranIds ??
				output?.MessageFireflyTranIds ??
				output?.ret1,
		),
		gatewayStates: normalizeArray(
			output?.gatewayStates ?? output?.GatewayStates ?? output?.ret2,
		),
		eventStates: normalizeArray(
			output?.eventStates ?? output?.EventStates ?? output?.ret3,
		),
		businessRuleStates: normalizeArray(
			output?.businessRuleStates ?? output?.BusinessRuleStates ?? output?.ret4,
		),
		businessRuleRequestIds: normalizeArray(
			output?.businessRuleRequestIds ??
				output?.BusinessRuleRequestIds ??
				output?.ret5,
		),
	};
};

const toNumericState = (value: any) => {
	if (typeof value === "number") return value;
	if (typeof value === "string" && value !== "") {
		const parsed = Number(value);
		return Number.isNaN(parsed) ? 0 : parsed;
	}
	return 0;
};

const buildEthereumExecutionElements = (
	methods: any[],
	snapshot: ReturnType<typeof extractSnapshotOutput>,
	meta: ReturnType<typeof parseBpmnExecutionMeta>,
	executionLayout?: any,
) => {
	const enumIds = getEthereumEnumIds(methods, executionLayout);
	const messageElements = enumIds.messageIds.map((id, index) => ({
		type: "message",
		MessageID: id,
		DisplayName: meta.messages[id]?.name || id,
		Documentation: meta.messages[id]?.documentation || "",
		Format: meta.messages[id]?.format || null,
		state: toNumericState(snapshot.messageStates[index]),
		FireflyTranID: String(snapshot.messageFireflyTranIds[index] ?? ""),
	}));
	const gatewayElements = enumIds.gatewayIds.map((id, index) => ({
		type: "gateway",
		GatewayID: id,
		DisplayName: meta.gateways[id]?.name || id,
		Documentation: meta.gateways[id]?.documentation || "",
		state: toNumericState(snapshot.gatewayStates[index]),
	}));
	const eventElements = enumIds.eventIds.map((id, index) => ({
		type: "event",
		EventID: id,
		DisplayName: meta.events[id]?.name || id,
		Documentation: meta.events[id]?.documentation || "",
		state: toNumericState(snapshot.eventStates[index]),
	}));
	const businessRuleElements = enumIds.businessRuleIds.map((id, index) => ({
		type: "businessRule",
		BusinessRuleID: id,
		DisplayName: meta.businessRules[id]?.name || id,
		Documentation: meta.businessRules[id]?.documentation || "",
		Inputs: meta.businessRules[id]?.inputs || [],
		Outputs: meta.businessRules[id]?.outputs || [],
		state: toNumericState(snapshot.businessRuleStates[index]),
		RequestID: String(snapshot.businessRuleRequestIds[index] ?? ""),
	}));
	return [
		...messageElements,
		...eventElements,
		...gatewayElements,
		...businessRuleElements,
	];
};

const buildSvgStyleForElements = (
	elementList: any[],
	actionRecords: ActionRecord[],
) => {
	const latestActionStatus = actionRecords.reduce((acc, item) => {
		if (!item.elementId || acc[item.elementId]) return acc;
		acc[item.elementId] = item.status;
		return acc;
	}, {} as Record<string, string>);
	const palette = {
		0: { fill: "#f1f5f9", stroke: "#cbd5e1", opacity: 0.65 },
		1: { fill: "#dbeafe", stroke: "#2563eb", opacity: 0.95 },
		2: { fill: "#fef3c7", stroke: "#d97706", opacity: 0.95 },
		3: { fill: "#dcfce7", stroke: "#16a34a", opacity: 0.95 },
	} as Record<number, { fill: string; stroke: string; opacity: number }>;

	const styles = { "& svg": {} as Record<string, any> };
	elementList.forEach((item) => {
		const elementId = getElementId(item);
		if (!elementId) return;
		const selector = `& g[data-element-id="${elementId}"]`;
		const stateStyle = palette[item.state] || palette[0];
		const actionStyle = item.state === 3 ? undefined : latestActionStatus[elementId];
		const fill =
			actionStyle === "failed"
				? "#fee2e2"
				: actionStyle === "running"
				? "#e0f2fe"
				: stateStyle.fill;
		const stroke =
			actionStyle === "failed"
				? "#dc2626"
				: actionStyle === "running"
				? "#0284c7"
				: stateStyle.stroke;
		styles["& svg"][selector] = {
			"& path, & polygon, & circle, & rect, & ellipse": {
				fill: `${fill} !important`,
				stroke: `${stroke} !important`,
				strokeWidth: actionStyle === "running" ? "3px" : "2px",
				opacity: stateStyle.opacity,
				transition: "all 180ms ease",
				filter:
					actionStyle === "running"
						? "drop-shadow(0 0 8px rgba(14,165,233,0.35))"
						: actionStyle === "failed"
						? "drop-shadow(0 0 8px rgba(220,38,38,0.25))"
						: "none",
				strokeDasharray: actionStyle === "running" ? "5 3" : "none",
			},
			"& text": {
				fontWeight: item.state === 1 || item.state === 2 ? 600 : 500,
			},
		};
	});
	return styles;
};

const getEthereumActionConfig = (
	element: any,
	instanceId: number,
	methodsByName: Record<string, any>,
	actionInputs: Record<string, Record<string, any>>,
) => {
	const hasBusinessRuleRequestId =
		typeof element?.RequestID === "string" &&
		element.RequestID !== "" &&
		element.RequestID !== "0x" &&
		element.RequestID !==
			"0x0000000000000000000000000000000000000000000000000000000000000000";
	if (element?.type === "message" && element?.state === 1) {
		const methodName = `${element.MessageID}_Send`;
		const method = methodsByName[methodName];
		const payload = buildEthereumMethodPayload(method, instanceId);
		const overrides = actionInputs[element.MessageID] || {};
		return {
			type: "message" as const,
			label: "Send",
			method: methodName,
			methodDef: method,
			payload: { ...payload, ...overrides },
		};
	}
	if (element?.type === "gateway" && element?.state === 1) {
		const method = methodsByName[element.GatewayID];
		return {
			type: "gateway" as const,
			label: "Execute",
			method: element.GatewayID,
			methodDef: method,
			payload: {
				...buildEthereumMethodPayload(method, instanceId),
				...(actionInputs[element.GatewayID] || {}),
			},
		};
	}
	if (element?.type === "event" && element?.state === 1) {
		const method = methodsByName[element.EventID];
		return {
			type: "event" as const,
			label: "Execute",
			method: element.EventID,
			methodDef: method,
			payload: {
				...buildEthereumMethodPayload(method, instanceId),
				...(actionInputs[element.EventID] || {}),
			},
		};
	}
	if (element?.type === "businessRule" && element?.state === 1) {
		const method = methodsByName[element.BusinessRuleID];
		return {
			type: "businessRule" as const,
			label: "Request DMN",
			method: element.BusinessRuleID,
			methodDef: method,
			payload: {
				...buildEthereumMethodPayload(method, instanceId),
				...(actionInputs[element.BusinessRuleID] || {}),
			},
		};
	}
	if (element?.type === "businessRule" && element?.state === 2) {
		if (!hasBusinessRuleRequestId) {
			return null;
		}
		const methodName = `${element.BusinessRuleID}_Continue`;
		const method = methodsByName[methodName];
		return {
			type: "businessRule" as const,
			label: "Continue",
			method: methodName,
			methodDef: method,
			payload: {
				...buildEthereumMethodPayload(method, instanceId),
				...(actionInputs[element.BusinessRuleID] || {}),
			},
		};
	}
	return null;
};

const getEthereumActionKey = (element: any, method: string) =>
	`${getElementId(element)}:${method}`;

const buildEthereumActionInputDefaults = (
	element: any,
	config: any,
	instanceId: number,
) => {
	const defaults: Record<string, any> = {};
	for (const param of config?.methodDef?.params || []) {
		const name = param?.name;
		if (!name || name === "instanceId" || name === "InstanceID") {
			continue;
		}
		defaults[name] = getEthereumParamDefaultValue(param, instanceId, element);
	}
	return defaults;
};

const EthereumExecutionView = ({
	bpmnData,
	bpmnInstance,
	contractMethodDes,
	onActionRecord,
	actionRecords = [],
}: {
	bpmnData: any;
	bpmnInstance: any;
	contractMethodDes: any;
	onActionRecord?: (event: ActionRecordEvent) => void;
	actionRecords?: ActionRecord[];
}) => {
	const apiBaseUrl = bpmnData?.firefly_url || "";
	const methods = Array.isArray(contractMethodDes?.methods)
		? contractMethodDes.methods
		: [];
	const ethEnvironmentId = String(bpmnData?.eth_environment || "");
	const methodsByName = useMemo(
		() =>
			methods.reduce((acc, item) => {
				if (item?.name) acc[item.name] = item;
				return acc;
			}, {} as Record<string, any>),
		[methods],
	);
	const executionMeta = useMemo(
		() => parseBpmnExecutionMeta(bpmnData?.bpmnContent),
		[bpmnData?.bpmnContent],
	);
	const executionLayout = bpmnData?.execution_layout || {};
	const instanceId = Number(bpmnInstance?.instance_chaincode_id ?? 0);
	const executableMethods = methods.filter((method: any) => {
		const name = method?.name || "";
		return (
			name.startsWith("Message_") ||
			name.startsWith("Gateway_") ||
			name.startsWith("Event_") ||
			name.startsWith("Activity_")
		);
	});
	const inspectMethods = methods.filter((method: any) => {
		const name = method?.name || "";
		return !(
			name === "createInstance" ||
			name === "initLedger" ||
			name === "setOracle"
		);
	});
	const defaultMethodName =
		executableMethods[0]?.name ||
		inspectMethods[0]?.name ||
		"";
	const [selectedMethod, setSelectedMethod] = useState(defaultMethodName);
	const [payloadText, setPayloadText] = useState("{}");
	const [resultText, setResultText] = useState("");
	const [requestMode, setRequestMode] = useState<"invoke" | "query">("invoke");
	const [running, setRunning] = useState(false);
	const [snapshotLoading, setSnapshotLoading] = useState(false);
	const [snapshotError, setSnapshotError] = useState<string | null>(null);
	const [snapshotElements, setSnapshotElements] = useState<any[]>([]);
	const [actionInputs, setActionInputs] = useState<Record<string, Record<string, any>>>(
		{},
	);
	const [svgStyle, setSvgStyle] = useState({});
	const [selectedEthereumIdentity, setSelectedEthereumIdentity] = useState<any>(null);
	const selectedEthereumKey = selectedEthereumIdentity?.address || "";
	const [pendingActionKeys, setPendingActionKeys] = useState<Record<string, boolean>>(
		{},
	);
	const [autoExecuteEnabled, setAutoExecuteEnabled] = useState(false);
	const [autoExecuteIntervalMs, setAutoExecuteIntervalMs] = useState(3000);
	const [autoExecuteRunning, setAutoExecuteRunning] = useState(false);

	useEffect(() => {
		const method =
			methods.find((item: any) => item?.name === selectedMethod) || null;
		if (!method) {
			setPayloadText("{}");
			return;
		}
		const payload = buildEthereumMethodPayload(
			method,
			bpmnInstance?.instance_chaincode_id,
		);
		setPayloadText(JSON.stringify(payload, null, 2));
	}, [selectedMethod, methods, bpmnInstance?.instance_chaincode_id]);

	useEffect(() => {
		if (!selectedMethod && defaultMethodName) {
			setSelectedMethod(defaultMethodName);
		}
	}, [selectedMethod, defaultMethodName]);

	const refreshSnapshot = async () => {
		if (!apiBaseUrl) {
			setSnapshotError("Execution API is not ready");
			setSnapshotElements([]);
			return [] as any[];
		}
		if (!Number.isFinite(instanceId)) {
			setSnapshotError("Instance id is invalid");
			setSnapshotElements([]);
			return [] as any[];
		}
		setSnapshotLoading(true);
		setSnapshotError(null);
		try {
			const response = await callFireflyContract(
				apiBaseUrl,
				"getExecutionSnapshot",
				{ instanceId },
				"query",
			);
			const snapshot = extractSnapshotOutput(response);
			const elements = buildEthereumExecutionElements(
				methods,
				snapshot,
				executionMeta,
				executionLayout,
			);
			setSnapshotElements(elements);
			return elements;
		} catch (error: any) {
			const errorText = String(error?.message || error || "Snapshot query failed");
			setSnapshotError(errorText);
			setSnapshotElements([]);
			throw error;
		} finally {
			setSnapshotLoading(false);
		}
	};

	useEffect(() => {
		refreshSnapshot();
	}, [apiBaseUrl, instanceId, methods.length, executionMeta, executionLayout]);

	useEffect(() => {
		setSvgStyle(buildSvgStyleForElements(snapshotElements, actionRecords));
	}, [snapshotElements, actionRecords]);

	const stateCounter = snapshotElements.reduce(
		(acc, item) => {
			const state = Number(item?.state ?? 0);
			if (state === 1) acc.ready += 1;
			else if (state === 2) acc.confirm += 1;
			else if (state === 3) acc.done += 1;
			else acc.disabled += 1;
			return acc;
		},
		{ disabled: 0, ready: 0, confirm: 0, done: 0 },
	);
	const actionableElements = snapshotElements.filter((item) =>
		Boolean(getEthereumActionConfig(item, instanceId, methodsByName, actionInputs)),
	);

	useEffect(() => {
		if (snapshotElements.length === 0) {
			return;
		}
		setActionInputs((prev) => {
			let changed = false;
			const next = { ...prev };
			for (const element of snapshotElements) {
				const config = getEthereumActionConfig(
					element,
					instanceId,
					methodsByName,
					prev,
				);
				if (!config) {
					continue;
				}
				const elementId = getElementId(element);
				if (!elementId) {
					continue;
				}
				const current = { ...(next[elementId] || {}) };
				const defaults = buildEthereumActionInputDefaults(
					element,
					config,
					instanceId,
				);
				for (const [name, value] of Object.entries(defaults)) {
					if (
						current[name] === undefined ||
						current[name] === null ||
						current[name] === ""
					) {
						current[name] = value;
						changed = true;
					}
				}
				next[elementId] = current;
			}
			return changed ? next : prev;
		});
	}, [snapshotElements, instanceId, methodsByName]);

	const invokeElementAction = async (element: any) => {
		const config = getEthereumActionConfig(
			element,
			instanceId,
			methodsByName,
			actionInputs,
		);
		if (!config) {
			message.info("No executable action for current state");
			return false;
		}
		if (!selectedEthereumKey) {
			message.error("Select an Ethereum signer first");
			return false;
		}
		const actionKey = getEthereumActionKey(element, config.method);
		if (pendingActionKeys[actionKey]) {
			message.info("This action is already pending");
			return false;
		}
		try {
			const latestElements = await refreshSnapshot();
			const latestElement = latestElements.find(
				(item: any) => getElementId(item) === getElementId(element),
			);
			const latestConfig = latestElement
				? getEthereumActionConfig(
						latestElement,
						instanceId,
						methodsByName,
						actionInputs,
				  )
				: null;
			if (!latestConfig || latestConfig.method !== config.method) {
				message.warning("Element is no longer actionable. Snapshot has been refreshed.");
				return false;
			}
		} catch {
			message.error("Failed to refresh execution snapshot before invoke");
			return false;
		}
		setPendingActionKeys((prev) => ({ ...prev, [actionKey]: true }));
		const traceId = createTraceId(`eth-${config.type}`);
		onActionRecord?.({
			traceId,
			phase: "start",
			type: config.type,
			action: config.method,
			elementId: getElementId(element),
			detail: `${config.label} started`,
			payload: config.payload,
		});
		try {
			const response = await callFireflyContract(
				apiBaseUrl,
				config.method,
				config.payload,
				"invoke",
				selectedEthereumKey,
			);
			setResultText(JSON.stringify(response, null, 2));
			onActionRecord?.({
				traceId,
				phase: "success",
				type: config.type,
				action: config.method,
				elementId: getElementId(element),
				detail: `${config.label} success`,
				payload: response,
				txId: response?.tx,
			});
			await refreshSnapshot();
			message.success(`${config.label} success`);
			return true;
		} catch (error: any) {
			const errorText = String(error?.message || error || "Action failed");
			setResultText(errorText);
			onActionRecord?.({
				traceId,
				phase: "error",
				type: config.type,
				action: config.method,
				elementId: getElementId(element),
				detail: `${config.label} failed`,
				error: errorText,
			});
			message.error(errorText);
			return false;
		} finally {
			setPendingActionKeys((prev) => {
				const next = { ...prev };
				delete next[actionKey];
				return next;
			});
		}
	};

	useEffect(() => {
		if (!autoExecuteEnabled) {
			setAutoExecuteRunning(false);
			return;
		}
		if (!selectedEthereumKey) {
			return;
		}
		if (snapshotLoading || running || autoExecuteRunning) {
			return;
		}
		if (Object.keys(pendingActionKeys).length > 0) {
			return;
		}
		const nextElement = actionableElements[0];
		if (!nextElement) {
			return;
		}
		const timer = window.setTimeout(async () => {
			setAutoExecuteRunning(true);
			try {
				const ok = await invokeElementAction(nextElement);
				if (!ok) {
					setAutoExecuteEnabled(false);
				}
			} finally {
				setAutoExecuteRunning(false);
			}
		}, autoExecuteIntervalMs);
		return () => {
			window.clearTimeout(timer);
		};
	}, [
		autoExecuteEnabled,
		autoExecuteIntervalMs,
		selectedEthereumKey,
		snapshotLoading,
		running,
		autoExecuteRunning,
		pendingActionKeys,
		actionableElements,
	]);

	useEffect(() => {
		if (!autoExecuteEnabled || !selectedEthereumKey || !apiBaseUrl) {
			return;
		}
		if (!Number.isFinite(instanceId)) {
			return;
		}
		const loop = window.setInterval(() => {
			if (snapshotLoading || running || autoExecuteRunning) {
				return;
			}
			refreshSnapshot().catch(() => {
				// refreshSnapshot already records snapshotError; keep auto polling alive
			});
		}, document.visibilityState === "visible"
			? autoExecuteIntervalMs
			: Math.max(autoExecuteIntervalMs, 15000));
		return () => {
			window.clearInterval(loop);
		};
	}, [
		autoExecuteEnabled,
		selectedEthereumKey,
		apiBaseUrl,
		instanceId,
		autoExecuteIntervalMs,
		snapshotLoading,
		running,
		autoExecuteRunning,
	]);

	const invokeMethod = async () => {
		if (!apiBaseUrl || !selectedMethod) {
			message.error("Execution API is not ready");
			return;
		}
		if (requestMode === "invoke" && !selectedEthereumKey) {
			message.error("Select an Ethereum signer first");
			return;
		}
		let payload: Record<string, any> = {};
		try {
			payload = payloadText.trim() ? JSON.parse(payloadText) : {};
		} catch (error) {
			message.error("Payload JSON is invalid");
			return;
		}
		const traceId = createTraceId(`eth-${requestMode}`);
		onActionRecord?.({
			traceId,
			phase: "start",
			type: "message",
			action: selectedMethod,
			elementId: selectedMethod,
			detail: `Ethereum ${requestMode}`,
			payload,
		});
		setRunning(true);
		try {
			const response = await callFireflyContract(
				apiBaseUrl,
				selectedMethod,
				payload,
				requestMode,
				requestMode === "invoke" ? selectedEthereumKey : undefined,
			);
			setResultText(JSON.stringify(response, null, 2));
			onActionRecord?.({
				traceId,
				phase: "success",
				type: "message",
				action: selectedMethod,
				elementId: selectedMethod,
				detail: `Ethereum ${requestMode} success`,
				payload: response,
				txId: response?.tx,
			});
			message.success(`${requestMode} ${selectedMethod} success`);
		} catch (error: any) {
			const errorText = String(error?.message || error || "Unknown error");
			setResultText(errorText);
			onActionRecord?.({
				traceId,
				phase: "error",
				type: "message",
				action: selectedMethod,
				elementId: selectedMethod,
				detail: `Ethereum ${requestMode} failed`,
				error: errorText,
			});
			message.error(errorText);
		} finally {
			setRunning(false);
		}
	};

	return (
		<div>
			<Alert
				type="info"
				showIcon
				message="Ethereum Execution"
				description="This page uses the BPMN's registered FireFly API directly. State is rendered from getExecutionSnapshot(instanceId)."
				style={{ marginBottom: 12 }}
			/>
			<EthereumIdentitySelector
				ethEnvironmentId={ethEnvironmentId}
				selectedKey={selectedEthereumKey}
				onSelect={setSelectedEthereumIdentity}
			/>
			{!selectedEthereumKey ? (
				<Alert
					type="warning"
					showIcon
					message="No Ethereum signer selected"
					description="Invoke actions use the selected Ethereum identity address as FireFly key. Without it, participant checks will revert."
					style={{ marginBottom: 12 }}
				/>
			) : (
				<Alert
					type="success"
					showIcon
					message="Ethereum signer ready"
					description={`Current signer: ${selectedEthereumIdentity?.name || "Identity"} (${selectedEthereumKey})`}
					style={{ marginBottom: 12 }}
				/>
			)}
			<div
				style={{
					display: "flex",
					flexWrap: "wrap",
					gap: 12,
					marginBottom: 12,
				}}
			>
				<Tag color="blue">Instance: {bpmnInstance?.instance_chaincode_id ?? "-"}</Tag>
				<Tag color="purple">API: {apiBaseUrl || "-"}</Tag>
				<Tag color="cyan">Methods: {methods.length}</Tag>
				<Tag color="processing">Ready: {stateCounter.ready}</Tag>
				<Tag color="orange">Waiting: {stateCounter.confirm}</Tag>
				<Tag color="success">Done: {stateCounter.done}</Tag>
				<Tag color="default">Disabled: {stateCounter.disabled}</Tag>
				<Tag color="geekblue">Actionable: {actionableElements.length}</Tag>
				<Tag color={autoExecuteEnabled ? "green" : "default"}>
					Auto Execute: {autoExecuteEnabled ? "ON" : "OFF"}
				</Tag>
				<Button size="small" loading={snapshotLoading} onClick={refreshSnapshot}>
					Refresh Snapshot
				</Button>
			</div>
			<div
				style={{
					display: "flex",
					flexWrap: "wrap",
					gap: 12,
					marginBottom: 12,
					alignItems: "center",
				}}
			>
				<Switch
					checked={autoExecuteEnabled}
					onChange={setAutoExecuteEnabled}
					checkedChildren="Auto Execute"
					unCheckedChildren="Manual"
					disabled={!selectedEthereumKey}
				/>
				<Select
					value={autoExecuteIntervalMs}
					style={{ width: 180 }}
					onChange={(value) => setAutoExecuteIntervalMs(value)}
					options={[
						{ label: "1s interval", value: 1000 },
						{ label: "2s interval", value: 2000 },
						{ label: "3s interval", value: 3000 },
						{ label: "5s interval", value: 5000 },
					]}
					disabled={!selectedEthereumKey}
				/>
				<Typography.Text type="secondary">
					Auto mode executes the first actionable element with current default parameters and selected signer.
				</Typography.Text>
			</div>
			{snapshotError ? (
				<Alert
					type="warning"
					showIcon
					message="Snapshot query failed"
					description={snapshotError}
					style={{ marginBottom: 12 }}
				/>
			) : null}
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "minmax(320px, 420px) 1fr",
					gap: 16,
					alignItems: "start",
				}}
			>
				<div
					style={{
						padding: 12,
						border: "1px solid #e2e8f0",
						borderRadius: 10,
						background: "#fff",
					}}
				>
					<Space direction="vertical" style={{ width: "100%" }} size={12}>
						<div>
							<Typography.Text strong>Actionable Elements</Typography.Text>
							<div style={{ marginTop: 8, display: "grid", gap: 10 }}>
								{actionableElements.length === 0 ? (
									<Typography.Text type="secondary">
										No actionable element in current snapshot.
									</Typography.Text>
								) : (
									actionableElements.map((element) => {
										const config = getEthereumActionConfig(
											element,
											instanceId,
											methodsByName,
											actionInputs,
										);
										if (!config) return null;
										const elementId = getElementId(element);
										const actionKey = getEthereumActionKey(
											element,
											config.method,
										);
										const isPending = Boolean(pendingActionKeys[actionKey]);
										const editableParams = (config.methodDef?.params || []).filter(
											(param: any) =>
												param?.name &&
												param.name !== "instanceId" &&
												param.name !== "InstanceID",
										);
										return (
											<div
												key={`${element.type}-${elementId}`}
												style={{
													padding: 10,
													border: "1px solid #e2e8f0",
													borderRadius: 8,
													background: "#f8fafc",
												}}
												>
													<Space wrap size={8}>
														<Tag color="blue">{element.type}</Tag>
														<Tag color="purple">{element.state}</Tag>
														<Typography.Text strong>
															{element.DisplayName || elementId}
														</Typography.Text>
														{element.DisplayName &&
														element.DisplayName !== elementId ? (
															<Tag>{elementId}</Tag>
														) : null}
													</Space>
												{element.Documentation ? (
													<div style={{ marginTop: 8 }}>
														<Typography.Text type="secondary">
															{element.Documentation}
														</Typography.Text>
													</div>
												) : null}
												{element.type === "message" &&
												element.Format &&
												typeof element.Format === "object" ? (
													<div style={{ marginTop: 8 }}>
														<Typography.Text type="secondary">
															Message Schema
														</Typography.Text>
														<div style={{ marginTop: 4, display: "flex", flexWrap: "wrap", gap: 6 }}>
															{Object.keys(element.Format?.properties || {}).map((key) => (
																<Tag key={key} color="geekblue">
																	{key}:{String(
																		element.Format.properties?.[key]?.type || "string",
																	)}
																</Tag>
															))}
															{Object.keys(element.Format?.files || {}).map((key) => (
																<Tag key={key} color="purple">
																	file:{key}
																</Tag>
															))}
														</div>
													</div>
												) : null}
												{element.type === "businessRule" &&
												(Array.isArray(element.Inputs) || Array.isArray(element.Outputs)) ? (
													<div style={{ marginTop: 8, display: "grid", gap: 4 }}>
														{Array.isArray(element.Inputs) && element.Inputs.length > 0 ? (
															<Typography.Text type="secondary">
																Inputs: {element.Inputs.map((item: any) => item?.name || item).join(", ")}
															</Typography.Text>
														) : null}
														{Array.isArray(element.Outputs) && element.Outputs.length > 0 ? (
															<Typography.Text type="secondary">
																Outputs: {element.Outputs.map((item: any) => item?.name || item).join(", ")}
															</Typography.Text>
														) : null}
													</div>
												) : null}
												{editableParams.map((param: any) => {
													const name = param.name;
													const paramType = inferEthereumParamType(param);
													const currentValue =
														actionInputs[elementId]?.[name] ??
														config.payload?.[name] ??
														"";
													return (
														<div key={`${elementId}-${name}`} style={{ marginTop: 8 }}>
															<Typography.Text type="secondary">
																{name}
															</Typography.Text>
															{paramType === "boolean" ? (
																<div style={{ marginTop: 4 }}>
																	<Switch
																		checked={Boolean(currentValue)}
																		onChange={(checked) =>
																			setActionInputs((prev) => ({
																				...prev,
																				[elementId]: {
																					...(prev[elementId] || {}),
																					[name]: checked,
																				},
																			}))
																		}
																	/>
																</div>
															) : (
																<Input
																	style={{ marginTop: 4 }}
																	type={paramType === "number" ? "number" : "text"}
																	value={String(currentValue ?? "")}
																	onChange={(event) =>
																		setActionInputs((prev) => ({
																			...prev,
																			[elementId]: {
																				...(prev[elementId] || {}),
																				[name]:
																					paramType === "number"
																						? Number(event.target.value || 0)
																						: event.target.value,
																			},
																		}))
																	}
																/>
															)}
														</div>
													);
												})}
												{element.type === "businessRule" && element.RequestID ? (
													<div style={{ marginTop: 8 }}>
														<Typography.Text type="secondary">
															RequestID: {element.RequestID}
														</Typography.Text>
													</div>
												) : null}
												{element.type === "businessRule" &&
												element.state === 2 &&
												(!element.RequestID ||
													element.RequestID === "0x" ||
													element.RequestID ===
														"0x0000000000000000000000000000000000000000000000000000000000000000") ? (
													<div style={{ marginTop: 8 }}>
														<Typography.Text type="secondary">
															Waiting for off-chain worker to bind DMN requestId.
														</Typography.Text>
													</div>
												) : null}
												<Button
													style={{ marginTop: 8 }}
													type="primary"
													loading={isPending}
													disabled={isPending}
													onClick={() => invokeElementAction(element)}
												>
													{config.label}
												</Button>
											</div>
										);
									})
								)}
							</div>
						</div>
						<div>
							<Typography.Text type="secondary">Advanced Action Method</Typography.Text>
							<Select
								style={{ width: "100%", marginTop: 4 }}
								value={selectedMethod}
								onChange={setSelectedMethod}
								options={executableMethods.map((item: any) => ({
									label: item.name,
									value: item.name,
								}))}
							/>
						</div>
						<div>
							<Typography.Text type="secondary">Advanced Inspect Method</Typography.Text>
							<Select
								style={{ width: "100%", marginTop: 4 }}
								value={selectedMethod}
								onChange={(value) => {
									setRequestMode("query");
									setSelectedMethod(value);
								}}
								options={inspectMethods.map((item: any) => ({
									label: item.name,
									value: item.name,
								}))}
							/>
						</div>
						<div>
							<Typography.Text type="secondary">Advanced Mode</Typography.Text>
							<Select
								style={{ width: "100%", marginTop: 4 }}
								value={requestMode}
								onChange={(value) => setRequestMode(value)}
								options={[
									{ label: "Invoke", value: "invoke" },
									{ label: "Query", value: "query" },
								]}
							/>
						</div>
						<div>
							<Typography.Text type="secondary">Advanced Payload JSON</Typography.Text>
							<Input.TextArea
								value={payloadText}
								onChange={(event) => setPayloadText(event.target.value)}
								autoSize={{ minRows: 12, maxRows: 24 }}
								style={{ marginTop: 4, fontFamily: "monospace" }}
							/>
						</div>
						<Button type="default" loading={running} onClick={invokeMethod}>
							Run
						</Button>
					</Space>
				</div>
				<div>
					<div
						style={{
							padding: 12,
							border: "1px solid #e2e8f0",
							borderRadius: 10,
							background: "#fff",
							marginBottom: 12,
						}}
					>
						<Typography.Text strong>BPMN Diagram</Typography.Text>
						<div
							style={{ marginTop: 12 }}
							className={css(svgStyle)}
							dangerouslySetInnerHTML={{ __html: bpmnData?.svgContent || "" }}
						/>
					</div>
					<div
						style={{
							padding: 12,
							border: "1px solid #e2e8f0",
							borderRadius: 10,
							background: "#fff",
						}}
					>
						<Typography.Text strong>Result</Typography.Text>
						<pre
							style={{
								marginTop: 8,
								maxHeight: 420,
								overflow: "auto",
								background: "#0f172a",
								color: "#e2e8f0",
								padding: 12,
								borderRadius: 8,
							}}
						>
							{resultText || "No result yet"}
						</pre>
					</div>
				</div>
			</div>
		</div>
	);
};

import { useAllFireflyData } from "./hook";
import axios from "axios";

const ExecutionPage = (props) => {
	const bpmnInstanceId = window.location.pathname.split("/").pop();
	const location = useLocation();

	// 1. get BPMN Content by bpmnInstanceId
	// 2. get BPMN Detail by bpmnId
	// 3. get all available Membership and it's identity to choose

	const [identity, setIdentity] = useState({
		name: "",
		membership: "",
		idInFirefly: "",
		core_url: "",
		identity: "",
	});
	const [autoRefresh, setAutoRefresh] = useState(true);
	const [refreshIntervalMs, setRefreshIntervalMs] = useState(5000);
	const [isRefreshing, setIsRefreshing] = useState(false);
	const [lastManualRefreshAt, setLastManualRefreshAt] = useState<string | null>(null);
	const [actionRecords, setActionRecords] = useState<ActionRecord[]>([]);
	const [executionMode, setExecutionMode] = useState<ExecutionMode>(() => {
		const mode = new URLSearchParams(window.location.search).get("mode");
		return mode === "mock" ? "mock" : "real";
	});
	const [mockElements, setMockElements] = useState<any[]>([]);
	const [mockProcessingElementId, setMockProcessingElementId] = useState<string>("");
	const [mockAutoRunning, setMockAutoRunning] = useState(false);
	const [mockFailureRate, setMockFailureRate] = useState(0);
	const [mockDelayRange, setMockDelayRange] = useState<[number, number]>([300, 900]);
	const [mockForceFailElements, setMockForceFailElements] = useState<string[]>([]);
	const mockElementsRef = useRef<any[]>([]);
	const [actionElementFilter, setActionElementFilter] = useState<string>("ALL");
	const [autoScrollTimeline, setAutoScrollTimeline] = useState(true);
	const timelineRef = useRef<HTMLDivElement | null>(null);
	const [bpmnInstance, bpmnInstanceReady, syncBpmnInstance] =
		useBPMNIntanceDetailData(bpmnInstanceId);
	const [bpmnData, bpmnReady, syncBpmn] = useBPMNDetailData(bpmnInstance.bpmn);

	const contractMethodDes = JSON.parse(bpmnReady ? bpmnData.ffiContent : "{ }");

	const svgRef = useRef(null);
	const [svgContent, setSvgContent] = useState(null);
	const [svgStyle, setSvgStyle] = useState({});

	useEffect(() => {
		// set content to svgRef element
		if (svgRef.current && bpmnReady) {
			svgRef.current.innerHTML = bpmnData.svgContent;
		}
		return () => {
			// cleanup
		};
	}, [bpmnInstanceId, svgRef.current, bpmnReady]);

	const isEthereumBpmn = Boolean(bpmnData?.eth_environment || bpmnData?.ethereum_contract);
	const contractName = bpmnReady
		? isEthereumBpmn
			? bpmnData?.firefly_url?.split("/apis/")?.[1] || ""
			: bpmnData?.chaincode?.name && bpmnData?.chaincode?.id
				? `${bpmnData.chaincode.name}-${bpmnData.chaincode.id.substring(0, 6)}`
				: ""
		: "";
	const full_core_url = isEthereumBpmn
		? bpmnData?.firefly_url
			? bpmnData.firefly_url.split("/api/v1/namespaces/default/apis/")[0]
			: "http://"
		: "http://" + identity.core_url;
	const [
		allEvents,
		allGateways,
		allMessages,
		allBusinessRules,
		fireflyDataReady,
		syncFireflyData,
		fireflyMeta,
	] = useAllFireflyData(
		full_core_url,
		contractName,
		bpmnInstance.instance_chaincode_id,
		!isEthereumBpmn,
	);
	const realElements = [
		...allMessages,
		...allEvents,
		...allGateways,
		...allBusinessRules,
	];
	const executionElements = executionMode === "mock" ? mockElements : realElements;
	const stateCounter = executionElements.reduce(
		(acc, item) => {
			const state = Number(item?.state ?? 0);
			if (state === 1) acc.ready += 1;
			else if (state === 2) acc.confirm += 1;
			else if (state === 3) acc.done += 1;
			else acc.disabled += 1;
			return acc;
		},
		{ disabled: 0, ready: 0, confirm: 0, done: 0 },
	);
	const currentElements = [
		...executionElements,
	].filter((msg) => {
		return msg.state === 1 || msg.state === 2;
	});
	const mockElementOptions = executionElements.reduce((acc, item) => {
		const id = getElementId(item);
		if (!id) return acc;
		acc.push({
			label: `${item.type}:${id}`,
			value: id,
		});
		return acc;
	}, [] as Array<{ label: string; value: string }>);
	const mockDonePercent = executionElements.length
		? Math.round((stateCounter.done / executionElements.length) * 100)
		: 0;
	const actionCounter = actionRecords.reduce(
		(acc, item) => {
			if (item.status === "running") acc.running += 1;
			else if (item.status === "success") acc.success += 1;
			else acc.failed += 1;
			return acc;
		},
		{ running: 0, success: 0, failed: 0 },
	);
	const actionElementOptions = [
		{ label: "All elements", value: "ALL" },
		...Array.from(new Set(actionRecords.map((item) => item.elementId).filter(Boolean))).map((item) => ({
			label: item,
			value: item,
		})),
	];
	const filteredActionRecords =
		actionElementFilter === "ALL"
			? actionRecords
			: actionRecords.filter((item) => item.elementId === actionElementFilter);
	const latestAction = filteredActionRecords.length > 0 ? filteredActionRecords[0] : null;

	const copyToClipboard = async (value: string, label: string) => {
		if (!value) return;
		try {
			if (navigator?.clipboard?.writeText) {
				await navigator.clipboard.writeText(value);
			} else {
				throw new Error("Clipboard API unavailable");
			}
			message.success(`${label} copied`);
		} catch (error) {
			message.error(`Failed to copy ${label}`);
		}
	};

	const onActionRecord = (event: ActionRecordEvent) => {
		const timestamp = event.timestamp || new Date().toISOString();
		setActionRecords((prev) => {
			const idx = prev.findIndex((item) => item.traceId === event.traceId);
			const current = idx >= 0 ? prev[idx] : null;
			const nextRecord: ActionRecord = {
				traceId: event.traceId,
				type: event.type,
				action: event.action,
				elementId: event.elementId,
				status:
					event.phase === "start"
						? "running"
						: event.phase === "success"
						? "success"
						: "failed",
				startedAt: current?.startedAt || timestamp,
				endedAt:
					event.phase === "start"
						? current?.endedAt || null
						: timestamp,
				detail: event.detail || current?.detail || "",
				txId: event.txId || current?.txId,
				fireflyId: event.fireflyId || current?.fireflyId,
				error: event.phase === "error"
					? event.error || current?.error || "Unknown error"
					: current?.error,
				payload: event.payload || current?.payload,
			};
			if (idx === -1) {
				return [nextRecord, ...prev].slice(0, 40);
			}
			const next = [...prev];
			next[idx] = nextRecord;
			next.sort((a, b) => {
				return new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime();
			});
			return next.slice(0, 40);
		});
	};

	const resetMockElements = () => {
		const parsed = parseMockElementsFromSvg(bpmnData?.svgContent);
		setMockElements(parsed);
		setMockProcessingElementId("");
	};

	const getNextMockActionable = (): {
		element: any;
		op: "execute" | "confirm";
	} | null => {
		const actionable = mockElementsRef.current.find(
			(item) => item.state === 1 || item.state === 2,
		);
		if (!actionable) return null;
		const op =
			actionable.type === "message" && actionable.state === 2
				? "confirm"
				: "execute";
		return { element: actionable, op };
	};

	const runMockAction = async (
		element: any,
		op: "execute" | "confirm",
	): Promise<boolean> => {
		const elementId = getElementId(element);
		if (!elementId) return false;
		const traceId = createTraceId("mock");
		setMockProcessingElementId(elementId);
		const [delayMin, delayMax] = mockDelayRange;
		const normalizedMin = Math.max(0, Math.min(delayMin, delayMax));
		const normalizedMax = Math.max(0, Math.max(delayMin, delayMax));
		const delayMs =
			normalizedMin === normalizedMax
				? normalizedMin
				: normalizedMin +
				  Math.round(Math.random() * (normalizedMax - normalizedMin));
		const injectedFail =
			mockForceFailElements.includes(elementId) ||
			Math.random() < mockFailureRate / 100;
		onActionRecord({
			traceId,
			phase: "start",
			type: element.type as ActionKind,
			action: op === "confirm" ? "mockConfirm" : "mockExecute",
			elementId,
			detail: `Mock ${op} started (delay=${delayMs}ms)`,
		});
		try {
			await sleep(delayMs);
			if (injectedFail) {
				throw new Error(
					mockForceFailElements.includes(elementId)
						? "Mock forced failure"
						: `Mock random failure (${mockFailureRate}%)`,
				);
			}
			setMockElements((prev) => {
				const idx = prev.findIndex((item) => getElementId(item) === elementId);
				if (idx < 0) return prev;
				const next = prev.map((item) => ({ ...item }));
				const current = next[idx];
				if (current.type === "message" && current.state === 1 && op === "execute") {
					current.state = 2;
					return next;
				}
				current.state = 3;
				let nextIdx = next.findIndex((item, index) => index > idx && item.state === 0);
				if (nextIdx < 0) {
					nextIdx = next.findIndex((item) => item.state === 0);
				}
				if (nextIdx >= 0) {
					next[nextIdx].state = 1;
				}
				return next;
			});
			onActionRecord({
				traceId,
				phase: "success",
				type: element.type as ActionKind,
				action: op === "confirm" ? "mockConfirm" : "mockExecute",
				elementId,
				detail: `Mock ${op} completed`,
				payload: {
					mode: "mock",
					op,
					elementId,
					delayMs,
				},
			});
			return true;
		} catch (error: any) {
			onActionRecord({
				traceId,
				phase: "error",
				type: element.type as ActionKind,
				action: op === "confirm" ? "mockConfirm" : "mockExecute",
				elementId,
				detail: `Mock ${op} failed`,
				error: String(error?.message || error || "Unknown error"),
			});
			return false;
		} finally {
			setMockProcessingElementId("");
		}
	};

	const runMockNextStep = async () => {
		const next = getNextMockActionable();
		if (!next) {
			message.info("No actionable element in mock mode");
			return;
		}
		await runMockAction(next.element, next.op);
	};

	const runMockAutoDemo = async () => {
		if (mockAutoRunning) return;
		setMockAutoRunning(true);
		try {
			let guard = 0;
			let consecutiveFailures = 0;
			while (guard < 200) {
				guard += 1;
				const next = getNextMockActionable();
				if (!next) break;
				const ok = await runMockAction(next.element, next.op);
				if (ok) {
					consecutiveFailures = 0;
				} else {
					consecutiveFailures += 1;
					if (consecutiveFailures >= 5) {
						message.warning("Auto demo stopped after consecutive failures");
						break;
					}
				}
				await sleep(220);
			}
		} finally {
			setMockAutoRunning(false);
		}
	};

	useEffect(() => {
		mockElementsRef.current = mockElements;
		setMockForceFailElements((prev) => {
			const allowed = new Set(mockElements.map((item) => getElementId(item)));
			return prev.filter((id) => allowed.has(id));
		});
	}, [mockElements]);

	useEffect(() => {
		if (executionMode !== "mock") return;
		resetMockElements();
		setActionRecords([]);
	}, [executionMode, bpmnData?.svgContent]);

	useEffect(() => {
		const mode = new URLSearchParams(location.search).get("mode");
		if (mode === "mock") {
			setExecutionMode("mock");
		} else if (mode === "real") {
			setExecutionMode("real");
		}
	}, [location.search]);

	useEffect(() => {
		if (executionMode === "mock") return;
		setMockAutoRunning(false);
		setMockProcessingElementId("");
	}, [executionMode]);

	const renderSvg = () => {
		const elementList =
			executionMode === "mock"
				? mockElements
				: [...allMessages, ...allEvents, ...allGateways, ...allBusinessRules];
		const latestActionStatus = actionRecords.reduce((acc, item) => {
			if (!item.elementId || acc[item.elementId]) return acc;
			acc[item.elementId] = item.status;
			return acc;
		}, {} as Record<string, string>);
		const palette = {
			0: { fill: "#f1f5f9", stroke: "#cbd5e1", opacity: 0.65 },
			1: { fill: "#dbeafe", stroke: "#2563eb", opacity: 0.95 },
			2: { fill: "#fef3c7", stroke: "#d97706", opacity: 0.95 },
			3: { fill: "#dcfce7", stroke: "#16a34a", opacity: 0.95 },
		} as Record<number, { fill: string; stroke: string; opacity: number }>;

		const generateStylesWithMsgList = (msgList) => {
			const styles = { "& svg": {} as Record<string, any> };
			msgList.forEach((msg) => {
				const elementId = getElementId(msg);
				if (!elementId) return;
				const selector = `& g[data-element-id="${elementId}"]`;
				const stateStyle = palette[msg.state] || palette[0];
				const actionStyle = msg.state === 3 ? undefined : latestActionStatus[elementId];
				const fill =
					actionStyle === "failed"
						? "#fee2e2"
						: actionStyle === "running"
						? "#e0f2fe"
						: stateStyle.fill;
				const stroke =
					actionStyle === "failed"
						? "#dc2626"
						: actionStyle === "running"
						? "#0284c7"
						: stateStyle.stroke;
				styles["& svg"][selector] = {
					"& path, & polygon, & circle, & rect, & ellipse": {
						fill: `${fill} !important`,
						stroke: `${stroke} !important`,
						strokeWidth: actionStyle === "running" ? "3px" : "2px",
						opacity: stateStyle.opacity,
						transition: "all 180ms ease",
						filter:
							actionStyle === "running"
								? "drop-shadow(0 0 8px rgba(14,165,233,0.35))"
								: actionStyle === "failed"
								? "drop-shadow(0 0 8px rgba(220,38,38,0.25))"
								: "none",
						strokeDasharray: actionStyle === "running" ? "5 3" : "none",
					},
					"& text": {
						fontWeight: msg.state === 1 || msg.state === 2 ? 600 : 500,
					},
				};
			});
			return styles;
		};
		const newStyles = generateStylesWithMsgList(elementList);
		setSvgStyle(newStyles);
	};

	useEffect(() => {
		renderSvg();
	}, [fireflyDataReady, executionMode, mockElements, actionRecords.length]);

	useEffect(() => {
		if (fireflyDataReady) {
			setIsRefreshing(false);
		}
	}, [fireflyDataReady]);

	useEffect(() => {
		if (!autoScrollTimeline) return;
		if (!timelineRef.current) return;
		timelineRef.current.scrollTo({ top: 0, behavior: "smooth" });
	}, [actionRecords.length, autoScrollTimeline]);

	useEffect(() => {
		if (
			executionMode !== "real" ||
			!autoRefresh ||
			!full_core_url ||
			full_core_url === "http://"
		) {
			return;
		}
		const loop = window.setInterval(() => {
			setIsRefreshing(true);
			syncFireflyData();
		}, document.visibilityState === "visible" ? refreshIntervalMs : Math.max(refreshIntervalMs, 15000));
		return () => {
			window.clearInterval(loop);
		};
	}, [executionMode, autoRefresh, full_core_url, refreshIntervalMs]);

	// useEffect(() => {
	//     const task = setInterval(() => {
	//         syncFireflyData();
	//     }, 3000);
	//     return () => {
	//         clearInterval(task);
	//     }
	// }
	//     , []);

	if (bpmnReady && isEthereumBpmn) {
		return (
			<EthereumExecutionView
				bpmnData={bpmnData}
				bpmnInstance={bpmnInstance}
				contractMethodDes={contractMethodDes}
				onActionRecord={onActionRecord}
				actionRecords={actionRecords}
			/>
		);
	}

	return (
		<div className="Execution">
			<div
				style={{
					marginTop: 12,
					marginBottom: 12,
					padding: 12,
					border: "1px solid #e2e8f0",
					borderRadius: 10,
					background: "#ffffff",
				}}
			>
				<Space wrap size={12}>
					<Typography.Text strong>Execution Mode</Typography.Text>
					<Switch
						checked={executionMode === "mock"}
						onChange={(checked) => setExecutionMode(checked ? "mock" : "real")}
						checkedChildren="Mock"
						unCheckedChildren="Real"
					/>
					<Tag color={executionMode === "mock" ? "gold" : "green"}>
						{executionMode === "mock" ? "MOCK EXECUTION" : "REAL EXECUTION"}
					</Tag>
					{executionMode === "mock" ? (
						<>
							<Button onClick={resetMockElements}>Reset Scenario</Button>
							<Button onClick={runMockNextStep}>Run Next Step</Button>
							<Button loading={mockAutoRunning} type="primary" onClick={runMockAutoDemo}>
								Run Auto Demo
							</Button>
						</>
					) : null}
				</Space>
				{executionMode === "mock" ? (
					<div
						style={{
							marginTop: 10,
							padding: 10,
							border: "1px dashed #cbd5e1",
							borderRadius: 8,
							background: "#f8fafc",
						}}
					>
						<Space wrap size={16} align="start">
							<div style={{ minWidth: 260 }}>
								<Typography.Text type="secondary">
									Failure Rate: {mockFailureRate}%
								</Typography.Text>
								<Slider
									min={0}
									max={100}
									value={mockFailureRate}
									onChange={(value) => setMockFailureRate(Number(value))}
								/>
							</div>
							<div style={{ minWidth: 320 }}>
								<Typography.Text type="secondary">
									Delay Range (ms): {mockDelayRange[0]} - {mockDelayRange[1]}
								</Typography.Text>
								<Slider
									range
									min={0}
									max={5000}
									step={50}
									value={mockDelayRange}
									onChange={(value) =>
										setMockDelayRange([
											Number((value as [number, number])[0]),
											Number((value as [number, number])[1]),
										])
									}
								/>
							</div>
							<div style={{ minWidth: 340 }}>
								<Typography.Text type="secondary">
									Force Fail Elements
								</Typography.Text>
								<Select
									mode="multiple"
									value={mockForceFailElements}
									style={{ width: "100%" }}
									placeholder="Choose element IDs to always fail"
									options={mockElementOptions}
									onChange={(values) => setMockForceFailElements(values as string[])}
								/>
							</div>
						</Space>
					</div>
				) : null}
			</div>

			{executionMode === "real" && !isEthereumBpmn ? (
				<IdentitySelector identity={identity} setIdentity={setIdentity} />
			) : executionMode === "real" && isEthereumBpmn ? (
				<Alert
					type="info"
					showIcon
					message="Ethereum execution"
					description="This BPMN uses the registered FireFly API directly. No Fabric FireFly identity selection is required on this page."
					style={{ marginBottom: 12 }}
				/>
			) : (
				<Alert
					type="info"
					showIcon
					message="Mock mode enabled"
					description="Actions update BPMN execution state locally for experiment validation. No chain contract / FireFly call is sent."
					style={{ marginBottom: 12 }}
				/>
			)}
			<div
				style={{
					marginTop: 12,
					marginBottom: 12,
					padding: 12,
					border: "1px solid #e2e8f0",
					borderRadius: 10,
					background: "#f8fafc",
				}}
			>
				<Space wrap size={8}>
					<Tag color={fireflyMeta?.connected ? "green" : "red"}>
						FireFly: {executionMode === "mock" ? "SKIPPED (MOCK)" : fireflyMeta?.connected ? "CONNECTED" : "DISCONNECTED"}
					</Tag>
					<Tag color="blue">Ready: {stateCounter.ready}</Tag>
					<Tag color="orange">Wait Confirm: {stateCounter.confirm}</Tag>
					<Tag color="default">Disabled: {stateCounter.disabled}</Tag>
					<Tag color="purple">Done: {stateCounter.done}</Tag>
					<Tag color="cyan">Actionable: {currentElements.length}</Tag>
				</Space>
				<Space wrap size={12} style={{ marginTop: 8 }}>
					<Typography.Text type="secondary">
						Core URL: {executionMode === "mock" ? "-" : full_core_url && full_core_url !== "http://" ? full_core_url : "-"}
					</Typography.Text>
					<Typography.Text type="secondary">
						Identity: {executionMode === "mock" ? "-" : identity?.name || "-"}
					</Typography.Text>
					<Typography.Text type="secondary">
						Last Sync: {executionMode === "mock" ? "-" : fireflyMeta?.lastSyncAt ? new Date(fireflyMeta.lastSyncAt).toLocaleTimeString() : "-"}
					</Typography.Text>
					<Typography.Text type="secondary">
						Last Manual Refresh: {lastManualRefreshAt ? new Date(lastManualRefreshAt).toLocaleTimeString() : "-"}
					</Typography.Text>
				</Space>
				{executionMode === "real" ? (
					<Space wrap size={12} style={{ marginTop: 8 }}>
						<Switch
							checked={autoRefresh}
							onChange={setAutoRefresh}
							checkedChildren="Auto Refresh"
							unCheckedChildren="Manual"
						/>
						<Select
							value={refreshIntervalMs}
							style={{ width: 160 }}
							onChange={(value) => setRefreshIntervalMs(value)}
							options={[
								{ label: "2s interval", value: 2000 },
								{ label: "5s interval", value: 5000 },
								{ label: "10s interval", value: 10000 },
							]}
						/>
						<Button
							loading={isRefreshing}
							onClick={() => {
								setIsRefreshing(true);
								setLastManualRefreshAt(new Date().toISOString());
								syncFireflyData();
								renderSvg();
							}}
						>
							Refresh
						</Button>
					</Space>
				) : (
					<div style={{ marginTop: 8 }}>
						<Space wrap size={12}>
							<Tag color="purple">Mock Steps: {executionElements.length}</Tag>
							<Tag color="success">Completed: {stateCounter.done}</Tag>
							<Tag color="processing">Actionable: {currentElements.length}</Tag>
							<Tag color={mockForceFailElements.length ? "error" : "default"}>
								Forced Fail Targets: {mockForceFailElements.length}
							</Tag>
						</Space>
						<Progress
							percent={mockDonePercent}
							size="small"
							strokeColor="#16a34a"
							trailColor="#e2e8f0"
							style={{ marginTop: 8, maxWidth: 360 }}
						/>
					</div>
				)}
				{executionMode === "real" && fireflyMeta?.error ? (
					<Alert
						style={{ marginTop: 8 }}
						type="warning"
						showIcon
						message="FireFly interaction warning"
						description={String(fireflyMeta.error)}
					/>
				) : null}
				<div
					style={{
						marginTop: 8,
						padding: 8,
						borderRadius: 8,
						background: "#f8fafc",
						border: "1px dashed #cbd5f5",
					}}
				>
					<Space wrap size={8}>
						<Tag color="processing">Running: {actionCounter.running}</Tag>
						<Tag color="success">Success: {actionCounter.success}</Tag>
						<Tag color="error">Failed: {actionCounter.failed}</Tag>
						<Tag color="default">Total: {actionRecords.length}</Tag>
					</Space>
					<Space wrap size={12} style={{ marginTop: 8 }}>
						<Select
							value={actionElementFilter}
							style={{ minWidth: 240 }}
							options={actionElementOptions}
							onChange={(value) => setActionElementFilter(value)}
						/>
						<Switch
							checked={autoScrollTimeline}
							onChange={setAutoScrollTimeline}
							checkedChildren="Auto Scroll"
							unCheckedChildren="Manual Scroll"
						/>
					</Space>
					<div
						ref={timelineRef}
						style={{
							marginTop: 8,
							maxHeight: 220,
							overflowY: "auto",
							borderRadius: 6,
							padding: 8,
							background: "#fff",
							border: "1px solid #e2e8f0",
						}}
					>
						{filteredActionRecords.length === 0 ? (
							<Typography.Text type="secondary">
								No records for current filter.
							</Typography.Text>
						) : (
							filteredActionRecords.slice(0, 12).map((record) => (
								<div
									key={record.traceId}
									style={{
										padding: "6px 0",
										borderBottom: "1px dashed #e2e8f0",
									}}
								>
									<Space wrap size={6}>
										<Tag
											color={
												record.status === "running"
													? "processing"
													: record.status === "success"
													? "success"
													: "error"
											}
										>
											{record.status.toUpperCase()}
										</Tag>
										<Tag color="blue">{record.type}</Tag>
										<Typography.Text>
											{record.action} ({record.elementId})
										</Typography.Text>
											<Typography.Text type="secondary">
												{new Date(record.startedAt).toLocaleTimeString()}
											</Typography.Text>
											{record.txId ? (
												<Button
													size="small"
													type="link"
													onClick={() => copyToClipboard(record.txId!, "tx")}
												>
													Copy tx
												</Button>
											) : null}
											{record.fireflyId ? (
												<Button
													size="small"
													type="link"
													onClick={() => copyToClipboard(record.fireflyId!, "message id")}
												>
													Copy msg
												</Button>
											) : null}
										</Space>
									{record.detail ? (
										<div>
											<Typography.Text type="secondary">
												{record.detail}
											</Typography.Text>
										</div>
									) : null}
									{record.txId || record.fireflyId ? (
										<div>
											<Typography.Text type="secondary">
												{record.txId ? `tx=${record.txId}` : ""}
												{record.txId && record.fireflyId ? " | " : ""}
												{record.fireflyId ? `message=${record.fireflyId}` : ""}
											</Typography.Text>
										</div>
									) : null}
									{record.error ? (
										<div>
											<Typography.Text type="danger">
												{record.error}
											</Typography.Text>
										</div>
									) : null}
								</div>
							))
						)}
					</div>
					{latestAction ? (
						<details style={{ marginTop: 8 }}>
							<summary>Latest Action Result</summary>
							<pre
								style={{
									marginTop: 6,
									maxHeight: 220,
									overflow: "auto",
									background: "#0f172a",
									color: "#e2e8f0",
									padding: 8,
									borderRadius: 6,
								}}
							>
								{JSON.stringify(latestAction.payload || latestAction, null, 2)}
							</pre>
						</details>
					) : null}
				</div>
			</div>

			<div
				dangerouslySetInnerHTML={{ __html: svgContent }}
				ref={svgRef}
				className={css(svgStyle)}
			/>

			{/* <Tag color="blue">Participant: {" " + getParticipantName(participant)}</Tag> */}

			<div
				style={{
					display: "flex",
					flexWrap: "wrap",
					gap: 12,
					marginTop: 20,
					padding: 12,
					border: "1px solid #e2e8f0",
					borderRadius: 10,
					background: "#ffffff",
				}}
			>
				{currentElements.map((currentElement) => {
					return (
						<ControlPanel
							key={`${currentElement.type}-${currentElement.EventID || currentElement.GatewayID || currentElement.MessageID || currentElement.BusinessRuleID}`}
							currentElement={currentElement}
							contractName={contractName}
							coreURL={full_core_url}
							bpmnName={bpmnData.name}
							contractMethodDes={contractMethodDes}
							bpmn={bpmnData}
							bpmnInstance={bpmnInstance}
							instanceId={bpmnInstance.instance_chaincode_id}
							identity={identity}
							onActionRecord={onActionRecord}
							executionMode={executionMode}
							onMockAction={runMockAction}
							mockProcessingElementId={mockProcessingElementId}
						/>
					);
				})}
			</div>
		</div>
	);
};

export default ExecutionPage;
