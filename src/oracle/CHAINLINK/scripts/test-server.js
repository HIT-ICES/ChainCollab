const http = require('http');

const PORT = 8080;

const server = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');

    console.log('📡 收到请求:', req.method, req.url);

    // 响应 /value 路径的请求，返回 {"value": 123} 格式
    if (req.method === 'GET' && req.url === '/value') {
        const response = {
            value: 1234
        };
        res.end(JSON.stringify(response));
    } else {
        // 其他路径返回 404
        res.statusCode = 404;
        res.end(JSON.stringify({ error: 'Not found' }));
    }
});

server.listen(PORT, () => {
    console.log(`🚀 测试服务器运行在 http://localhost:${PORT}`);
    console.log(`📡 访问: curl http://localhost:${PORT}/value`);
    console.log(`✅ 返回: {"value": 123}`);
    console.log('');
    console.log('用于测试的 URL:');
    console.log(`http://host.docker.internal:${PORT}/value`);
});
