func (cc *SmartContract) #message#_Complete(ctx contractapi.TransactionContextInterface, targetTaskID int, ConfirmTargetX509 string, instanceID string) error {
	stub := ctx.GetStub()
	instance,_ := cc.GetInstance(ctx, instanceID)

	collectiveMsgName := "#message#"
	collectiveMsg, _ := cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	participant_id := collectiveMsg.ReceiveParticipantID
	
	// MultiTask Address Located
	choreographyTaskID := collectiveMsg.ChoreographyTaskID

	choreographyTask, _ := cc.ReadChoreographyTask(ctx, instanceID, choreographyTaskID)
	if choreographyTask.IsMulti == true {
		collectiveMsgName = fmt.Sprintf("#message#_%d", targetTaskID)
	}


	collectiveMsg, _ = cc.ReadCollectiveMsg(ctx, instanceID, collectiveMsgName)
	sendParticipantID := collectiveMsg.SendParticipantID
	receiveParticipantID := collectiveMsg.ReceiveParticipantID
	sendParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, sendParticipantID)
	receiveParticipant, _ := cc.ReadCollectiveParticipant(ctx, instanceID, receiveParticipantID)

	var errorMessage string
	var key1, key2 string
	var msgsToHandle []Message = make([]Message, 0)
	var eventsToTrigger []string = make([]string,0)
	var event map[string]interface{}
	var eventJsonString string
	var eventJsonBytes []byte
	if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == false {
		// 一对一
		key1 = "nonMulti"
		key2 = "nonMulti"
		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1][key2])

		event = map[string]interface{}{
			"type": "Confirm_#message#",
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)
		eventsToTrigger = append(eventsToTrigger, eventJsonString)

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false{
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

	}else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == false {
		// 多对一 回应 
		// 1. 响应所有消息
		// 2. 添加Target

		key1 = ConfirmTargetX509
		key2 = "nonMulti"

		participant_key := key2
		if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false{
			errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
			fmt.Println(errorMessage)
			return fmt.Errorf(errorMessage)
		}

		// Which To Confirm? Decided By ConfirmTargetX509
		confirmTargetSender, ok := sendParticipant.Participants[key1];
		if  !ok {
			errorMessage := "UnExisted ConfirmTarget"
			return fmt.Errorf(errorMessage)
		}

		msgsToHandle = append(msgsToHandle, collectiveMsg.Messages[key1]["nonMulti"])

		event = map[string]interface{}{
			"type": fmt.Sprintf("Confirm_#message#_%s", confirmTargetSender.ParticipantID),
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)

		eventsToTrigger = append(eventsToTrigger, eventJsonString)
	}else if sendParticipant.IsMulti == false && receiveParticipant.IsMulti == true {
		// 一对多 回应，响应自己的部分，修改计数器
		key1 = "nonMulti"
		key2 = cc.get_X509_identity(ctx)

		if receiveParticipant.IsLocked == true {
			// check if key2 in it
			if _, ok := receiveParticipant.Participants[key2]; ok {
				// check Participant
				participant_key := key2
				if cc.check_participant(ctx, instanceID, participant_id, participant_key) == false{
					errorMessage := fmt.Sprintf("Participant %s is not allowed to send the message", participant_id)
					fmt.Println(errorMessage)
					return fmt.Errorf(errorMessage)
				}
			}else {
				return fmt.Errorf("The participant is locked and the participant is not registered")
			}
		}else{

			if receiveParticipant.MultiMaximum <= len(receiveParticipant.Participants) {
				errorMessage := "ReceiveParticipants Has Reach the Maximum"
				return fmt.Errorf(errorMessage)
			}

			if cc.check_participant(ctx, instanceID, participant_id, "") != true {
				errorMessage := "Not Allowed To participate as a Receiver"
				return fmt.Errorf(errorMessage)
			}

			// create new Participant if not exist
			x509 := cc.get_X509_identity(ctx)
			participant_increasing_key := len(receiveParticipant.Participants)
			msp, _ := ctx.GetClientIdentity().GetMSPID()
			newParticipant := Participant{
				ParticipantID: fmt.Sprintf("%d",participant_increasing_key),
				MSP: msp,
				IsMulti: true,
				X509: x509,
			}
			receiveParticipant.Participants[key2] = newParticipant
		}

		// get the message and increase it's confirmedCount


		if collectiveMsg.MessageConfirmedCount >= receiveParticipant.MultiMaximum {
			return fmt.Errorf("The number of messages sent by the participant exceeds the maximum")
		}

		message_increasing_key := fmt.Sprintf("%d",collectiveMsg.MessageConfirmedCount)
		msg := collectiveMsg.Messages[key1][message_increasing_key]
		delete(collectiveMsg.Messages[key1], message_increasing_key)
		collectiveMsg.Messages[key1][key2] = msg
		collectiveMsg.MessageConfirmedCount += 1


		msgsToHandle = append(msgsToHandle, msg)

		event = map[string]interface{}{
			"type": fmt.Sprintf("Confirm_#message#_%d", message_increasing_key),
		}

		eventJsonBytes, _ = json.Marshal(event)

		eventJsonString = string(eventJsonBytes)

		eventsToTrigger = append(eventsToTrigger, eventJsonString)

	}else if sendParticipant.IsMulti == true && receiveParticipant.IsMulti == true {
		// 多对多 UnSupported Operations?
		errorMessage = fmt.Sprintf("UnSupported Operation")
		return fmt.Errorf(errorMessage)
	}


	for _, event := range eventsToTrigger {
		res,err := cc.Invoke_Other_chaincode(ctx, "stateCharts:v1", "default",
		stateCharts.EncodeTriggerActionArgs(instance.StateMachineDescription, instance.CurrentState, event))
		if err != nil {
			return err
		}
		state, changed := stateCharts.DecodeTriggerActionResult(res)

		if !changed {
			return fmt.Errorf("The state machine does not change")
		}

		instance.CurrentState = state
	} 

	stub.SetEvent(collectiveMsgName, []byte("Message is Confirmed !"))
	cc.SetInstance(ctx, instance)
	return nil
}