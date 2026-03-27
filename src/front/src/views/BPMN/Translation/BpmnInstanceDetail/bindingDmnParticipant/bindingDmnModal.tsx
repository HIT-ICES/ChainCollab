import { useState, useEffect } from "react"
import {
    Box,
    Button,
    Typography,
    Stack,
    FormControl,
    InputLabel,
    Select as MUISelect,
    MenuItem,
    Table as MUITable,
    TableHead,
    TableBody,
    TableCell,
    TableRow,
    TableContainer,
    Paper,
    SelectChangeEvent,
    Divider
} from "@mui/material"
import { Binding, retrieveBPMN } from "@/api/externalResource"
import { useBusinessRulesDataByBpmn } from "./hooks"
import { useDmnListData } from "../../../Dmn/hooks"
import { useAppSelector } from "@/redux/hooks"
import { useDecisions } from "./hooks"



const DmnBindingBlock = (
    {
        businessRuleToFullfill,
        isHandle,
        unSetHandle,
        getActivity,
        setActivity,
        unSetActivity,
        close
    }

) => {
    const currentConsortiumId = useAppSelector((state) => state.consortium.currentConsortiumId)
    const [dmns, { }, syncDmns] = useDmnListData(currentConsortiumId)
    const [dmnId, setDmnId] = useState<string>("")

    const dmnToUse = dmns.filter((dmn) => dmn.id === dmnId)
    const [decisions, { }, refreshDecisions] = useDecisions(dmnToUse.length > 0 ? dmnToUse[0].dmnContent : "")
    const mainDecision = decisions.find((decision) => decision.is_main)
    const availableInput1 = mainDecision?.inputs ?? []
    const availableOutput1 = mainDecision?.outputs ?? []

    const availableInput = decisions.reduce((accumulator, decisions) => {  
        const decisionInputs = Array.isArray(decisions.inputs) ? decisions.inputs : [];  
        return [...accumulator, ...decisionInputs];  
    }, []);
    const availableOutput = decisions.reduce((accumulator, decisions) => {  
        const decisionOutputs = Array.isArray(decisions.outputs) ? decisions.outputs : [];  
        return [...accumulator, ...decisionOutputs];  
    }, []);
    const [currentParamMapping, setCurrentParamMapping] = useState({})

    useEffect(() => {

        if (!businessRuleToFullfill) {
            return
        }

        // init currentParamMapping based on businessRuleToFullfill'input and outputs, but not always empty
        const content = businessRuleToFullfill ? JSON.parse(businessRuleToFullfill.documentation) : {
            inputs: [], outputs: []
        }

        if (getActivity(businessRuleToFullfill.businessRuleId)) {
            const activity = getActivity(businessRuleToFullfill.businessRuleId)
            setCurrentParamMapping(activity.paramMapping)
            setDmnId(activity.dmnId)
            return
        }

        const newMap = {}
        content.inputs.map((input) => {
            newMap[input.name] = ""
        })
        setCurrentParamMapping(newMap)
    }, [businessRuleToFullfill])

    const checkParamMappingFullfill = () => {
        const content = businessRuleToFullfill ? JSON.parse(businessRuleToFullfill.documentation) : {
            inputs: [], outputs: []
        }
        const inputs = content.inputs
        const outputs = content.outputs
        const inputsFullfill = inputs.every((input) => {
            return currentParamMapping[input.name] !== ""
        })
        const outputsFullfill = outputs.every((output) => {
            return currentParamMapping[output.name] !== ""
        })

        return inputsFullfill && outputsFullfill
    }

    const handleOk = () => {
        if (!checkParamMappingFullfill()) {
            alert("Please fullfill the param mapping")
            return
        }
        setActivity(
            businessRuleToFullfill.businessRuleId,
            dmnId,
            mainDecision.id,
            swapMappingKeyValue(currentParamMapping),
            dmnToUse[0].dmnContent
        )
        close()

    }

    const handleCancel = () => {
        unSetHandle()
    }

    const handleReset = () => {
        unSetActivity(businessRuleToFullfill.businessRuleId)
    }

    const content = businessRuleToFullfill ? JSON.parse(businessRuleToFullfill.documentation) : {
        inputs: [], outputs: []
    }

    const inputDataSource = content.inputs.map((item) => {
        return {
            activitySlot: item,
            availableInput: availableInput
        }
    })

    const outputDataSource = content.outputs.map((item) => {
        return {
            activitySlot: item,
            availableInput: availableOutput
        }
    })


    const renderActivityCell = (slot) => (
        <Box>
            <Typography fontWeight={600}>{slot.name}</Typography>
            <Typography variant="caption" color="text.secondary">
                type: {slot.type}
            </Typography>
        </Box>
    )

    const renderSelectCell = (row, label) => (
        <FormControl size="small" fullWidth>
            <InputLabel>{label}</InputLabel>
            <MUISelect
                label={label}
                value={currentParamMapping[row.activitySlot.name] || ""}
                onChange={(event: SelectChangeEvent<string>) => {
                    setCurrentParamMapping({
                        ...currentParamMapping,
                        [row.activitySlot.name]: event.target.value as string
                    })
                }}
            >
                {row.availableInput.map((input, index) => {
                    const value = input.text || input.name || `${label}-${index}`
                    const displayLabel = input.text
                        ? `${input.text} type: ${input.typeRef ?? "unknown"}`
                        : `${input.name} type: ${input.type ?? "unknown"}`
                    return (
                        <MenuItem key={`${row.activitySlot.name}-${value}`} value={value}>
                            {displayLabel}
                        </MenuItem>
                    )
                })}
            </MUISelect>
        </FormControl>
    )


    return (
        <Box sx={{ width: "100%", display: isHandle ? "block" : "none" }}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center" sx={{ mb: 3 }}>
                <Typography variant="subtitle2" sx={{ minWidth: 160 }} color="text.secondary" fontWeight={600}>
                    Field Name
                </Typography>
                <FormControl fullWidth size="small">
                    <InputLabel id="dmn-select-label">Select DMN</InputLabel>
                    <MUISelect
                        labelId="dmn-select-label"
                        label="Select DMN"
                        value={dmnId}
                        onChange={(event: SelectChangeEvent<string>) => {
                            setDmnId(event.target.value as string)
                        }}
                    >
                        {dmns.map((dmn) => (
                            <MenuItem key={dmn.id} value={dmn.id}>
                                {dmn.name}
                            </MenuItem>
                        ))}
                    </MUISelect>
                </FormControl>
            </Stack>

            <Stack spacing={2}>
                <Box>
                    <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                        Input
                    </Typography>
                    <TableContainer component={Paper} variant="outlined">
                        <MUITable size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell width="40%">Activity Slot</TableCell>
                                    <TableCell>Available Input</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {inputDataSource.map((row) => (
                                    <TableRow key={row.activitySlot.name}>
                                        <TableCell>{renderActivityCell(row.activitySlot)}</TableCell>
                                        <TableCell>{renderSelectCell(row, "Available Input")}</TableCell>
                                    </TableRow>
                                ))}
                                {inputDataSource.length === 0 && (
                                    <TableRow>
                                        <TableCell colSpan={2}>
                                            <Typography variant="body2" color="text.secondary">
                                                No input slots defined for this BusinessRuleTask.
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </MUITable>
                    </TableContainer>
                </Box>

                <Box>
                    <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                        Output
                    </Typography>
                    <TableContainer component={Paper} variant="outlined">
                        <MUITable size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell width="40%">Activity Slot</TableCell>
                                    <TableCell>Available Output</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {outputDataSource.map((row) => (
                                    <TableRow key={row.activitySlot.name}>
                                        <TableCell>{renderActivityCell(row.activitySlot)}</TableCell>
                                        <TableCell>{renderSelectCell(row, "Available Output")}</TableCell>
                                    </TableRow>
                                ))}
                                {outputDataSource.length === 0 && (
                                    <TableRow>
                                        <TableCell colSpan={2}>
                                            <Typography variant="body2" color="text.secondary">
                                                No output slots defined for this BusinessRuleTask.
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </MUITable>
                    </TableContainer>
                </Box>
            </Stack>

            <Stack direction="row" spacing={1.5} justifyContent="flex-end" sx={{ mt: 3 }}>
                <Button onClick={handleCancel}>Cancel</Button>
                <Button color="warning" onClick={handleReset}>Reset</Button>
                <Button variant="contained" onClick={handleOk}>Ok</Button>
            </Stack>

        </Box>
    )

    function swapMappingKeyValue(originMapping) {
        const swappedParamMapping = {}

        for (const key in originMapping) {
            const value = originMapping[key]
            swappedParamMapping[value] = key
        }
        return swappedParamMapping
    }
}


export const BindingDmnModal = ({
    bpmnId,
    DmnBindingInfo,
    setDmnBindingInfo
}) => {

    const [businessRules, { }, syncbusinessRules] = useBusinessRulesDataByBpmn(bpmnId)

    useEffect(() => {
        // Init businessRulesInfo
        const newMap = {}
        Object.keys(businessRules).map((businessRuleId) => {
            newMap[businessRuleId] = {
                [businessRuleId + "_DMNID"]: "",
                [businessRuleId + "_DecisionID"]: "",
                [businessRuleId + "_ParamMapping"]: {},
                [businessRuleId + "_Content"]: "",
                "isBinded": false
            }
        })
        setDmnBindingInfo(newMap)
    }, [businessRules])


    const getActivity = (businessRuleId) => {
        if (!DmnBindingInfo[businessRuleId]) {
            return null
        }
        if (!DmnBindingInfo[businessRuleId]["isBinded"]) {
            return null
        }

        return {
            "dmnId": DmnBindingInfo[businessRuleId][businessRuleId + "_DMNID"],
            "decisionId": DmnBindingInfo[businessRuleId][businessRuleId + "_DecisionID"],
            "paramMapping": DmnBindingInfo[businessRuleId][businessRuleId + "_ParamMapping"],
            "content": DmnBindingInfo[businessRuleId][businessRuleId + "_Content"]
        }
    }


    const setActivity = (businessRuleId, dmnId, decisionId, paramMapping, content) => {
        setDmnBindingInfo({
            ...DmnBindingInfo,
            [businessRuleId]: {
                ...DmnBindingInfo[businessRuleId],
                [businessRuleId + "_DMNID"]: dmnId,
                [businessRuleId + "_DecisionID"]: decisionId,
                [businessRuleId + "_ParamMapping"]: paramMapping,
                [businessRuleId + "_Content"]: content,
                "isBinded": true
            }
        })
    }
    const unSetActivity = (businessRuleId) => {
        setDmnBindingInfo({
            ...DmnBindingInfo,
            [businessRuleId]: {
                ...DmnBindingInfo[businessRuleId],
                [businessRuleId + "_DMNID"]: "",
                [businessRuleId + "_DecisionID"]: "",
                [businessRuleId + "_ParamMapping"]: {},
                [businessRuleId + "_Content"]: "",
                "isBinded": false
            }
        })
    }

    const [currentBusinessRuleId, setCurrentBusinessRuleId] = useState<string>("")
    const close = () => {
        setCurrentBusinessRuleId("")
    }

    const data = Object.entries(businessRules as Record<string, any>).map(([businessRuleId, value]) => {
        return {
            businessRuleName: value?.name,
            businessRuleId: businessRuleId,
            documentation: value?.documentation,
        }
    })

    const itemToHandle = data.find((item) => item.businessRuleId === currentBusinessRuleId)

    const isHandle = itemToHandle ? true : false
    return (
        <>
            <TableContainer component={Paper} variant="outlined" sx={{ mb: 3 }}>
                <MUITable size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>BusinessRuleTask Name</TableCell>
                            <TableCell width={160} align="right">DMN</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {data.map((record) => {
                            const isSelected = record.businessRuleId === currentBusinessRuleId
                            return (
                                <TableRow
                                    key={record.businessRuleId}
                                    selected={isSelected}
                                    hover
                                >
                                    <TableCell>
                                        <Typography color={isSelected ? "primary" : "text.primary"} fontWeight={isSelected ? 600 : 500}>
                                            {record.businessRuleName}
                                        </Typography>
                                    </TableCell>
                                    <TableCell align="right">
                                        <Button
                                            variant={isSelected ? "contained" : "outlined"}
                                            size="small"
                                            onClick={() => setCurrentBusinessRuleId(record.businessRuleId)}
                                        >
                                            绑定
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            )
                        })}
                    </TableBody>
                </MUITable>
            </TableContainer>
            <DmnBindingBlock
                businessRuleToFullfill={itemToHandle}
                isHandle={isHandle}
                unSetHandle={() => {
                    setCurrentBusinessRuleId("")
                }}
                getActivity={getActivity}
                setActivity={setActivity}
                unSetActivity={unSetActivity}
                close={close}
            />
        </>

    )
}
