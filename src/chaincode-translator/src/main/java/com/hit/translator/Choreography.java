package com.hit.translator;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.hit.translator.ChoreographyTask;
import org.camunda.bpm.model.bpmn.Bpmn;
import org.camunda.bpm.model.bpmn.BpmnModelInstance;
import org.camunda.bpm.model.bpmn.instance.*;
import org.camunda.bpm.model.xml.impl.instance.ModelElementInstanceImpl;
import org.camunda.bpm.model.xml.instance.DomElement;
import org.camunda.bpm.model.xml.instance.ModelElementInstance;

// import org.hyperledger.fabric.contract.ContractInterface;
// import org.hyperledger.fabric.contract.annotation.Contact;
// import org.hyperledger.fabric.contract.annotation.Contract;
// import org.hyperledger.fabric.contract.annotation.Default;
// import org.hyperledger.fabric.contract.annotation.Info;
// import org.hyperledger.fabric.contract.annotation.License;

import com.owlike.genson.Genson;
import org.json.JSONObject;
import org.json.JSONTokener;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

//java doc: https://docs.camunda.org/javadoc/camunda-bpm-platform/7.3/overview-summary.html
public class Choreography {

    private final Genson genson = new Genson();

    private enum AssetTransferErrors {
        ASSET_NOT_FOUND,
        ASSET_ALREADY_EXISTS
    }

    public static int startint;
    private static BpmnModelInstance modelInstance;
    public static ArrayList<String> participantsWithoutDuplicates;
    public static ArrayList<String> partecipants;
    public static ArrayList<String> functions;
    public static Collection<FlowNode> allNodes;
    public static int startCounter;
    public static Integer xorCounter;
    public static Integer parallelCounter;
    public static Integer eventBasedCounter;
    public static Integer endEventCounter;
    public static String choreographyFile;
    public ArrayList<DomElement> participantsTask;
    public ArrayList<DomElement> msgTask;
    public ArrayList<SequenceFlow> taskIncoming, taskOutgoing;
    public static ArrayList<String> nodeSet;
    public static String request; // 存储括号内的一系列参数
    public static String response;
    public static ArrayList<String> gatewayGuards; // 消息传入的参数（完全是 类型+参数 的形式）
    public static Map<String, String> messageParasMap; // 之后构造器需要补上
    public static Set<String> gatewayMemoryParams;
    public static ArrayList<String> toBlock;
    public static List<String> tasks;
    // public static ContractObject finalContract;
    public static List<String> elementsID;
    private static String startEventAdd;
    // private static List<String> roleFortask; 不需要
    // private static LinkedHashMap<String, String> taskIdAndRole; 不需要
    public static String ffiJsonFile = "";
    private final String TRANSSUBMIT = "    @Transaction(intent = Transaction.TYPE.SUBMIT)\n";
    private final String TRANSEVALUATE = "    @Transaction(intent = Transaction.TYPE.EVALUATE)\n";

    // public boolean start(File bpmnFile, Map<String, User> participants,
    // List<String> optionalRoles,
    // List<String> mandatoryRoles) throws Exception {
    public static boolean start(File bpmnFile, String participantMspMap) throws Exception {
        try {
            Choreography choreography = new Choreography();
            choreography.readFile(bpmnFile);
            choreography.getParticipants();
            choreography.storageAllMessageParasMap();
            System.out.println(messageParasMap);
            choreography.addGatewayMemoryParams();
            choreography.FlowNodeSearch();
            // 后四个需要修改
            choreographyFile = choreography.initial(bpmnFile.getName(), participantMspMap)
                    + choreographyFile; // initial需要修改为生成链码
            // choreographyFile += choreography.lastFunctions(); //这个不需要
            // finalContract = new ContractObject(null, null, null, null, gatewayGuards,
            // taskIdAndRole); 存疑，用作数据库存储
            choreography.fileAll(bpmnFile.getName());

            // System.out.println("Contract creation done");
            // System.out.println("Ruolii:" + Arrays.toString(roleFortask.toArray()));
            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }

    }

    public static boolean startExport(File bpmnFile, String participantMspMap) throws Exception {
        try {
            Choreography choreography = new Choreography();
            choreography.readFile(bpmnFile);
            choreography.getParticipants();
            choreography.storageAllMessageParasMap();
            // System.out.println(messageParasMap);
            choreography.addGatewayMemoryParams();
            choreography.FlowNodeSearch();

            choreographyFile = choreography.initial(bpmnFile.getName(), participantMspMap)
                    + choreographyFile;

            // choreography.fileAllResponse(bpmnFile.getName());

            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }

    }

    public Choreography() {
        elementsID = new ArrayList<String>();
        tasks = new ArrayList<String>();
        gatewayGuards = new ArrayList<String>();
        partecipants = new ArrayList<String>();
        startint = 0;
        startCounter = 0;
        xorCounter = 0;
        eventBasedCounter = 0;
        parallelCounter = 0;
        endEventCounter = 0;
        choreographyFile = "";
        this.participantsTask = new ArrayList<DomElement>();
        this.msgTask = new ArrayList<DomElement>();
        this.taskIncoming = new ArrayList<SequenceFlow>();
        this.taskOutgoing = new ArrayList<SequenceFlow>();
        nodeSet = new ArrayList<>();
        request = "";
        response = "";
        startEventAdd = "";
        gatewayGuards = new ArrayList<String>();
        gatewayMemoryParams = new HashSet<String>();
        messageParasMap = new HashMap<String, String>();
    }

    public void readFile(File bpFile) throws IOException {
        System.out.println("You chose to open this file: " + bpFile.getName());
        modelInstance = Bpmn.readModelFromFile(bpFile);
        allNodes = modelInstance.getModelElementsByType(FlowNode.class);
    }

    private static String initial(String filename, String participantMspMap) {

        String intro = "package chaincode\n" +
                "\n" +
                "import (\n" +
                "\t\"encoding/json\"\n" +
                "\t\"errors\"\n" +
                "\t\"fmt\"\n" +
                "\t\"github.com/hyperledger/fabric-contract-api-go/contractapi\"\n" +
                "\t\"strings\"\n" +
                ")\n" +
                "\n" +
                "// SmartContract provides functions for managing an Asset\n" +
                "type SmartContract struct {\n" +
                "\tcontractapi.Contract\n" +
                "\tcurrentMemory StateMemory\n" +
                "}\n\n"
                + "type ElementState int\n" +
                "\n" +
                "const (\n" +
                "\tDISABLE = iota\n" +
                "\tENABLE\n" +
                "\tWAITFORCONFIRM\n" +
                "\tDONE\n" +
                ")\n" +
                "\n" +
                "type Message struct {\n" +
                "\tMessageID     string       `json:\"messageID\"`\n" +
                "\tSendMspID     string       `json:\"sendMspID\"`\n" +
                "\tReceiveMspID  string       `json:\"receiveMspID\"`\n" +
                "\tFireflyTranID string       `json:\"fireflyTranID\"`\n" +
                "\tMsgState      ElementState `json:\"msgState\"`\n" +
                "\tFormat        string       `json:\"format\"`\n" +
                "}\n" +
                "\n" +
                "type Gateway struct {\n" +
                "\tGatewayID    string       `json:\"gatewayID\"`\n" +
                "\tGatewayState ElementState `json:\"gatewayState\"`\n" +
                "}\n" +
                "\n" +
                "type ActionEvent struct {\n" +
                "\tEventID    string       `json:\"eventID\"`\n" +
                "\tEventState ElementState `json:\"eventState\"`\n" +
                "}\n\n"
                + "type StateMemory struct { \n";

        for (String param : gatewayMemoryParams) {
            if (messageParasMap.containsKey(param)) {
                intro += "\t" + param + "\t\t" + transfer2GoType(messageParasMap.get(param)) + "\t\t`json:\"" + param
                        + "\"`\n";
            }
        }
        intro += "}\n\n";

        String consFunc = "func (cc *SmartContract) CreateMessage(ctx contractapi.TransactionContextInterface, messageID string, sendMspID string, receiveMspID string, fireflyTranID string, msgState ElementState, format string) (*Message, error) {\n"
                +
                "\tstub := ctx.GetStub()\n" +
                "\n" +
                "\t// 检查是否存在具有相同ID的记录\n" +
                "\texistingData, err := stub.GetState(messageID)\n" +
                "\tif err != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"获取状态数据时出错: %v\", err)\n" +
                "\t}\n" +
                "\tif existingData != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"消息 %s 已存在\", messageID)\n" +
                "\t}\n" +
                "\n" +
                "\t// 创建消息对象\n" +
                "\tmsg := &Message{\n" +
                "\t\tMessageID:     messageID,\n" +
                "\t\tSendMspID:     sendMspID,\n" +
                "\t\tReceiveMspID:  receiveMspID,\n" +
                "\t\tFireflyTranID: fireflyTranID,\n" +
                "\t\tMsgState:      msgState,\n" +
                "\t\tFormat:      format,\n" +
                "\t}\n" +
                "\n" +
                "\t// 将消息对象序列化为JSON字符串并保存在状态数据库中\n" +
                "\tmsgJSON, err := json.Marshal(msg)\n" +
                "\tif err != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"序列化消息数据时出错: %v\", err)\n" +
                "\t}\n" +
                "\terr = stub.PutState(messageID, msgJSON)\n" +
                "\tif err != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"保存消息数据时出错: %v\", err)\n" +
                "\t}\n" +
                "\n" +
                "\treturn msg, nil\n" +
                "}\n" +
                "\n" +
                "func (cc *SmartContract) CreateGateway(ctx contractapi.TransactionContextInterface, gatewayID string, gatewayState ElementState) (*Gateway, error) {\n"
                +
                "\tstub := ctx.GetStub()\n" +
                "\n" +
                "\t// 检查是否存在具有相同ID的记录\n" +
                "\texistingData, err := stub.GetState(gatewayID)\n" +
                "\tif err != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"获取状态数据时出错: %v\", err)\n" +
                "\t}\n" +
                "\tif existingData != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"网关 %s 已存在\", gatewayID)\n" +
                "\t}\n" +
                "\n" +
                "\t// 创建网关对象\n" +
                "\tgtw := &Gateway{\n" +
                "\t\tGatewayID:    gatewayID,\n" +
                "\t\tGatewayState: gatewayState,\n" +
                "\t}\n" +
                "\n" +
                "\t// 将网关对象序列化为JSON字符串并保存在状态数据库中\n" +
                "\tgtwJSON, err := json.Marshal(gtw)\n" +
                "\tif err != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"序列化网关数据时出错: %v\", err)\n" +
                "\t}\n" +
                "\terr = stub.PutState(gatewayID, gtwJSON)\n" +
                "\tif err != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"保存网关数据时出错: %v\", err)\n" +
                "\t}\n" +
                "\n" +
                "\treturn gtw, nil\n" +
                "}\n" +
                "\n" +
                "func (cc *SmartContract) CreateActionEvent(ctx contractapi.TransactionContextInterface, eventID string, eventState ElementState) (*ActionEvent, error) {\n"
                +
                "\tstub := ctx.GetStub()\n" +
                "\n" +
                "\t// 创建ActionEvent对象\n" +
                "\tactionEvent := &ActionEvent{\n" +
                "\t\tEventID:    eventID,\n" +
                "\t\tEventState: eventState,\n" +
                "\t}\n" +
                "\n" +
                "\t// 将ActionEvent对象序列化为JSON字符串并保存在状态数据库中\n" +
                "\tactionEventJSON, err := json.Marshal(actionEvent)\n" +
                "\tif err != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"序列化事件数据时出错: %v\", err)\n" +
                "\t}\n" +
                "\terr = stub.PutState(eventID, actionEventJSON)\n" +
                "\tif err != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"保存事件数据时出错: %v\", err)\n" +
                "\t}\n" +
                "\n" +
                "\treturn actionEvent, nil\n" +
                "}\n" +
                "\n" +
                "// Read function\n" +
                "func (c *SmartContract) ReadMsg(ctx contractapi.TransactionContextInterface, messageID string) (*Message, error) {\n"
                +
                "\tmsgJSON, err := ctx.GetStub().GetState(messageID)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn nil, err\n" +
                "\t}\n" +
                "\n" +
                "\tif msgJSON == nil {\n" +
                "\t\terrorMessage := fmt.Sprintf(\"Message %s does not exist\", messageID)\n" +
                "\t\tfmt.Println(errorMessage)\n" +
                "\t\treturn nil, errors.New(errorMessage)\n" +
                "\t}\n" +
                "\n" +
                "\tvar msg Message\n" +
                "\terr = json.Unmarshal(msgJSON, &msg)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn nil, err\n" +
                "\t}\n" +
                "\n" +
                "\treturn &msg, nil\n" +
                "}\n" +
                "\n" +
                "func (c *SmartContract) ReadGtw(ctx contractapi.TransactionContextInterface, gatewayID string) (*Gateway, error) {\n"
                +
                "\tgtwJSON, err := ctx.GetStub().GetState(gatewayID)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn nil, err\n" +
                "\t}\n" +
                "\n" +
                "\tif gtwJSON == nil {\n" +
                "\t\terrorMessage := fmt.Sprintf(\"Gateway %s does not exist\", gatewayID)\n" +
                "\t\tfmt.Println(errorMessage)\n" +
                "\t\treturn nil, errors.New(errorMessage)\n" +
                "\t}\n" +
                "\n" +
                "\tvar gtw Gateway\n" +
                "\terr = json.Unmarshal(gtwJSON, &gtw)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn nil, err\n" +
                "\t}\n" +
                "\n" +
                "\treturn &gtw, nil\n" +
                "}\n" +
                "\n" +
                "func (c *SmartContract) ReadEvent(ctx contractapi.TransactionContextInterface, eventID string) (*ActionEvent, error) {\n"
                +
                "\teventJSON, err := ctx.GetStub().GetState(eventID)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn nil, err\n" +
                "\t}\n" +
                "\n" +
                "\tif eventJSON == nil {\n" +
                "\t\terrorMessage := fmt.Sprintf(\"Event state %s does not exist\", eventID)\n" +
                "\t\tfmt.Println(errorMessage)\n" +
                "\t\treturn nil, errors.New(errorMessage)\n" +
                "\t}\n" +
                "\n" +
                "\tvar event ActionEvent\n" +
                "\terr = json.Unmarshal(eventJSON, &event)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn nil, err\n" +
                "\t}\n" +
                "\n" +
                "\treturn &event, nil\n" +
                "}\n" +
                "\n" +
                "// Change State  function\n" +
                "func (c *SmartContract) ChangeMsgState(ctx contractapi.TransactionContextInterface, messageID string, msgState ElementState) error {\n"
                +
                "\tstub := ctx.GetStub()\n" +
                "\n" +
                "\tmsg, err := c.ReadMsg(ctx, messageID)\n" +
                "\tif err != nil {\n" +
                "\t\treturn err\n" +
                "\t}\n" +
                "\n" +
                "\tmsg.MsgState = msgState\n" +
                "\n" +
                "\tmsgJSON, err := json.Marshal(msg)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn err\n" +
                "\t}\n" +
                "\n" +
                "\terr = stub.PutState(messageID, msgJSON)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn err\n" +
                "\t}\n" +
                "\n" +
                "\treturn nil\n" +
                "}\n" +
                "\n" +
                "func (c *SmartContract) ChangeGtwState(ctx contractapi.TransactionContextInterface, gatewayID string, gtwState ElementState) error {\n"
                +
                "\tstub := ctx.GetStub()\n" +
                "\n" +
                "\tgtw, err := c.ReadGtw(ctx, gatewayID)\n" +
                "\tif err != nil {\n" +
                "\t\treturn err\n" +
                "\t}\n" +
                "\n" +
                "\tgtw.GatewayState = gtwState\n" +
                "\n" +
                "\tgtwJSON, err := json.Marshal(gtw)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn err\n" +
                "\t}\n" +
                "\n" +
                "\terr = stub.PutState(gatewayID, gtwJSON)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn err\n" +
                "\t}\n" +
                "\n" +
                "\treturn nil\n" +
                "}\n" +
                "\n" +
                "func (c *SmartContract) ChangeEventState(ctx contractapi.TransactionContextInterface, eventID string, eventState ElementState) error {\n"
                +
                "\tstub := ctx.GetStub()\n" +
                "\n" +
                "\tactionEvent, err := c.ReadEvent(ctx, eventID)\n" +
                "\tif err != nil {\n" +
                "\t\treturn err\n" +
                "\t}\n" +
                "\n" +
                "\tactionEvent.EventState = eventState\n" +
                "\n" +
                "\tactionEventJSON, err := json.Marshal(actionEvent)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn err\n" +
                "\t}\n" +
                "\n" +
                "\terr = stub.PutState(eventID, actionEventJSON)\n" +
                "\tif err != nil {\n" +
                "\t\tfmt.Println(err.Error())\n" +
                "\t\treturn err\n" +
                "\t}\n" +
                "\n" +
                "\treturn nil\n" +
                "}\n" +
                "\n" +
                "//get all message\n" +
                "\n" +
                "func (cc *SmartContract) GetAllMessages(ctx contractapi.TransactionContextInterface) ([]*Message, error) {\n"
                +
                "\tresultsIterator, err := ctx.GetStub().GetStateByRange(\"\", \"\")\n" +
                "\tif err != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"获取状态数据时出错: %v\", err) //直接err也行\n" +
                "\t}\n" +
                "\tdefer resultsIterator.Close()\n" +
                "\n" +
                "\tvar messages []*Message\n" +
                "\tfor resultsIterator.HasNext() {\n" +
                "\t\tqueryResponse, err := resultsIterator.Next()\n" +
                "\t\tif err != nil {\n" +
                "\t\t\treturn nil, fmt.Errorf(\"迭代状态数据时出错: %v\", err)\n" +
                "\t\t}\n" +
                "\n" +
                "\t\tvar message Message\n" +
                "\t\terr = json.Unmarshal(queryResponse.Value, &message)\n" +
                "\t\tif strings.HasPrefix(message.MessageID, \"Message\") {\n" +
                "			if err != nil {\n" +
                "\t\t\t\treturn nil, fmt.Errorf(\"反序列化消息数据时出错: %v\", err)\n" +
                "			}\n\n" +
                "			messages = append(messages, &message)\n		}\n" +
                "\t}\n" +
                "\n" +
                "\treturn messages, nil\n" +
                "}\n\n" +
                // 获得所有元素方法
                "func (cc *SmartContract) GetAllGateways(ctx contractapi.TransactionContextInterface) ([]*Gateway, error) {\n"
                +
                "\tresultsIterator, err := ctx.GetStub().GetStateByRange(\"\", \"\")\n" +
                "\tif err != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"获取状态数据时出错: %v\", err) \n" +
                "\t}\n" +
                "\tdefer resultsIterator.Close()\n" +
                "\n" +
                "\tvar gateways []*Gateway\n" +
                "\tfor resultsIterator.HasNext() {\n" +
                "\t\tqueryResponse, err := resultsIterator.Next()\n" +
                "\t\tif err != nil {\n" +
                "\t\t\treturn nil, fmt.Errorf(\"迭代状态数据时出错: %v\", err)\n" +
                "\t\t}\n" +
                "\n" +
                "\t\tvar gateway Gateway\n" +
                "\t\terr = json.Unmarshal(queryResponse.Value, &gateway)\n" +
                "\t\tif strings.HasPrefix(gateway.GatewayID, \"ExclusiveGateway\") ||\n" +
                "\t\t\tstrings.HasPrefix(gateway.GatewayID, \"EventBasedGateway\") ||\n" +
                "\t\t\tstrings.HasPrefix(gateway.GatewayID, \"Gateway\") ||\n" +
                "\t\t\tstrings.HasPrefix(gateway.GatewayID, \"ParallelGateway\") {\n" +
                "\t\t\tif err != nil {\n" +
                "\t\t\t\treturn nil, fmt.Errorf(\"反序列化网关数据时出错: %v\", err)\n" +
                "\t\t\t}\n" +
                "\n" +
                "\t\t\tgateways = append(gateways, &gateway)\n" +
                "\t\t}\n" +
                "\t}\n" +
                "\n" +
                "\treturn gateways, nil\n" +
                "}\n\n" +
                "func (cc *SmartContract) GetAllActionEvents(ctx contractapi.TransactionContextInterface) ([]*ActionEvent, error) {\n"
                +
                "\tresultsIterator, err := ctx.GetStub().GetStateByRange(\"\", \"\")\n" +
                "\tif err != nil {\n" +
                "\t\treturn nil, fmt.Errorf(\"获取状态数据时出错: %v\", err)\n" +
                "\t}\n" +
                "\tdefer resultsIterator.Close()\n" +
                "\n" +
                "\tvar events []*ActionEvent\n" +
                "\tfor resultsIterator.HasNext() {\n" +
                "\t\tqueryResponse, err := resultsIterator.Next()\n" +
                "\t\tif err != nil {\n" +
                "\t\t\treturn nil, fmt.Errorf(\"迭代状态数据时出错: %v\", err)\n" +
                "\t\t}\n" +
                "\n" +
                "\t\tvar event ActionEvent\n" +
                "\t\terr = json.Unmarshal(queryResponse.Value, &event)\n" +
                "\t\tif strings.HasPrefix(event.EventID, \"StartEvent\") ||\n" +
                "\t\t\tstrings.HasPrefix(event.EventID, \"Event\") ||\n" +
                "\t\t\tstrings.HasPrefix(event.EventID, \"EndEvent\") {\n" +
                "\t\t\tif err != nil {\n" +
                "\t\t\t\treturn nil, fmt.Errorf(\"反序列化事件数据时出错: %v\", err)\n" +
                "\t\t\t}\n" +
                "\n" +
                "\t\t\tevents = append(events, &event)\n" +
                "\t\t}\n" +
                "\t}\n" +
                "\n" +
                "\treturn events, nil\n" +
                "}\n\n";

        String initFunc = "\n" +
                "// InitLedger adds a base set of elements to the ledger\n" +
                "\n" +
                "var isInited bool = false\n\n"
                + "func (cc *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {\n" +
                "\tstub := ctx.GetStub()\n"
                + "\tif isInited {\n" +
                "\t\terrorMessage := \"Chaincode has already been initialized\"\n" +
                "\t\tfmt.Println(errorMessage)\n" +
                "\t\treturn fmt.Errorf(errorMessage)\n" +
                "\t}\n\n";

        String tempStartElement = "";

        for (String elID : elementsID) { // 所有元素的
            // System.out.println("elementsID is :" + elementsID + "\n\n\n");
            // if (elID.equals(elementsID.get(elementsID.size() - 1))) {
            // System.out.println("sono uguale: " + elID + " e: " +
            // elementsID.get(elementsID.size()-1));
            if (elID.startsWith("Event") && !elID.startsWith("EventBased")) {
                ModelElementInstance event = modelInstance.getModelElementById(elID);
                // 开始事件
                if (event instanceof StartEvent) {
                    initFunc += "\tcc.CreateActionEvent(ctx, \"" + elID + "\", ENABLE)\n";
                    tempStartElement = elID;
                } else if (event instanceof EndEvent) {
                    initFunc += "\tcc.CreateActionEvent(ctx, \"" + elID + "\", DISABLE)\n";
                }

            } else if (elID.startsWith("Message")) {
                // func (cc *SmartContract) CreateMessage(ctx
                // contractapi.TransactionContextInterface,
                // messageID string, sendMspID string, receiveMspID string,
                // fireflyTranID string, msgState ElementState, format string)
                Message messageChildElement = modelInstance.getModelElementById(elID);
                String docuType = "";
                if (messageChildElement != null) {
                    for (DomElement childElement : messageChildElement.getDomElement().getChildElements()) {
                        String type = childElement.getLocalName();
                        // switch (type) {
                        // case "documentation":
                        // docuType = childElement.getTextContent();
                        // docuType = docuType.replace("\"", "\\\"");
                        //
                        // }
                        switch (type) {
                            case "documentation":
                                docuType = childElement.getTextContent();

                                ObjectMapper objectMapper = new ObjectMapper();
                                String formattedJson = "";

                                try {
                                    JsonNode rootNode = objectMapper.readTree(docuType);
                                    formattedJson = objectMapper.writeValueAsString(rootNode);

                                    JsonNode propertiesNode = rootNode.get("properties");

                                    if (propertiesNode != null) {
                                        propertiesNode.fields().forEachRemaining(entry -> {
                                            String propertyName = entry.getKey();
                                            JsonNode propertyNode = entry.getValue();

                                            JsonNode typeNode = propertyNode.get("type");
                                            String propertyType = typeNode != null ? typeNode.asText() : null;

                                            System.out
                                                    .println("Property Name: " + propertyName + ", Type: "
                                                            + propertyType);
                                        });
                                    }
                                } catch (JsonProcessingException e) {
                                    throw new RuntimeException(e);
                                }
                                formattedJson = formattedJson.replaceAll("\"", "\\\\\"");
                                docuType = formattedJson; // 将重新格式化后的 JSON 字符串赋值给 docuType
                                break; // 确保在处理完 "documentation" 后结束 case
                        }
                    }
                }

                String tempSourceMsp = "";
                String tempTargetMsp = "";

                for (MessageFlow flow : modelInstance.getModelElementsByType(MessageFlow.class)) {
                    // System.out.println(elID.equals(flow.getAttributeValue("messageRef")));
                    if (elID.equals(flow.getAttributeValue("messageRef"))) {
                        String tempSourceRef = flow.getAttributeValue("sourceRef");
                        // String tempSourceRef = flow.getSource().getAttributeValue("id");
                        String tempTargetRef = flow.getAttributeValue("targetRef");
                        // System.out.println(tempSourceRef + tempTargetRef );
                        // try {
                        Genson tempGenson = new Genson();
                        // String jsonContent = new String(
                        // Files.readAllBytes(Paths.get("src/main/java/org/example/mocks/msp.json")));
                        Map<String, String> jsonMap = tempGenson.deserialize(participantMspMap, Map.class);
                        System.out.println("jsonMap = " + jsonMap);
                        if (jsonMap != null) {
                            for (Map.Entry<String, String> entry : jsonMap.entrySet()) {
                                String key = entry.getKey();
                                String value = entry.getValue();
                                if (key.equals(tempSourceRef)) {
                                    tempSourceMsp = value;
                                }
                                if (key.equals(tempTargetRef)) {
                                    tempTargetMsp = value;
                                }
                            }
                        }
                        // } catch (IOException e) {
                        // throw new RuntimeException(e);
                        // }
                    }
                }
                // MessageFlow tempMessageFlow = modelInstance.get;

                initFunc += "\tcc.CreateMessage(ctx, \"" + elID + "\"" + ", \"" + tempSourceMsp + "\"" + ", \""
                        + tempTargetMsp + "\"" + ", \"\"" + ", DISABLE, \"" + docuType + "\")\n";
            } else {
                initFunc += "\tcc.CreateGateway(ctx, \"" + elID + "\", DISABLE)\n";
            }
            // }
        }

        initFunc += "\n\tisInited = true\n" +
                "\n" +
                "\tstub.SetEvent(\"initContractEvent\", []byte(\"Contract has been initialized successfully\"))\n" +
                // "\tcc." + lowercaseFirstChar(tempStartElement) + "(ctx)\n" +
                "\treturn nil\n" +
                "}\n";

        System.out.println(ffiJsonFile);

        ffiJsonFile = "{\n" +
                "  \"namespace\": \"default\",\n" +
                "  \"name\": \"message_transfer\",\n" +
                "  \"description\": \"Spec interface for the message-transfer-basic golang chaincode\",\n" +
                "  \"version\": \"1.0\",\n" +
                "  \"methods\": [\n" +
                "    {\n" +
                "      \"name\": \"GetAllMessages\",\n" +
                "      \"pathname\": \"\",\n" +
                "      \"description\": \"\",\n" +
                "      \"params\": [],\n" +
                "      \"returns\": [\n" +
                "        {\n" +
                "          \"name\": \"\",\n" +
                "          \"schema\": {\n" +
                "            \"type\": \"array\",\n" +
                "            \"details\": {\n" +
                "              \"type\": \"object\",\n" +
                "              \"properties\": {\n" +
                "                \"type\": \"string\"\n" +
                "              }\n" +
                "            }\n" +
                "          }\n" +
                "        }\n" +
                "      ]\n" +
                "    },\n" +
                "    {\n" +
                "      \"name\": \"GetAllGateways\",\n" +
                "      \"pathname\": \"\",\n" +
                "      \"description\": \"\",\n" +
                "      \"params\": [],\n" +
                "      \"returns\": [\n" +
                "        {\n" +
                "          \"name\": \"\",\n" +
                "          \"schema\": {\n" +
                "            \"type\": \"array\",\n" +
                "            \"details\": {\n" +
                "              \"type\": \"object\",\n" +
                "              \"properties\": {\n" +
                "                \"type\": \"string\"\n" +
                "              }\n" +
                "            }\n" +
                "          }\n" +
                "        }\n" +
                "      ]\n" +
                "    },\n" +
                "    {\n" +
                "      \"name\": \"GetAllActionEvents\",\n" +
                "      \"pathname\": \"\",\n" +
                "      \"description\": \"\",\n" +
                "      \"params\": [],\n" +
                "      \"returns\": [\n" +
                "        {\n" +
                "          \"name\": \"\",\n" +
                "          \"schema\": {\n" +
                "            \"type\": \"array\",\n" +
                "            \"details\": {\n" +
                "              \"type\": \"object\",\n" +
                "              \"properties\": {\n" +
                "                \"type\": \"string\"\n" +
                "              }\n" +
                "            }\n" +
                "          }\n" +
                "        }\n" +
                "      ]\n" +
                "    },\n" +
                "{\n" +
                "      \"name\": \"InitLedger\",\n" +
                "      \"pathname\": \"\",\n" +
                "      \"description\": \"\",\n" +
                "      \"params\": [" +
                "],\n" +
                "      \"returns\": []\n" +
                "    }" + ffiJsonFile
                + "\n]\n}";

        // return intro + constr + other;
        return intro + consFunc + initFunc;
    }

    private String lastFunctions() { // 可以处理
        String descr = " function enable(string memory _taskID) internal {\n" +
                "	elements[position[_taskID]].status=State.ENABLED; }\n"
                // + " emit stateChanged(counter++);\r\n" + "}\r\n" + "\r\n"
                + "    function disable(string memory _taskID) internal { elements[position[_taskID]].status=State.DISABLED; }\r\n"
                + "\r\n"
                + "    function done(string memory _taskID) internal { elements[position[_taskID]].status=State.DONE; "
                +
                "			emit functionDone(_taskID);\n" +
                "		 }\r\n"
                + "   \r\n"
                + "    function getCurrentState()public view  returns(Element[] memory, StateMemory memory){\r\n"
                + "        // emit stateChanged(elements, currentMemory);\r\n"
                + "        return (elements, currentMemory);\r\n" + "    }\r\n" + "    \r\n"
                + "    function compareStrings (string memory a, string memory b) internal pure returns (bool) { \r\n"
                + "        return keccak256(abi.encode(a)) == keccak256(abi.encode(b)); \r\n" + "    }\n}";

        return descr;
    }

    // public static String projectPath = System.getenv("ChorChain");
    // //尝试获取名为ChorChain的环境变量的值
    // public static String projectPath =
    // "D:/CS/projects/blockchain/chaincode-go-bpmn/chaincode";
    public static String projectPath = "src/main/java/com/hit/example";

    private static void fileAll(String fileName) throws IOException, Exception { // File.separator来确保路径在不同操作系统中的兼容性
        FileWriter wChor = new FileWriter(new File(projectPath + File.separator + parseName(fileName, ".go")));
        BufferedWriter bChor = new BufferedWriter(wChor);
        bChor.write(choreographyFile);
        bChor.flush();
        bChor.close();
        // System.out.println("Solidity contract created.");

    }

    private static void fileAllResponse(String fileName) throws IOException, Exception { // File.separator来确保路径在不同操作系统中的兼容性
        FileWriter wChor = new FileWriter(new File(projectPath + File.separator + parseName(fileName, ".go")));
        BufferedWriter bChor = new BufferedWriter(wChor);
        bChor.write(choreographyFile);
        bChor.flush();
        bChor.close();
        // System.out.println("Solidity contract created.");

    }

    public static String parseName(String name, String extension) {
        String[] oldName = name.split("\\.");

        String newName = oldName[0] + extension;
        return newName;
    }

    public void getParticipants() {
        Collection<Participant> parti = modelInstance.getModelElementsByType(Participant.class);
        for (Participant p : parti) {
            if (p.getName() != null && p.getName().length() > 0 && p.getName() != "") {
                partecipants.add(p.getName());
            }
        }
        participantsWithoutDuplicates = new ArrayList<>(new HashSet<>(partecipants)); // 技巧，去除重复元素
    }

    public Map<String, String> getParticipantIdName() {
        Collection<Participant> parti = modelInstance.getModelElementsByType(Participant.class);
        Map<String, String> participantIdName = new HashMap<>();
        parti.stream().forEach(p -> {
            participantIdName.put(p.getId(), p.getName());
        });
        return participantIdName;
    }

    // public void FlowNodeSearch(List<String> optionalRoles, List<String>
    // mandatoryRoles) {
    public void FlowNodeSearch() {
        // check for all SequenceFlow elements in the BPMN model
        for (SequenceFlow flow : modelInstance.getModelElementsByType(SequenceFlow.class)) {
            // node to be processed, created by the target reference of the sequence flow
            ModelElementInstance node = modelInstance.getModelElementById(flow.getAttributeValue("targetRef"));

            // node containing the source of the flow, useful to get the start element
            ModelElementInstance start = modelInstance.getModelElementById(flow.getAttributeValue("sourceRef"));
            // 开始事件
            if (start instanceof StartEvent) {
                // checking and processing all the outgoing nodes
                for (SequenceFlow outgoing : ((StartEvent) start).getOutgoing()) {
                    ModelElementInstance nextNode = modelInstance
                            .getModelElementById(outgoing.getAttributeValue("targetRef"));

                    start.setAttributeValue("name", "startEvent_" + startCounter);
                    startCounter++;
                    nodeSet.add(start.getAttributeValue("id"));
                    // mergeMap(start.getAttributeValue("id"), "internal");
                    elementsID.add(start.getAttributeValue("id"));
                    // roleFortask.add("internal");
                    tasks.add(start.getAttributeValue("name"));

                    startEventAdd = start.getAttributeValue("id");

                    String descr = "func (cc *SmartContract) " + lowercaseFirstChar(parseSid(getNextId(start, false)))
                            + "(ctx contractapi.TransactionContextInterface) error { \n"
                            + "	stub := ctx.GetStub()\n\tactionEvent, err := cc.ReadEvent(ctx, \""
                            + start.getAttributeValue("id") + "\")\n"
                            + "\tif err != nil {\n" +
                            "\t\treturn err\n" +
                            "\t}\n\n"
                            + "\tif actionEvent.EventState != ENABLE {\n" +
                            "\t\terrorMessage := fmt.Sprintf(\"Event state %s is not allowed\", actionEvent.EventID)\n"
                            +
                            "\t\tfmt.Println(errorMessage)\n" +
                            "\t\treturn fmt.Errorf(errorMessage)\n" +
                            "\t}\n\n"
                            + "\tcc.ChangeEventState(ctx, \"" + start.getAttributeValue("id") + "\", DONE)\n"
                            + "\tstub.SetEvent(\"" + start.getAttributeValue("id")
                            + "\", []byte(\"Contract has been started successfully\"))\n\n";
                    if (nextNode instanceof Gateway)
                        descr += "\tcc.ChangeGtwState(ctx, \"" + getNextId(nextNode, false) + "\", ENABLE)\n"
                        // + "\tcc." + lowercaseFirstChar(parseSid(nextNode.getAttributeValue("id"))) +
                        // "(ctx)\n\n"
                                + "\treturn nil\n}\n\n";
                    else
                        descr += "\tcc.ChangeMsgState(ctx, \"" + getNextId(nextNode, false)
                                + "\", ENABLE)\n\treturn nil\n}\n\n";

                    choreographyFile += descr;

                    ffiJsonFile += ",\n{\n" +
                            "      \"name\": \"" + parseSid(parseSid(getNextId(start, false))) + "\",\n" +
                            "      \"pathname\": \"\",\n" +
                            "      \"description\": \"\",\n" +
                            "      \"params\": [],\n" +
                            "      \"returns\": []\n" +
                            "    }";
                }
            }
            // 为排他网关
            if (node instanceof ExclusiveGateway && !nodeSet.contains(getNextId(node, false))) {
                if (node.getAttributeValue("name") == null) {
                    node.setAttributeValue("name", "exclusiveGateway_" + xorCounter);
                    xorCounter++;
                }

                nodeSet.add(getNextId(node, false));
                elementsID.add(getNextId(node, false));
                // roleFortask.add("internal");
                // mergeMap(getNextId(node, false), "internal");
                tasks.add(node.getAttributeValue("name"));

                String descr = "func (cc *SmartContract) " + lowercaseFirstChar(parseSid(getNextId(node, false)))
                        + "(ctx contractapi.TransactionContextInterface) error { \n"
                        + "	stub := ctx.GetStub()\n\tgtw, err := cc.ReadGtw(ctx, \""
                        + lowercaseFirstChar(parseSid(getNextId(node, false))) + "\")\n"
                        + "\tif err != nil {\n" +
                        "\t\treturn err\n" +
                        "\t}\n\n"
                        + "\tif gtw.GatewayState != ENABLE {\n" +
                        "\t\terrorMessage := fmt.Sprintf(\"Gateway state %s is not allowed\", gtw.GatewayID)\n" +
                        "\t\tfmt.Println(errorMessage)\n" +
                        "\t\treturn fmt.Errorf(errorMessage)\n" +
                        "\t}\n\n"
                        + "\tcc.ChangeGtwState(ctx, \"" + lowercaseFirstChar(parseSid(getNextId(node, false)))
                        + "\", DONE)\n"
                        + "\tstub.SetEvent(\"" + lowercaseFirstChar(parseSid(getNextId(node, false)))
                        + "\", []byte(\"ExclusiveGateway has been done\"))\n\n";
                int countIf = 0;
                for (SequenceFlow outgoing : ((ExclusiveGateway) node).getOutgoing()) { // 向下转型
                    ModelElementInstance nextElement = modelInstance
                            .getModelElementById(outgoing.getAttributeValue("targetRef"));
                    if (outgoing.getAttributeValue("name") != null) {
                        String condition = "";
                        if (countIf > 0) {
                            condition = "else if ";
                        } else {
                            condition = "if ";
                        }

                        // 注意：下一个不是message！ 是编排任务
                        descr += condition + addCompareString(outgoing.getAttributeValue("name")) + " {\n";
                        if (nextElement instanceof Gateway) {
                            descr += "        cc.ChangeGtwState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        } else if (nextElement instanceof EndEvent) {
                            descr += "        cc.ChangeEventState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        } else if (nextElement instanceof Message
                                || nextElement.getAttributeValue("id").startsWith("ChoreographyTask")) {
                            descr += "        cc.ChangeMsgState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        }

                        if (nextElement instanceof Gateway || nextElement instanceof EndEvent) {
                            descr += "cc." + lowercaseFirstChar(parseSid(getNextId(nextElement, false))) + "(ctx) \n";
                        }
                        countIf++;
                        descr += "} ";

                    } else {// 无name,则直接enable（一般只有一个流）
                        if (nextElement instanceof Gateway) {
                            descr += "        cc.ChangeGtwState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        } else if (nextElement instanceof EndEvent) {
                            descr += "        cc.ChangeEventState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        } else if (nextElement instanceof Message
                                || nextElement.getAttributeValue("id").startsWith("ChoreographyTask")) {
                            descr += "        cc.ChangeMsgState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        }

                        // if (nextElement instanceof Gateway || nextElement instanceof EndEvent) {
                        // descr += "cc." + lowercaseFirstChar(parseSid(getNextId(nextElement, false)))
                        // + "(ctx) \n";
                        // }
                        // descr += "} ";
                    }

                }

                descr += "\n\treturn nil\n}\n\n";
                choreographyFile += descr;

                ffiJsonFile += ",\n{\n" +
                        "      \"name\": \"" + parseSid(getNextId(node, false)) + "\",\n" +
                        "      \"pathname\": \"\",\n" +
                        "      \"description\": \"\",\n" +
                        "      \"params\": [],\n" +
                        "      \"returns\": []\n" +
                        "    }";

                // 为基于事件网关
            } else if (node instanceof EventBasedGateway && !nodeSet.contains(getNextId(node, false))) {

                if (node.getAttributeValue("name") == null) {
                    node.setAttributeValue("name", "eventBasedGateway_" + eventBasedCounter);
                    eventBasedCounter++;
                }
                nodeSet.add(getNextId(node, false));
                elementsID.add(getNextId(node, false));
                // roleFortask.add("internal");
                // mergeMap(getNextId(node, false), "internal");
                tasks.add(node.getAttributeValue("name"));

                String descr = "func (cc *SmartContract) " + lowercaseFirstChar(parseSid(getNextId(node, false)))
                        + "(ctx contractapi.TransactionContextInterface) error { \n"
                        + "	stub := ctx.GetStub()\n\tgtw, err := cc.ReadGtw(ctx, \""
                        + lowercaseFirstChar(parseSid(getNextId(node, false))) + "\")\n"
                        + "\tif err != nil {\n" +
                        "\t\treturn err\n" +
                        "\t}\n\n"
                        + "\tif gtw.GatewayState != ENABLE {\n" +
                        "\t\terrorMessage := fmt.Sprintf(\"Gateway state %s is not allowed\", gtw.GatewayID)\n" +
                        "\t\tfmt.Println(errorMessage)\n" +
                        "\t\treturn fmt.Errorf(errorMessage)\n" +
                        "\t}\n\n"
                        + "\tcc.ChangeGtwState(ctx, \"" + lowercaseFirstChar(parseSid(getNextId(node, false)))
                        + "\", DONE)\n"
                        + "\tstub.SetEvent(\"" + lowercaseFirstChar(parseSid(getNextId(node, false)))
                        + "\", []byte(\"EventbasedGateway has been done\"))\n\n";

                for (SequenceFlow outgoing : ((EventBasedGateway) node).getOutgoing()) {
                    ModelElementInstance nextElement = modelInstance
                            .getModelElementById(outgoing.getAttributeValue("targetRef"));
                    if (nextElement instanceof Gateway) {
                        descr += "        cc.ChangeGtwState(ctx, \"" + getNextId(nextElement, false)
                                + "\" ,ENABLE)\n\n";
                    } else if (nextElement instanceof EndEvent) {
                        descr += "        cc.ChangeEventState(ctx, \"" + getNextId(nextElement, false)
                                + "\" ,ENABLE)\n\n";
                    } else if (nextElement instanceof Message
                            || nextElement.getAttributeValue("id").startsWith("ChoreographyTask")) {
                        descr += "        cc.ChangeMsgState(ctx, \"" + getNextId(nextElement, false)
                                + "\" ,ENABLE)\n\n";
                    }
                }

                descr += "\nreturn nil\n}\n\n";
                choreographyFile += descr;

                ffiJsonFile += ",\n{\n" +
                        "      \"name\": \"" + parseSid(getNextId(node, false)) + "\",\n" +
                        "      \"pathname\": \"\",\n" +
                        "      \"description\": \"\",\n" +
                        "      \"params\": [],\n" +
                        "      \"returns\": []\n" +
                        "    }";

                // 为平行网关
            } else if (node instanceof ParallelGateway && !nodeSet.contains(getNextId(node, false))) {

                if (node.getAttributeValue("name") == null) {
                    node.setAttributeValue("name", "parallelGateway_" + parallelCounter);
                    parallelCounter++;
                }
                nodeSet.add(getNextId(node, false));
                elementsID.add(getNextId(node, false));
                // roleFortask.add("internal");
                // mergeMap(getNextId(node, false), "internal");
                tasks.add(node.getAttributeValue("name"));

                String descr = "func (cc *SmartContract) " + lowercaseFirstChar(parseSid(getNextId(node, false)))
                        + "(ctx contractapi.TransactionContextInterface) error { \n"
                        + "	stub := ctx.GetStub()\n\tgtw, err := cc.ReadGtw(ctx, \"" + start.getAttributeValue("id")
                        + "\")\n"
                        + "\tif err != nil {\n" +
                        "\t\treturn err\n" +
                        "\t}\n\n"
                        + "\tif gtw.GatewayState != ENABLE {\n" +
                        "\t\terrorMessage := fmt.Sprintf(\"Gateway state %s is not allowed\", gtw.GatewayID)\n" +
                        "\t\tfmt.Println(errorMessage)\n" +
                        "\t\treturn fmt.Errorf(errorMessage)\n" +
                        "\t}\n\n"
                        + "\tcc.ChangeGtwState(ctx, \"" + lowercaseFirstChar(parseSid(getNextId(node, false)))
                        + "\", DONE)\n"
                        + "\tstub.SetEvent(\"" + lowercaseFirstChar(parseSid(getNextId(node, false)))
                        + "\", []byte(\"Gateway has been done\"))\n\n";

                // 可能会有多对多的情况

                // if the size of incoming nodes is 1 -> flows split（一对多）
                if (((ParallelGateway) node).getIncoming().size() == 1) {
                    for (SequenceFlow outgoing : ((ParallelGateway) node).getOutgoing()) {
                        ModelElementInstance nextElement = modelInstance
                                .getModelElementById(outgoing.getAttributeValue("targetRef"));

                        if (nextElement instanceof Gateway) {
                            descr += "        cc.ChangeGtwState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        } else if (nextElement instanceof EndEvent) {
                            descr += "        cc.ChangeEventState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        } else if (nextElement instanceof Message
                                || nextElement.getAttributeValue("id").startsWith("ChoreographyTask")) {
                            descr += "        cc.ChangeMsgState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        }

                        // if (nextElement instanceof Gateway || nextElement instanceof EndEvent) {
                        // descr += "cc."+lowercaseFirstChar(parseSid(getNextId(nextElement, false))) +
                        // "() \n";
                        // }
                    }
                    descr += "\nreturn nil\n}\n\n";
                    choreographyFile += descr;

                    // if the size of the outgoing nodes is 1 -> flows converging(多对一)
                } else if (((ParallelGateway) node).getOutgoing().size() == 1) {
                    descr += "\tif ";
                    int lastCounter = 0;
                    for (SequenceFlow incoming : ((ParallelGateway) node).getIncoming()) {
                        lastCounter++;
                        ModelElementInstance prevElement = modelInstance
                                .getModelElementById(incoming.getAttributeValue("sourceRef"));

                        if (prevElement instanceof Gateway) {
                            descr += "func() bool { gtw, err := cc.ReadGtw(ctx, \"" + getNextId(prevElement, false)
                                    + "\"); return err == nil && gtw.GatewayState == DONE }() ";
                        } else if (prevElement instanceof EndEvent) {
                            descr += "func() bool { event, err := cc.ReadEvent(ctx, \"" + getNextId(prevElement, false)
                                    + "\"); return err == nil && event.EventState == DONE }() ";
                        } else if (prevElement instanceof Message // TWOWAY 可能会有问题
                                || prevElement.getAttributeValue("id").startsWith("ChoreographyTask")) {
                            ChoreographyTask task = new ChoreographyTask((ModelElementInstanceImpl) node,
                                    modelInstance);
                            if (task.getType() == ChoreographyTask.TaskType.TWOWAY) {
                                descr += "func() bool { msg, err := cc.ReadMsg(ctx, \"" + getNextId(prevElement, true)
                                        + "\"); return err == nil && msg.MsgState == DONE }() ";
                            } else if (task.getType() == ChoreographyTask.TaskType.ONEWAY) {
                                descr += "func() bool { msg, err := cc.ReadMsg(ctx, \"" + getNextId(prevElement, false)
                                        + "\"); return err == nil && msg.MsgState == DONE }() ";
                            }

                        }

                        if (lastCounter == ((ParallelGateway) node).getIncoming().size()) {
                            descr += "";
                        } else {
                            descr += "&& ";
                        }
                    }
                    descr += " { \n";
                    for (SequenceFlow outgoing : ((ParallelGateway) node).getOutgoing()) {
                        ModelElementInstance nextElement = modelInstance
                                .getModelElementById(outgoing.getAttributeValue("targetRef"));

                        if (nextElement instanceof Gateway) {
                            descr += "        cc.ChangeGtwState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        } else if (nextElement instanceof EndEvent) {
                            descr += "        cc.ChangeEventState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        } else if (nextElement instanceof Message
                                || nextElement.getAttributeValue("id").startsWith("ChoreographyTask")) {
                            descr += "        cc.ChangeMsgState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        }

                        // if (nextElement instanceof Gateway || nextElement instanceof EndEvent) {
                        // descr += "cc."+lowercaseFirstChar(parseSid(getNextId(nextElement, false))) +
                        // "(); \n";
                        // }
                        descr += "}\nreturn nil\n} \n\n";
                        choreographyFile += descr;
                    }
                }
                ffiJsonFile += ",\n{\n" +
                        "      \"name\": \"" + parseSid(getNextId(node, false)) + "\",\n" +
                        "      \"pathname\": \"\",\n" +
                        "      \"description\": \"\",\n" +
                        "      \"params\": [],\n" +
                        "      \"returns\": []\n" +
                        "    }";

                // 为结束事件
            } else if (node instanceof EndEvent && !nodeSet.contains(getNextId(node, false))) {
                if (node.getAttributeValue("name") == null) {
                    node.setAttributeValue("name", "endEvent_" + endEventCounter);
                    endEventCounter++;
                }
                nodeSet.add(getNextId(node, false));
                elementsID.add(getNextId(node, false));
                tasks.add(node.getAttributeValue("name"));

                String descr = "func (cc *SmartContract) " + lowercaseFirstChar(parseSid(getNextId(node, false)))
                        + "(ctx contractapi.TransactionContextInterface) error { \n"
                        + "	stub := ctx.GetStub()\n\tevent, err := cc.ReadEvent(ctx, \"" + node.getAttributeValue("id")
                        + "\")\n"
                        + "\tif err != nil {\n" +
                        "\t\treturn err\n" +
                        "\t}\n\n"
                        + "\tif event.EventState != ENABLE {\n" +
                        "\t\terrorMessage := fmt.Sprintf(\"Event state %s is not allowed\", event.EventID)\n" +
                        "\t\tfmt.Println(errorMessage)\n" +
                        "\t\treturn fmt.Errorf(errorMessage)\n" +
                        "\t}\n\n"
                        + "\tcc.ChangeEventState(ctx, \"" + node.getAttributeValue("id") + "\", DONE)\n"
                        + "\tstub.SetEvent(\"" + node.getAttributeValue("id")
                        + "\", []byte(\"EndEvent has been done\"))\n\treturn nil\n}\n\n";
                choreographyFile += descr;

                ffiJsonFile += ",\n{\n" +
                        "      \"name\": \"" + parseSid(getNextId(node, false)) + "\",\n" +
                        "      \"pathname\": \"\",\n" +
                        "      \"description\": \"\",\n" +
                        "      \"params\": [],\n" +
                        "      \"returns\": []\n" +
                        "    }";

                // 为普通含消息的编排任务
            } else if (node instanceof ModelElementInstanceImpl && !(node instanceof EndEvent)
                    && !(node instanceof ParallelGateway) && !(node instanceof ExclusiveGateway)
                    && !(node instanceof EventBasedGateway) && (checkTaskPresence(getNextId(node, false)) == false)) {

                boolean taskNull = false;
                nodeSet.add(getNextId(node, false));

                request = ""; //
                response = "";

                String descr = "";
                Participant participant = null;
                String participantName = "";
                ChoreographyTask task = new ChoreographyTask((ModelElementInstanceImpl) node, modelInstance); // 该ModelElementInstance接口能否安全地向下转型为实例类？
                getRequestAndResponse(task);

                participant = modelInstance.getModelElementById(task.getInitialParticipant().getId());

                participantName = participant.getAttributeValue("name");

                String[] req = response.split(" ");
                String ret = ""; // 目前看暂时没用
                String call = "";
                String eventBlock = ""; // 之后被加末尾的片段（基于事件阻塞-使状态disable

                if (start instanceof EventBasedGateway) {
                    for (SequenceFlow block : ((EventBasedGateway) start).getOutgoing()) {
                        ModelElementInstance nextElement = modelInstance
                                .getModelElementById(block.getAttributeValue("targetRef"));
                        if (!(getNextId(nextElement, false).equals(getNextId(node, false)))) {

                            if (nextElement instanceof Gateway) {
                                eventBlock += "        cc.ChangeGtwState(ctx, \"" + getNextId(nextElement, false)
                                        + "\" ,DISABLE)\n\n";
                            } else if (nextElement instanceof EndEvent) {
                                eventBlock += "        cc.ChangeEventState(ctx, \"" + getNextId(nextElement, false)
                                        + "\" ,DISABLE)\n\n";
                            } else if (nextElement instanceof Message
                                    || nextElement.getAttributeValue("id").startsWith("ChoreographyTask")) {
                                eventBlock += "        cc.ChangeMsgState(ctx, \"" + getNextId(nextElement, false)
                                        + "\" ,DISABLE)\n\n";
                            }
                        }
                    }
                }

                if (task.getType() == ChoreographyTask.TaskType.ONEWAY) { // 没有response
                    // System.out.println("Task � 1 way");
                    taskNull = false;
                    // String pName = getRole(participantName, optionalRoles, mandatoryRoles);

                    descr += "func (cc *SmartContract) " + parseSid(getNextId(node, false)) + "_Send"
                            + "(ctx contractapi.TransactionContextInterface, fireflyTranID string"
                            + extractGatewayGuards(getNextId(node, false)) + ") error {\n" // 这里需要获得对应msgid的参数（前面的exclusicvegateway需要进行一定的参数存储
                            + "	stub := ctx.GetStub()\n\tmsg, err := cc.ReadMsg(ctx, \"" + getNextId(node, false)
                            + "\")\n"
                            + "\tif err != nil {\n" +
                            "\t\treturn err\n" +
                            "\t}\n\n"
                            + "\tclientIdentity := ctx.GetClientIdentity()\n" +
                            "\tclientMspID, _ := clientIdentity.GetMSPID()\n" // 检查权限
                            + "\tif clientMspID != msg.SendMspID {\n" +
                            "\t\terrorMessage := fmt.Sprintf(\"Msp denied\")\n" +
                            "\t\tfmt.Println(errorMessage)\n" +
                            "\t\treturn errors.New(fmt.Sprintf(\"Msp denied\"))\n" +
                            "\t}\n"
                            + "\tif msg.MsgState != ENABLE {\n" +
                            "\t\terrorMessage := fmt.Sprintf(\"Event state %s is not allowed\", msg.MessageID)\n" +
                            "\t\tfmt.Println(errorMessage)\n" +
                            "\t\treturn fmt.Errorf(errorMessage)\n" +
                            "\t}\n\n" // getAttributeValue可能需要改为nextid
                            // + "\tcc.ChangeMsgState(ctx, \"" +node.getAttributeValue("id")+ "\",
                            // WAITFORCONFIRM)\n" //变为 WAITFORCONFIRM 状态
                            // + "\tmsg, _ = cc.ReadMsg(ctx, \""+ node.getAttributeValue("id")+"\")\n"
                            + "\tmsg.MsgState = WAITFORCONFIRM\n"
                            + "\tmsg.FireflyTranID = fireflyTranID\n"
                            + "\tmsgJSON, _ := json.Marshal(msg)\n\tstub.PutState(\"" + getNextId(node, false)
                            + "\", msgJSON)\n\t"
                            + "\tstub.SetEvent(\"" + node.getAttributeValue("id")
                            + "\", []byte(\"Message wait for confirming\"))\n\n"
                            + storageToMemory(getNextId(node, false)) + eventBlock; // 存储到内存中

                    // descr += " require(elements[position[\"" + getNextId(node, false)
                    // + "\"]].status==State.ENABLED); \n" + " done(\"" + getNextId(node, false) +
                    // "\");\n"
                    // + addToMemory(request) + eventBlock;

                    // confirm方法 （可能要移到下面） ++++++++++++++++++++++++++++
                    // descr += "function (cc *SmartContract) " + parseSid(getNextId(node, false)) +
                    // "_Confirm" + "(ctx contractapi.TransactionContextInterface) error {\n"
                    // + " stub := ctx.GetStub()\n\tmsg, err := cc.ReadMsg(ctx, \""+
                    // node.getAttributeValue("id")+"\")\n"
                    // + "\tif msg.MsgState != WAITFORCONFIRM {\n" +
                    // "\t\terrorMessage := fmt.Sprintf(\"Msg state %s does not allowed\",
                    // msg.MessageID)\n" +
                    // "\t\tfmt.Println(errorMessage)\n" +
                    // "\t\treturn errors.New(fmt.Sprintf(\"Msg state %s does not allowed\",
                    // msg.MessageID))\n" +
                    // "\t}\n"
                    // + "\tclientIdentity := ctx.GetClientIdentity()\n" +
                    // "\tclientMspID, _ := clientIdentity.GetMSPID()\n" +
                    // "\n" +
                    // "\t\terrorMessage := fmt.Sprintf(\"Msp denied\")\n" +
                    // "\t\tfmt.Println(errorMessage)\n" +
                    // "\t\treturn errors.New(fmt.Sprintf(\"Msp denied\"))\n" +
                    // "\t}\n\n"
                    // + "\tcc.ChangeMsgState(ctx, \"" +node.getAttributeValue("id")+ "\", DONE)\n"
                    // //变为 WAITFORCONFIRM 状态
                    // + "\tstub.SetEvent(\"" + node.getAttributeValue("id") +"\", []byte(\"Message
                    // has been done\"))\n\n";

                    // addGlobal(request); //按照我们的设计，这两个都得取代

                    // roleFortask.add(participantName);

                } else if (task.getType() == ChoreographyTask.TaskType.TWOWAY) {
                    taskNull = false;

                    // String pName = getRole(participantName, optionalRoles, mandatoryRoles);

                    if (!request.isEmpty()) {
                        // System.out.println("RICHIESTA NON VUOTA");
                        taskNull = false;

                        descr += "func (cc *SmartContract) " + parseSid(getNextId(node, false)) + "_Send"
                                + "(ctx contractapi.TransactionContextInterface, fireflyTranID string"
                                + extractGatewayGuards(getNextId(node, false)) + ") error {\n" // 这里需要获得对应msgid的参数（前面的exclusicvegateway需要进行一定的参数存储
                                + "	stub := ctx.GetStub()\n\tmsg, err := cc.ReadMsg(ctx, \"" + getNextId(node, false)
                                + "\")\n"
                                + "\tif err != nil {\n" +
                                "\t\treturn err\n" +
                                "\t}\n\n"
                                + "\tclientIdentity := ctx.GetClientIdentity()\n" +
                                "\tclientMspID, _ := clientIdentity.GetMSPID()\n" // 检查权限
                                + "\tif clientMspID != msg.SendMspID {\n" +
                                "\t\terrorMessage := fmt.Sprintf(\"Msp denied\")\n" +
                                "\t\tfmt.Println(errorMessage)\n" +
                                "\t\treturn errors.New(fmt.Sprintf(\"Msp denied\"))\n" +
                                "\t}\n\n"
                                + "\tif msg.MsgState != ENABLE {\n" +
                                "\t\terrorMessage := fmt.Sprintf(\"Event state %s is not allowed\", msg.MessageID)\n" +
                                "\t\tfmt.Println(errorMessage)\n" +
                                "\t\treturn fmt.Errorf(errorMessage)\n" +
                                "\t}\n\n"
                                // + "\tcc.ChangeMsgState(ctx, \"" +getNextId(node, false)+ "\",
                                // WAITFORCONFIRM)\n" //变为 WAITFORCONFIRM 状态
                                // + "\tmsg, _ = cc.ReadMsg(ctx, \""+ getNextId(node, false)+"\")\n"
                                + "\tmsg.MsgState = WAITFORCONFIRM\n"
                                + "\tmsg.FireflyTranID = fireflyTranID\n"
                                + "\tmsgJSON, _ := json.Marshal(msg)\n\tstub.PutState(\"" + getNextId(node, false)
                                + "\", msgJSON)\n"
                                + "\tstub.SetEvent(\"" + getNextId(node, false)
                                + "\", []byte(\"Message wait for confirming\"))\n\n"
                                // + "\tcc.ChangeMsgState(ctx, \"" + getNextId(node, true)+ "\",
                                // WAITFORCONFIRM)\n\t"
                                + storageToMemory(getNextId(node, false)) + eventBlock + "\nreturn nil\n}\n\n"; // 这里先闭上（因为只有response有后面taskNull
                                                                                                                // ==
                                                                                                                // false
                                                                                                                // 的逻辑,
                        // 上面肯定要换,设计成传messageid

                        descr += "func (cc *SmartContract) " + parseSid(getNextId(node, false)) + "_Complete"
                                + "(ctx contractapi.TransactionContextInterface"
                                // + extractGatewayGuards(getNextId(node, false))
                                + ") error {\n" // 这里需要获得对应msgid的参数（前面的exclusicvegateway需要进行一定的参数存储
                                + "	stub := ctx.GetStub()\n\tmsg, err := cc.ReadMsg(ctx, \"" + getNextId(node, false)
                                + "\")\n"
                                + "\tif err != nil {\n" +
                                "\t\treturn err\n" +
                                "\t}\n\n"
                                + "\tclientIdentity := ctx.GetClientIdentity()\n" +
                                "\tclientMspID, _ := clientIdentity.GetMSPID()\n" // 检查权限
                                + "\tif clientMspID != msg.ReceiveMspID {\n" +
                                "\t\terrorMessage := fmt.Sprintf(\"Msp denied\")\n" +
                                "\t\tfmt.Println(errorMessage)\n" +
                                "\t\treturn errors.New(fmt.Sprintf(\"Msp denied\"))\n" +
                                "\t}\n\n"
                                + "\tif msg.MsgState != WAITFORCONFIRM {\n" +
                                "\t\terrorMessage := fmt.Sprintf(\"Event state %s is not allowed\", msg.MessageID)\n" +
                                "\t\tfmt.Println(errorMessage)\n" +
                                "\t\treturn fmt.Errorf(errorMessage)\n" +
                                "\t}\n\n"
                                + "\tcc.ChangeMsgState(ctx, \"" + getNextId(node, false) + "\", DONE)\n"
                                + "\tstub.SetEvent(\"" + getNextId(node, false)
                                + "\", []byte(\"Message has been done\"))\n\n"
                                + "\tcc.ChangeMsgState(ctx, \"" + getNextId(node, true)
                                + "\", ENABLE)\n\treturn nil\n}\n\n";
                    } else {
                        taskNull = true;
                    }

                    if (!response.isEmpty()) {
                        // System.out.println("RISPOSTA NON VUOTA");
                        taskNull = false;
                        descr += "func (cc *SmartContract) " + parseSid(getNextId(node, true)) + "_Send"
                                + "(ctx contractapi.TransactionContextInterface, fireflyTranID string"
                                + extractGatewayGuards(getNextId(node, true)) + ") error {\n" // 这里需要获得对应msgid的参数（前面的exclusicvegateway需要进行一定的参数存储
                                + "	stub := ctx.GetStub()\n\tmsg, err := cc.ReadMsg(ctx, \"" + getNextId(node, true)
                                + "\")\n"
                                + "\tif err != nil {\n" +
                                "\t\treturn err\n" +
                                "\t}\n\n"
                                + "\tclientIdentity := ctx.GetClientIdentity()\n" +
                                "\tclientMspID, _ := clientIdentity.GetMSPID()\n" // 检查权限
                                + "\tif clientMspID != msg.SendMspID {\n" +
                                "\t\terrorMessage := fmt.Sprintf(\"Msp denied\")\n" +
                                "\t\tfmt.Println(errorMessage)\n" +
                                "\t\treturn errors.New(fmt.Sprintf(\"Msp denied\"))\n" +
                                "\t}\n"
                                + "\tif msg.MsgState != ENABLE {\n" +
                                "\t\terrorMessage := fmt.Sprintf(\"Event state %s is not allowed\", msg.MessageID)\n" +
                                "\t\tfmt.Println(errorMessage)\n" +
                                "\t\treturn fmt.Errorf(errorMessage)\n" +
                                "\t}\n\n"
                                // + "\tcc.ChangeMsgState(ctx, \"" +getNextId(node, true)+ "\",
                                // WAITFORCONFIRM)\n" //变为 WAITFORCONFIRM 状态
                                // + "msg, _ = cc.ReadMsg(ctx, \""+ getNextId(node, true)+"\")\n"
                                + "\tmsg.MsgState = WAITFORCONFIRM\n"
                                + "\tmsg.FireflyTranID = fireflyTranID\n"
                                + "\tmsgJSON, _ := json.Marshal(msg)\n\tstub.PutState(\"" + getNextId(node, true)
                                + "\", msgJSON)\n"
                                + "\tstub.SetEvent(\"" + getNextId(node, true)
                                + "\", []byte(\"Message wait for confirming\"))\n\n"
                                + storageToMemory(getNextId(node, true)) + eventBlock;

                        // addGlobal(response);

                    } else {
                        taskNull = true;
                    }

                }

                choreographyFile += descr;
                descr = "\t";
                // checking the outgoing elements from the task
                // System.out.println("TASK NULL � : " + taskNull);
                if (taskNull == false) { // 补上enable
                    // 修改添加complete方法，这个taskNull放到编排任务的最后一个message confirm 来判断

                    String messageElementName = null;
                    if (task.getType() == ChoreographyTask.TaskType.ONEWAY) {
                        messageElementName = getNextId(node, false);
                    } else if (task.getType() == ChoreographyTask.TaskType.TWOWAY) {
                        messageElementName = getNextId(node, true);
                    }

                    // ffi逻辑补充在这里

                    if (task.getType() == ChoreographyTask.TaskType.ONEWAY) {
                        ffiJsonFile += ",\n{\n" +
                                "      \"name\": \"" + parseSid(getNextId(node, false)) + "_Send" + "\",\n" +
                                "      \"pathname\": \"\",\n" +
                                "      \"description\": \"\",\n" +
                                "      \"params\": [\n" +
                                "        {\n" +
                                "          \"name\": \"fireflyTranID\",\n" +
                                "          \"schema\": {\n" +
                                "            \"type\": \"string\"\n" +
                                "          }\n" +
                                "        }\n" +
                                // 需要添加ffi参数逻辑
                                extractFFIJsonGatewayGuards(getNextId(node, false)) +
                                "      ],\n" +
                                "      \"returns\": []\n" +
                                "    }";

                        ffiJsonFile += ",\n{\n" +
                                "      \"name\": \"" + parseSid(messageElementName) + "_Complete" + "\",\n" +
                                "      \"pathname\": \"\",\n" +
                                "      \"description\": \"\",\n" +
                                "      \"params\": [],\n" +
                                // " {\n" +
                                // " \"name\": \"fireflyTranID\",\n" +
                                // " \"schema\": {\n" +
                                // " \"type\": \"string\"\n" +
                                // " }\n" +
                                // " }\n" +
                                //// extractFFIJsonGatewayGuards(getNextId(node, false)) +
                                // " ],\n" +
                                "      \"returns\": []\n" +
                                "    }";

                    } else if (task.getType() == ChoreographyTask.TaskType.TWOWAY) {
                        if (!request.isEmpty()) {
                            ffiJsonFile += ",\n{\n" +
                                    "      \"name\": \"" + parseSid(getNextId(node, false)) + "_Send" + "\",\n" +
                                    "      \"pathname\": \"\",\n" +
                                    "      \"description\": \"\",\n" +
                                    "      \"params\": [\n" +
                                    "        {\n" +
                                    "          \"name\": \"fireflyTranID\",\n" +
                                    "          \"schema\": {\n" +
                                    "            \"type\": \"string\"\n" +
                                    "          }\n" +
                                    "        }\n" +
                                    extractFFIJsonGatewayGuards(getNextId(node, false)) +
                                    "      ],\n" +
                                    "      \"returns\": []\n" +
                                    "    }";

                            ffiJsonFile += ",\n{\n" +
                                    "      \"name\": \"" + parseSid(getNextId(node, false)) + "_Complete" + "\",\n" +
                                    "      \"pathname\": \"\",\n" +
                                    "      \"description\": \"\",\n" +
                                    "      \"params\": [],\n" +
                                    "      \"returns\": []\n" +
                                    "    }";
                        }
                        if (!response.isEmpty()) {
                            ffiJsonFile += ",\n{\n" +
                                    "      \"name\": \"" + parseSid(getNextId(node, true)) + "_Send" + "\",\n" +
                                    "      \"pathname\": \"\",\n" +
                                    "      \"description\": \"\",\n" +
                                    "      \"params\": [\n" +
                                    "        {\n" +
                                    "          \"name\": \"fireflyTranID\",\n" +
                                    "          \"schema\": {\n" +
                                    "            \"type\": \"string\"\n" +
                                    "          }\n" +
                                    "        }\n" +
                                    extractFFIJsonGatewayGuards(getNextId(node, true)) +
                                    "      ],\n" +
                                    "      \"returns\": []\n" +
                                    "    }";

                            ffiJsonFile += ",\n{\n" +
                                    "      \"name\": \"" + parseSid(messageElementName) + "_Complete" + "\",\n" +
                                    "      \"pathname\": \"\",\n" +
                                    "      \"description\": \"\",\n" +
                                    "      \"params\": [],\n" +
                                    "      \"returns\": []\n" +
                                    "    }";
                        }
                    }

                    descr += "\nreturn nil\n}\n\n";
                    descr += "func (cc *SmartContract) " + parseSid(messageElementName) + "_Complete"
                            + "(ctx contractapi.TransactionContextInterface"
                            // + extractGatewayGuards(messageElementName)
                            + ") error {\n" // 这里需要获得对应msgid的参数（前面的exclusicvegateway需要进行一定的参数存储
                            + "	stub := ctx.GetStub()\n\tmsg, err := cc.ReadMsg(ctx, \"" + messageElementName + "\")\n"
                            + "\tif err != nil {\n" +
                            "\t\treturn err\n" +
                            "\t}\n\n"
                            + "\tclientIdentity := ctx.GetClientIdentity()\n" +
                            "\tclientMspID, _ := clientIdentity.GetMSPID()\n" // 检查权限
                            + "\tif clientMspID != msg.ReceiveMspID {\n" +
                            "\t\terrorMessage := fmt.Sprintf(\"Msp denied\")\n" +
                            "\t\tfmt.Println(errorMessage)\n" +
                            "\t\treturn errors.New(fmt.Sprintf(\"Msp denied\"))\n" +
                            "\t}\n\n"
                            + "\tif msg.MsgState != WAITFORCONFIRM {\n" +
                            "\t\terrorMessage := fmt.Sprintf(\"Event state %s is not allowed\", msg.MessageID)\n" +
                            "\t\tfmt.Println(errorMessage)\n" +
                            "\t\treturn fmt.Errorf(errorMessage)\n" +
                            "\t}\n\n"
                            + "\tcc.ChangeMsgState(ctx, \"" + messageElementName + "\", DONE)\n"
                            + "\tstub.SetEvent(\"" + messageElementName + "\", []byte(\"Message has been done\"))\n\n";

                    for (SequenceFlow out : task.getOutgoing()) {
                        ModelElementInstance nextElement = modelInstance
                                .getModelElementById(out.getAttributeValue("targetRef"));
                        // descr += "\tenable(\"" + getNextId(nextElement, false) + "\");\n";

                        if (nextElement instanceof Gateway) {
                            descr += "\tcc.ChangeGtwState(ctx, \"" + getNextId(nextElement, false) + "\" ,ENABLE)\n\n";
                        } else if (nextElement instanceof EndEvent) {
                            descr += "\tcc.ChangeEventState(ctx, \"" + getNextId(nextElement, false)
                                    + "\" ,ENABLE)\n\n";
                        } else if (nextElement instanceof Message
                                || nextElement.getAttributeValue("id").startsWith("ChoreographyTask")) {
                            descr += "\tcc.ChangeMsgState(ctx, \"" + getNextId(nextElement, false) + "\" ,ENABLE)\n\n";
                        }
                        descr += ret; // 这里好像有错误？

                    }

                }
                descr += "\nreturn nil\n}\t//编排任务的最后一个消息\n\n";
                choreographyFile += descr;
            }

        }
    }

    // public void mergeMap(String id, String role) {
    // taskIdAndRole.put(id, role);
    // }

    public void storageAllMessageParasMap() {
        for (SequenceFlow flow : modelInstance.getModelElementsByType(SequenceFlow.class)) {
            ModelElementInstance node = modelInstance.getModelElementById(flow.getAttributeValue("targetRef"));
            if (node instanceof ModelElementInstanceImpl && !(node instanceof EndEvent)
                    && !(node instanceof ParallelGateway) && !(node instanceof ExclusiveGateway)
                    && !(node instanceof EventBasedGateway) && (checkTaskPresence(getNextId(node, false)) == false)) {

                ChoreographyTask task = new ChoreographyTask((ModelElementInstanceImpl) node, modelInstance);

                Message messageChildElement = modelInstance.getModelElementById(getNextId(node, false));
                if (messageChildElement != null) {
                    for (DomElement childElement : messageChildElement.getDomElement().getChildElements()) {
                        String type = childElement.getLocalName();
                        switch (type) {
                            case "documentation":
                                System.out.println(
                                        childElement.getTextContent() + "!!!!!!!!\n\n\n\n\n\n\n\n\n\n\n!!!!!!");
                                boolean isValid = isValidJson(childElement.getTextContent());
                                System.out.println("Is Valid JSON? " + isValid);

                                // Map<String, String> resultMap =
                                // genson.deserialize(childElement.getTextContent(), Map.class);
                                // messageParasMap.putAll(resultMap);
                                ObjectMapper objectMapper = new ObjectMapper();
                                JsonNode rootNode = null;
                                try {
                                    rootNode = objectMapper.readTree(childElement.getTextContent());
                                    JsonNode propertiesNode = rootNode.get("properties");
                                    if (propertiesNode != null) {
                                        propertiesNode.fields().forEachRemaining(entry -> {
                                            String propertyName = entry.getKey();
                                            JsonNode propertyNode = entry.getValue();

                                            String propertyType = propertyNode.get("type").asText();

                                            String propertyDescription = propertyNode.get("description").asText();
                                            messageParasMap.put(propertyName, propertyType);
                                        });
                                    }

                                } catch (JsonProcessingException e) {
                                    throw new RuntimeException(e);
                                }
                        }
                    }
                }

                if (task.getType() == ChoreographyTask.TaskType.TWOWAY) {
                    Message messageChild2Element = modelInstance.getModelElementById(getNextId(node, true));
                    for (DomElement childElement : messageChild2Element.getDomElement().getChildElements()) {
                        String type = childElement.getLocalName();
                        switch (type) {
                            case "documentation":
                                System.out.println(
                                        childElement.getTextContent() + "!!!!!!!!\n\n\n\n\n\n\n\n\n\n\n!!!!!!");
                                boolean isValid = isValidJson(childElement.getTextContent());
                                System.out.println("Response Is Valid JSON? " + isValid);

                                // Map<String, String> resultMap =
                                // genson.deserialize(childElement.getTextContent(), Map.class);
                                // messageParasMap.putAll(resultMap);
                                ObjectMapper objectMapper = new ObjectMapper();
                                JsonNode rootNode = null;
                                try {
                                    rootNode = objectMapper.readTree(childElement.getTextContent());
                                    JsonNode propertiesNode = rootNode.get("properties");
                                    if (propertiesNode != null) {
                                        propertiesNode.fields().forEachRemaining(entry -> {
                                            String propertyName = entry.getKey();
                                            JsonNode propertyNode = entry.getValue();

                                            String propertyType = propertyNode.get("type").asText();

                                            String propertyDescription = propertyNode.get("description").asText();
                                            messageParasMap.put(propertyName, propertyType);
                                        });
                                    }

                                } catch (JsonProcessingException e) {
                                    throw new RuntimeException(e);
                                }

                        }
                    }
                }
                // System.out.println(messageParasMap);
            }
        }
    }

    public static boolean isValidJson(String jsonString) {
        try {
            new JSONObject(new JSONTokener(jsonString));
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private static String parseSid(String sid) {
        return sid.replace("-", "_");
    }

    // 失效
    private static String lowercaseFirstChar(String input) {
        // if (input == null || input.isEmpty()) {
        // return input;
        // }
        // char[] chars = input.toCharArray();
        // chars[0] = Character.toLowerCase(chars[0]);
        // return new String(chars);
        return input;
    }

    private String extractGatewayGuards(String input) {
        Map<String, String> commonEntries = new HashMap<>();
        Message messageChildElement = modelInstance.getModelElementById(input);
        if (messageChildElement != null) {
            for (DomElement childElement : messageChildElement.getDomElement().getChildElements()) {
                String type = childElement.getLocalName();
                switch (type) {
                    case "documentation":
                        boolean isValid = isValidJson(childElement.getTextContent());
                        System.out.println("Is Valid JSON? " + isValid);

                        // Map<String, String> tempMap =
                        // genson.deserialize(childElement.getTextContent(), Map.class);
                        //
                        //// commonEntries = findCommonEntries(tempMap, messageParasMap);
                        // //messageParasMap应该换，不能是这个，而应该是gatewayMemoryParams
                        // commonEntries = findCommonEntries(tempMap);
                        ObjectMapper objectMapper = new ObjectMapper();
                        Map<String, String> propertiesMap = new HashMap<>();
                        try {
                            JsonNode rootNode = objectMapper.readTree(childElement.getTextContent());
                            JsonNode propertiesNode = rootNode.get("properties");

                            if (propertiesNode != null && propertiesNode.isObject()) {
                                propertiesNode.fields().forEachRemaining(entry -> {
                                    String propertyName = entry.getKey();
                                    JsonNode propertyNode = entry.getValue();

                                    if (propertyNode != null) {
                                        String propertyType = propertyNode.has("type")
                                                ? propertyNode.get("type").asText()
                                                : "";
                                        String propertyDescription = propertyNode.has("description")
                                                ? propertyNode.get("description").asText()
                                                : "";

                                        propertiesMap.put(propertyName, propertyType);
                                    }
                                });
                            }

                        } catch (JsonProcessingException e) {
                            throw new RuntimeException(e);
                        }

                        // Map<String, String> tempMap =
                        // genson.deserialize(childElement.getTextContent(), Map.class);

                        // commonEntries = findCommonEntries(tempMap, messageParasMap);
                        // //messageParasMap应该换，不能是这个，而应该是gatewayMemoryParams
                        commonEntries = findCommonEntries(propertiesMap);

                }
            }
        }

        String resultString = "";
        for (Map.Entry<String, String> entry : commonEntries.entrySet()) {
            resultString += ", " + entry.getKey() + " " + entry.getValue();
        }
        return resultString;

    }

    private String extractFFIJsonGatewayGuards(String input) {
        Map<String, String> commonEntries = new HashMap<>();
        Message messageChildElement = modelInstance.getModelElementById(input);
        if (messageChildElement != null) {
            for (DomElement childElement : messageChildElement.getDomElement().getChildElements()) {
                String type = childElement.getLocalName();
                switch (type) {
                    case "documentation":
                        // Map<String, String> tempMap =
                        // genson.deserialize(childElement.getTextContent(), Map.class);
                        // commonEntries = findCommonEntries(tempMap);
                        ObjectMapper objectMapper = new ObjectMapper();
                        Map<String, String> propertiesMap = new HashMap<>();
                        try {
                            JsonNode rootNode = objectMapper.readTree(childElement.getTextContent());
                            JsonNode propertiesNode = rootNode.get("properties");

                            if (propertiesNode != null && propertiesNode.isObject()) {
                                propertiesNode.fields().forEachRemaining(entry -> {
                                    String propertyName = entry.getKey();
                                    JsonNode propertyNode = entry.getValue();

                                    String propertyType = propertyNode.get("type").asText();
                                    String propertyDescription = propertyNode.get("description").asText();

                                    propertiesMap.put(propertyName, propertyType);
                                });
                            }

                        } catch (JsonProcessingException e) {
                            throw new RuntimeException(e);
                        }

                        commonEntries = findCommonEntries(propertiesMap);

                }
            }
        }

        String resultString = "";
        for (Map.Entry<String, String> entry : commonEntries.entrySet()) {
            resultString += ",\n{\n" +
                    "          \"name\": \"" + entry.getKey() + "\",\n" +
                    "          \"schema\": {\n" +
                    "            \"type\": \"" + goType2JsonType(entry.getValue()) + "\"\n" +
                    "          }\n" +
                    "        }";
        }
        return resultString;
    }

    private String goType2JsonType(String type) {
        if (type.equals("string")) {
            return "string";
        } else if (type.equals("int")) {
            return "integer";
        } else if (type.equals("long")) {
            return "integer";
        } else if (type.equals("float")) {
            return "number";
        } else if (type.equals("double")) {
            return "number";
        } else if (type.equals("bool")) {
            return "boolean";
        }
        return type;
    }

    private static Map<String, String> findCommonEntries(Map<String, String> tempMap) {
        Map<String, String> commonEntries = new HashMap<>();

        for (Map.Entry<String, String> entry : tempMap.entrySet()) {
            String key = entry.getKey();
            String value = entry.getValue();

            if (gatewayMemoryParams.contains(key)) {
                commonEntries.put(key, transfer2GoType(value));
            }
        }

        return commonEntries;
    }

    private static String getNextId(ModelElementInstance nextNode, boolean msg) { // msg用于区分处理请求消息还是响应消息
        String id = "";
        // System.out.println(nextNode.getClass());
        // 非开始、终止事件、非网关
        if (nextNode instanceof ModelElementInstanceImpl && !(nextNode instanceof EndEvent)
                && !(nextNode instanceof ParallelGateway) && !(nextNode instanceof ExclusiveGateway)
                && !(nextNode instanceof EventBasedGateway) && !(nextNode instanceof StartEvent)) {
            ChoreographyTask task = new ChoreographyTask((ModelElementInstanceImpl) nextNode, modelInstance);
            if (task.getRequest() != null && msg == false) {
                // System.out.println("SONO DENTRO GETrEQUEST != NULL");
                MessageFlow requestMessageFlowRef = task.getRequest(); // request和response区别？
                MessageFlow requestMessageFlow = modelInstance.getModelElementById(requestMessageFlowRef.getId());
                // //System.out.println("MESSAGAE FLOW REF ID:" +
                // requestMessageFlowRef.getId());
                Message requestMessage = modelInstance
                        .getModelElementById(requestMessageFlow.getAttributeValue("messageRef"));
                if (requestMessage.getName() != null) {
                    // System.out.println("SONO DENTRO REQUEST.GETNAME != NULL");
                    id = requestMessage.getAttributeValue("id");
                } else {
                    // System.out.println("SONO DENTRO LA RISPOSTA PERCH� REQUEST.GETNAME � NULL");
                    MessageFlow responseMessageFlowRef = task.getResponse();
                    if (responseMessageFlowRef != null) {
                        MessageFlow responseMessageFlow = modelInstance
                                .getModelElementById(responseMessageFlowRef.getId());
                        Message responseMessage = modelInstance
                                .getModelElementById(responseMessageFlow.getAttributeValue("messageRef"));
                        // if(!responseMessage.getAttributeValue("name").isEmpty()) {
                        id = responseMessage.getAttributeValue("id");
                    }

                    // }

                }
            } else if (task.getRequest() == null && msg == false || task.getResponse() != null && msg == true) {
                // System.out.println("SONO DENTRO GETREQUEST == NULL");
                MessageFlow responseMessageFlowRef = task.getResponse();
                MessageFlow responseMessageFlow = modelInstance.getModelElementById(responseMessageFlowRef.getId());
                Message responseMessage = modelInstance
                        .getModelElementById(responseMessageFlow.getAttributeValue("messageRef"));
                if (responseMessage.getName() != null) {
                    id = responseMessage.getAttributeValue("id");
                }

            } //
        } else {
            id = nextNode.getAttributeValue("id");
        }
        // System.out.println("GET ID RETURNS: " + id);
        return id;
    }

    // if比较逻辑（对排他网关输出上的表达式进行解析，获得信息）
    private static String addCompareString(String guards) {
        // String guards = outgoing.getAttributeValue("name");

        String res = "";
        // solidity中字符串不能比较相同，先abi编码哈希值比较是否相同compareStrings
        if (guards.contains("\"")) { // 处理字符串等值比较
            // String[] guardValue = guards.split("==");
            // res = "compareStrings(currentMemory." + guardValue[0] + ", " + guardValue[1]
            // + ")==true";
            res = "cc.currentMemory." + guards;
            String[] guardValue = guards.split("==");
            gatewayMemoryParams.add(guardValue[0]);
        } else if (guards.contains("==")) { // 处理非字符串比较
            res = "cc.currentMemory." + guards;
            String[] guardValue = guards.split("==");
            gatewayMemoryParams.add(guardValue[0]);
        } else if (guards.contains(">=")) { // 好像没有数字相关的处理
            String[] guardValue = guards.split(">=");
            gatewayMemoryParams.add(guardValue[0]);
            res = "cc.currentMemory." + guardValue[0] + ">= cc.currentMemory." + guardValue[1];
        } else if (guards.contains(">")) {
            String[] guardValue = guards.split(">");
            gatewayMemoryParams.add(guardValue[0]);
            res = "cc.currentMemory." + guardValue[0] + "> cc.currentMemory." + guardValue[1];
        } else if (guards.contains("<=")) {
            String[] guardValue = guards.split("<=");
            gatewayMemoryParams.add(guardValue[0]);
            res = "cc.currentMemory." + guardValue[0] + "<= cc.currentMemory." + guardValue[1];
        } else if (guards.contains("<")) {
            String[] guardValue = guards.split("<");
            gatewayMemoryParams.add(guardValue[0]);
            res = "cc.currentMemory." + guardValue[0] + "< cc.currentMemory." + guardValue[1];
        }

        // System.out.println("RESULTT: " + res);
        return res;
    }

    private boolean checkTaskPresence(String sid) {
        // System.out.println(sid);
        boolean isPresent = false;
        for (String id : elementsID) {
            if (sid.equals(id)) {
                isPresent = true;
                return isPresent;
            }
        }
        return isPresent;
    }

    // 往elementsID、tasks中加东西
    public void getRequestAndResponse(ChoreographyTask task) { // task是必定初始化了的，初始化了node和model
        // if there is only the response
        Participant participant = modelInstance.getModelElementById(task.getInitialParticipant().getId());
        String participantName = participant.getAttributeValue("name");

        if (task.getRequest() == null && task.getResponse() != null) {
            // System.out.println("task.getRequest() = null: " + task.getRequest());
            MessageFlow responseMessageFlowRef = task.getResponse();
            MessageFlow responseMessageFlow = modelInstance.getModelElementById(responseMessageFlowRef.getId());
            Message responseMessage = modelInstance
                    .getModelElementById(responseMessageFlow.getAttributeValue("messageRef"));

            if (!responseMessage.getAttributeValue("name").isEmpty()) {
                elementsID.add(responseMessage.getId());
                response = responseMessage.getAttributeValue("name");
                tasks.add(response);
                // roleFortask.add(task.getParticipantRef().getName());
                // mergeMap(responseMessage.getId(), task.getParticipantRef().getName());
            }

        }
        // if there is only the request
        else if (task.getRequest() != null && task.getResponse() == null) {
            MessageFlow requestMessageFlowRef = task.getRequest();
            MessageFlow requestMessageFlow = modelInstance.getModelElementById(requestMessageFlowRef.getId());
            Message requestMessage = modelInstance
                    .getModelElementById(requestMessageFlow.getAttributeValue("messageRef"));
            if (requestMessage != null) {
                if (requestMessage.getAttributeValue("name") != null
                        && !requestMessage.getAttributeValue("name").isEmpty()) { // 检查requestMessage的name属性值是否不是null和空字符串
                    elementsID.add(requestMessage.getId());
                    request = requestMessage.getAttributeValue("name");
                    tasks.add(request);
                    // roleFortask.add(participantName);
                    // mergeMap(requestMessage.getId(), participantName);
                }
            }

        }
        // if there are both
        else { // 凑代码行数？？？？？？
            MessageFlow requestMessageFlowRef = task.getRequest(); // requestMessageFlowRef是requestMessageFlow的引用
            MessageFlow responseMessageFlowRef = task.getResponse();
            MessageFlow requestMessageFlow = modelInstance.getModelElementById(requestMessageFlowRef.getId());
            MessageFlow responseMessageFlow = modelInstance.getModelElementById(responseMessageFlowRef.getId());
            Message requestMessage = modelInstance
                    .getModelElementById(requestMessageFlow.getAttributeValue("messageRef"));
            Message responseMessage = modelInstance
                    .getModelElementById(responseMessageFlow.getAttributeValue("messageRef"));
            if (requestMessage.getAttributeValue("name") != null) { // 检查requestMessage的name属性值是否不是null
                elementsID.add(requestMessage.getId());
                request = requestMessage.getAttributeValue("name");
                tasks.add(request);
                // roleFortask.add(participantName);
                // mergeMap(requestMessage.getId(), participantName);
            }
            if (responseMessage.getAttributeValue("name") != null) {

                elementsID.add(responseMessage.getId());
                response = responseMessage.getAttributeValue("name");
                tasks.add(response);
                // roleFortask.add(task.getParticipantRef().getName());
                // mergeMap(responseMessage.getId(), task.getParticipantRef().getName());
            }

        }

    }

    // checkMand检查调用者（msg.sender）是否具有指定角色的权限，checkOpt类似于checkMand，但这个modifier用于检查可选角色
    public String getRole(String part, List<String> optionalRoles, List<String> mandatoryRoles) {
        String res = "";
        for (int i = 0; i < mandatoryRoles.size(); i++) {

            if ((mandatoryRoles.get(i)).equals(part)) {
                res = "checkMand(roleList[" + i + "]";
                return res;
            }
        }
        for (int o = 0; o < optionalRoles.size(); o++) {
            if ((optionalRoles.get(o)).equals(part)) {
                res = "checkOpt(optionalList[" + o + "]";
                return res;
            }
        }

        return res;
    }

    private static String addMemory(String toParse) { // 需要改成只保留网关参数
        // System.out.println(toParse);
        String n = toParse.replace("string ", "string memory ");
        // String[] tokens = n.split(" ");
        return n;
    }

    // 未完全解读
    private static String addToMemory(String msg) {
        String add = "";
        String n = msg.replace("string", "").replace("uint", "").replace("bool", "").replace(" ", "");
        String r = n.replace(")", "");
        String[] t = r.split("\\(");
        String[] m = t[1].split(",");

        for (String value : m) {

            add += "currentMemory." + value + "=" + value + ";\n";
        }

        return add;
    }

    private String storageToMemory(String input) { // 传msgid
        // 获得 gateway 上必要参数逻辑
        Map<String, String> commonEntries = new HashMap<>();
        Message messageChildElement = modelInstance.getModelElementById(input);
        if (messageChildElement != null) {
            for (DomElement childElement : messageChildElement.getDomElement().getChildElements()) {
                String type = childElement.getLocalName();
                switch (type) {
                    case "documentation":
                        boolean isValid = isValidJson(childElement.getTextContent());
                        System.out.println("Is Valid JSON? " + isValid);

                        // Map<String, String> tempMap =
                        // genson.deserialize(childElement.getTextContent(), Map.class);
                        // commonEntries = findCommonEntries(tempMap);
                        ObjectMapper objectMapper = new ObjectMapper();
                        Map<String, String> propertiesMap = new HashMap<>();
                        try {
                            JsonNode rootNode = objectMapper.readTree(childElement.getTextContent());
                            JsonNode propertiesNode = rootNode.get("properties");

                            if (propertiesNode != null && propertiesNode.isObject()) {
                                propertiesNode.fields().forEachRemaining(entry -> {
                                    String propertyName = entry.getKey();
                                    JsonNode propertyNode = entry.getValue();

                                    String propertyType = propertyNode.get("type").asText();
                                    String propertyDescription = propertyNode.get("description").asText();

                                    propertiesMap.put(propertyName, propertyType);
                                });
                            }

                        } catch (JsonProcessingException e) {
                            throw new RuntimeException(e);
                        }
                        commonEntries = findCommonEntries(propertiesMap);

                }
            }
        }

        String resultString = "";
        for (Map.Entry<String, String> entry : commonEntries.entrySet()) {
            resultString += "cc.currentMemory." + entry.getKey() + " = " + entry.getKey() + "\n\t";
        }

        return resultString;
    }

    private static String addGlobal(String name) {
        String r = name.replace(")", "");
        String[] t = r.split("\\(");
        String[] m = t[1].split(",");
        for (String param : m) {
            gatewayGuards.add(param);
        }

        return "";
    }

    // 据左括号 ( 分割字符
    private static String getPrameters(String messageName) {
        // System.out.println("GETPARAM: " + messageName);
        String[] parsedMsgName = messageName.split("\\(");

        return "(" + parsedMsgName[1];
    }

    private static String createTransaction(ChoreographyTask task, List<String> optionalRoles,
            List<String> mandatoryRoles) {
        String ret = "";
        Participant toPay = task.getParticipantRef();
        if (mandatoryRoles.contains(toPay.getName())) {
            ret = "roles[\"" + toPay.getName() + "\"].transfer(msg.value);";
        } else if (optionalRoles.contains(toPay.getName())) {
            ret = "optionalRoles[\"" + toPay.getName() + "\"].transfer(msg.value);";
        }
        /*
         * String n = msg.replace("address", "").replace("payable", "");
         * String r = n.replace(")", "");
         * String[] t = r.split("\\(");
         * ret = t[1] + ".transfer(msg.value);";
         */

        return ret;
    }

    private static String transfer2GoType(String msg) {
        if (msg == null) {
            return "interface{}"; // 在Go中，接口类型（interface{}）可以表示任何类型的数据
        } else if (msg.equals("int")) {
            return "int"; // Go语言中的int类型
        } else if (msg.equals("long")) {
            return "int64"; // Go语言中的int64类型
        } else if (msg.equals("float")) {
            return "float32"; // Go语言中的float32类型
        } else if (msg.equals("double")) {
            return "float64"; // Go语言中的float64类型
        } else if (msg.equals("boolean")) {
            return "bool"; // Go语言中的布尔类型
        } else if (msg.equals("string")) {
            return "string"; // Go语言中的字符串类型
        } else if (msg.equals("number")) {
            return "int";
        } else {
            return "interface{}"; // 其它类型统一使用接口类型表示
        }
    }

    public void addGatewayMemoryParams() {
        for (SequenceFlow flow : modelInstance.getModelElementsByType(SequenceFlow.class)) {
            ModelElementInstance node = modelInstance.getModelElementById(flow.getAttributeValue("targetRef"));
            if (node instanceof ExclusiveGateway) {
                for (SequenceFlow outgoing : ((ExclusiveGateway) node).getOutgoing()) {
                    if (outgoing.getAttributeValue("name") != null) {
                        addCompareString(outgoing.getAttributeValue("name"));
                    }
                }
            }
        }
    }
    // }

}
