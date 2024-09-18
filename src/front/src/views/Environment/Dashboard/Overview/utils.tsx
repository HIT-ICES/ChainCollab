

export const DBstatus2stepandstatus = (status) => {
    if (status === "CREATED") {
        return {step: 1, status: "wait"}
    } else if (status === "INITIALIZED") {
        return {step:2, status: "wait"}
    } else if (status === "STARTED") {
        return { step: 3, status: "wait" }
    } else if (status === "ACTIVATED") {
        return { step: 3, status: "finish"}
    }
    return { step: 1, status: "wait" }
}