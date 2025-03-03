import { useEffect, useRef, useState } from "react";
import { css } from "@emotion/css";
import {
	Button,
	Input,
	Form,
	Upload,
	Tag,
	Typography,
	Table,
	Select,
} from "antd";
import { UploadOutlined } from "@ant-design/icons";
import { useLocation } from "react-router-dom";
import {
	useBPMNIntanceDetailData,
	useBPMNDetailData,
	useFireflyIdentity,
} from "./hook";
import {
	getFireflyIdentity,
	getFireflyWithMSP,
} from "@/api/externalResource.ts";
import { useSelector } from "react-redux";
import TestComponentV2 from "./testComponent.jsx";

import {
	getMessageWithId,
	getBatchWithId,
	getOperationWithId,
	getEventWithTX,
} from "@/api/fireflyAPI.ts";

const TestMode = false;

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
} from "@/api/executionAPI.ts";

const InputComponentForMessage = ({
	currentElement,
	contractName,
	coreURL,
	bpmnName,
	Identity,
	contractMethodDes,
	bpmn,
	bpmnInstance,
	instanceId,
	the_identity,
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
		invokeMessageAction(
			coreURL,
			contractName,
			methodName,
			{},
			instanceId,
			the_identity.identity.data[0].value,
		);
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
				});
			setMessageToConfirm(messageToShow);
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
							<Tag color="green">
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
		// 0. get Identity to send message

		// const msp = currentElement.ReceiveMspID
		// const mspData = await getFireflyWithMSP(msp)

		const Identity = "did:firefly:" + the_identity?.name;

		// 1. check type
		// 2. upload file if exists
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
		if (file_ids) {
			await new Promise((resolve) => setTimeout(resolve, 2000));
		}
		// // 3. send firefly message if exists

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
		console.log("SENDDATA");
		console.log(res);
		output_obj["message_id"] = res.header.id;
		output_obj["message_create_time"] = res.header.created;
		const fireflyMessageID = res.header.id;
		// // 4. use firefly message id to send contract message
		// const fireflyMessageID = "534a8bd7-4d3f-42a9-86b4-8248a2c3164e"
		const methodParams = contractMethodDes.methods
			.find((item) => {
				return item.name === methodName;
			})
			.params.filter((item) => {
				return item.name !== "fireflyTranID";
			});
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
			the_identity.identity.data[0].value,
		);
		console.log("SENDDATA");
		console.log(res2);
		output_obj["invoke_id"] = res2.id;
		output_obj["invoke_start_time"] = res2.created;
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
					await onHandleMessage(formRef.current.getFieldsValue(), output_obj);
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
					console.log("format.properties", format.properties);
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
				if (entry.name.includes(url_pattern)) {
					const navigationStart = performance.timing.navigationStart;
					theRes["start_time"] = navigationStart + entry.fetchStart;
					theRes["timeCost"] = entry.responseStart - entry.requestStart;
					theRes["end_time"] = navigationStart + entry.responseEnd;
				}
			}
		});
		observer.observe({ entryTypes: ["resource"] });
		const res = await func(...args);
		await sleep(300);
		observer.disconnect();
		// console.log(`Execution details for ${label}:`, theRes);
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
}) => {
	const location = useLocation();
	const queryParams = new URLSearchParams(location.search);
	const msp = queryParams.get("msp");
	const type = currentElement?.type;
	const Identity = queryParams.get("identity");
	const isYourTurn = (() => {
		if (type === "event") return currentElement?.EventState === 1;
		if (type === "gateway") return currentElement?.GatewayState === 1;
		if (type === "message")
			return (
				currentElement?.MsgState === 1 ||
				// currentElement?.sendMspID === msp ||
				currentElement?.MsgState === 2
			);
		// currentElement?.receiveMspID === msp;
		if (type === "businessRule") return currentElement?.State === 1;
	})();
	// debugger
	const showTransactionId = (() => {
		if (type === "message")
			return (
				currentElement?.msgState === 2 && currentElement?.receiveMspID === msp
			);
		return false;
	})();

	if (!isYourTurn) return null;

	// EVENT

	const onHandleEvent = () => {
		TimeDecorator(invokeEventAction, "Event", "invoke/Event")(
			coreURL,
			contractName,
			currentElement.EventID,
			instanceId,
		);
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

	const onHandleGateway = () => {
		TimeDecorator(invokeGatewayAction, "Gateway", "invoke/Gateway")(
			coreURL,
			contractName,
			currentElement.GatewayID,
			instanceId,
		);
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
		const res = await TimeDecorator(invokeBusinessRuleAction, "BusinessRule", "invoke/Activity", output)(
			coreURL,
			contractName,
			currentElement.BusinessRuleID,
			instanceId,
		);

		return res
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
						onHandleBusinessRule();
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
						const operation = await getOperationWithId("http://127.0.0.1:5000", executor_op);
						const executor_tx = operation.tx;
						const events2 = await getEventWithTX("http://127.0.0.1:5000", executor_tx);
						output["event_time_2"] =  events2[0].created
						for (const key in output) {
							output[key] = TimeStampHandler(output[key]);
						}
						return output;
					}}
					calcFunc={(time_obj) => {
						console.log(time_obj);
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
						Identity={Identity}
						contractMethodDes={contractMethodDes}
						bpmn={bpmn}
						bpmnInstance={bpmnInstance}
						instanceId={instanceId}
						the_identity={identity}
					/>
				) : null}
			</div>
		);
};

import { useAvailableIdentity } from "./hook.ts";

const IdentitySelector = ({ identity, setIdentity }) => {
	// 1. get all membership and participant based on user identity
	const [currentMembership, setCurrentMembership] = useState("");
	const [availableIdentities, isLoading, refetch] = useAvailableIdentity();
	const identities_example = [
		{
			memebership_id: "123",
			membership_name: "123",
			identities: [
				{
					core_url: "127.0.0.1:5001",
					firefly_identity_id: "dfc4",
					identity_id: "6e",
					name: "name",
				},
			],
		},
	];
	// console.log(availableIdentities)
	// console.log(currentMembership)

	if (isLoading || !availableIdentities) {
		return <div>Loading</div>;
	}

	// console.log(availableIdentities.find((item) => item.membership_id === currentMembership))

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
				{availableIdentities.map((item) => {
					return (
						<Select.Option key={item.membership_id} value={item.memebership_id}>
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
					const the_one = availableIdentities
						.find((item) => item.membership_id === currentMembership)
						?.identities.find((item) => item.firefly_identity_id === value);
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
				{availableIdentities
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

import { useAllFireflyData } from "./hook";
import axios from "axios";
import { time } from "console";

const ExecutionPage = (props) => {
	const bpmnInstanceId = window.location.pathname.split("/").pop();

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

	const contractName = bpmnReady
		? bpmnData.chaincode.name + "-" + bpmnData.chaincode.id.substring(0, 6)
		: "";
	const full_core_url = "http://" + identity.core_url;
	const [
		allEvents,
		allGateways,
		allMessages,
		allBusinessRules,
		fireflyDataReady,
		syncFireflyData,
	] = useAllFireflyData(
		full_core_url,
		contractName,
		bpmnInstance.instance_chaincode_id,
	);
	const currentElements = [
		...allMessages,
		...allEvents,
		...allGateways,
		...allBusinessRules,
	].filter((msg) => {
		return msg.state === 1 || msg.state === 2;
	});

	const renderSvg = () => {
		const updatedMsgList = [
			...allMessages,
			...allEvents,
			...allGateways,
			...allBusinessRules,
		].map((msg) => {
			let color = "";
			// msgState, gatewayState, eventState;
			// State: 0: disabled, 1: enabled, 2: wait for confirm, 3: completed
			switch (msg.state) {
				case 0:
					color = "unColored";
					break;
				case 1:
					color = "green";
					break;
				case 2:
					color = "red";
					break;
				case 3:
					color = "blue";
					break;
				default:
					color = "";
			}
			return { ...msg, color };
		});

		const generateStylesWithMsgList = (msgList) => {
			let styles = { "& svg": {} };
			msgList.forEach((msg) => {
				if (msg.color === "unColored" && msg.color === "") return;

				const selector = (() => {
					console.log(msg);
					if (msg.type === "event")
						return `& g[data-element-id="${msg.EventID}"]`;
					if (msg.type === "gateway")
						return `& g[data-element-id="${msg.GatewayID}"]`;
					if (msg.type === "message")
						return `& g[data-element-id="${msg.MessageID}"]`;
					if (msg.type === "businessRule") {
						return `& g[data-element-id="${msg.BusinessRuleID}"]`;
					}
				})();
				styles["& svg"][selector] = {
					"& path": {
						fill: `${msg.color} !important`,
					},
					"& polygon": {
						fill: `${msg.color} !important`,
					},
					"& circle": {
						fill: `${msg.color} !important`,
					},
					// "& rect": {
					//     fill: `${msg.color} !important`,
					// }
				};
			});
			return styles;
		};
		const newStyles = generateStylesWithMsgList(updatedMsgList);
		setSvgStyle(newStyles);
	};

	useEffect(() => {
		renderSvg();
	}, [fireflyDataReady]);

	// useEffect(() => {
	//     const task = setInterval(() => {
	//         syncFireflyData();
	//     }, 3000);
	//     return () => {
	//         clearInterval(task);
	//     }
	// }
	//     , []);

	return (
		<div className="Execution">
			<IdentitySelector identity={identity} setIdentity={setIdentity} />

			<div
				dangerouslySetInnerHTML={{ __html: svgContent }}
				ref={svgRef}
				className={css(svgStyle)}
			/>

			{/* <Tag color="blue">Participant: {" " + getParticipantName(participant)}</Tag> */}

			<div style={{ display: "flex", marginTop: "20px" }}>
				{currentElements.map((currentElement) => {
					return (
						<ControlPanel
							currentElement={currentElement}
							contractName={contractName}
							coreURL={full_core_url}
							bpmnName={bpmnData.name}
							contractMethodDes={contractMethodDes}
							bpmn={bpmnData}
							bpmnInstance={bpmnInstance}
							instanceId={bpmnInstance.instance_chaincode_id}
							identity={identity}
						/>
					);
				})}
			</div>
			<Button
				onClick={() => {
					syncFireflyData();
					renderSvg();
				}}
			>
				Refresh
			</Button>
			<Button
				onClick={() => {
					syncFireflyData();
					renderSvg();
				}}
			>
				StateCharts Detail
			</Button>
		</div>
	);
};

export default ExecutionPage;
