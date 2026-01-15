const http = require('http');

const PORT = 3000;

const server = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');

    console.log('📡 收到请求:', req.method, req.url);

    // 固定返回 {"value": 123} 格式，这是 MyChainlinkRequester 合约期望的格式
    const response = {
        value: 123
    };

    res.end(JSON.stringify(response));
});

server.listen(PORT, () => {
    console.log(`🚀 测试服务器运行在 http://localhost:${PORT}`);
    console.log(`📡 访问: curl http://localhost:${PORT}`);
    console.log(`✅ 返回: {"value": 123}`);
    console.log('');
    console.log('用于测试的 URL:');
    console.log(`http://host.docker.internal:${PORT}`);
});
