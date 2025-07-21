

export const DBstatus2stepandstatus = (status) => {
    if (status === "CREATED") {
        return {step: 1, status: "wait"}
    } else if (status === "INITIALIZED") {
        return {step:2, status: "wait"}
    } else if (status === "STARTED") {
        return { step: 3, status: "wait" }
    } else if (status === "ACTIVATED") {
        return { step: 4, status: "finish"}
    }
    return { step: 1, status: "wait" }
}

export const SSIStatusStepAndStatus = (status) => {
    if (status === "INDYINITIALED") {
        return {step: 1, status: "wait"}
    } else if (status === "DOCKERSTARTED") {
        return {step:2, status: "wait"}
    } else if (status === "ACAPYPREPAERD") {
        return { step: 3, status: "wait" }
    } else if (status === "ACTIVATED") {
        return { step: 4, status: "finish"}
    }
    return { step: 1, status: "wait" }
}