 stateMachineDescription = {
    initial: 'idle',
    context: {
        username: 'Hello',
        password: '',
        error: null
    },
    states: {
        idle: {
            on: {
                LOGIN: {
                    target: 'loading',
                    cond: 'isFormValid',
                    actions: 'clearError'
                }
            }
        },
        loading: {
            entry: 'logLoading',
            on: {
                RESOLVE: 'success',
                REJECT: {
                    target: 'failure',
                    actions: 'logFailure'
                }
            }
        },
        success: {
            entry: 'logSuccess',
            type: 'final'
        },
        failure: {
            on: {
                RETRY: {
                    target: 'idle',
                    actions: 'clearError'
                }
            }
        }
    }
}


const actions = {
    // 更新用户名和密码
    updateCredentials: (context, event) => {
        context.username = event.username;
        context.password = event.password;
    },
    // 清除错误信息
    clearError: (context) => {
        context.error = null;
    },
    // 记录登录成功
    logSuccess: (context) => {
        console.log('登录成功！用户名:', context.username);
    },
    // 记录登录失败
    logFailure: (context, event) => {
        context.error = event.error;
        console.log('登录失败！错误信息:', context.error);
    },
    // 记录加载状态
    logLoading: () => {
        console.log('正在登录...');
    }
}
const guards = {
    // 检查表单是否有效
    isFormValid: (context, event) => {
        return context.username.trim() !== '' && context.password.trim() !== '';
    }
}

module.exports = {
    stateMachineDescription: stateMachineDescription,
    guards: guards,
    actions: actions
}