from loader import STEP, CHECK_CONDITION, BoolWithMessage

def pre_check(conditions:list[CHECK_CONDITION]) -> bool:
    return True

def post_check(conditions:list[CHECK_CONDITION]) -> bool:
    return True

def invoke_api(url: str, param: list) -> bool:
    return True


def invoke_step(step: STEP) -> BoolWithMessage:
    if not step:
        return BoolWithMessage(False, "Step not found")

    if not pre_check(step.check_conditions):
        return BoolWithMessage(False, "Pre-check failed")

    if not invoke_api(step.invoker, step.param):
        return BoolWithMessage(False, "Invoke failed")

    if not post_check(step.check_conditions):
        return BoolWithMessage(False, "Post-check failed")


def invoke_task(path, steps: list[STEP]) -> BoolWithMessage:

    def get_step_with_name(name: str) -> STEP:
        for step in steps:
            if step.element == name:
                return step
        return None

    for index,step in enumerate(path):
        if not (res:= invoke_step(get_step_with_name(step))):
            return BoolWithMessage(False, f"Step {index} failed for reason:{res}")
    return BoolWithMessage(True, "All steps passed")
