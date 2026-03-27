import http from "http";

const port = Number(process.env.MOCK_PORT || 18080);

const server = http.createServer((req, res) => {
  if (!req.url) {
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "missing url" }));
    return;
  }

  if (req.url.startsWith("/metrics")) {
    const now = Date.now();
    const temp = 18 + (now % 7000) / 1000;
    const humidity = 40 + (now % 3000) / 100;
    const price = 50000 + (now % 9000);
    const payload = {
      source: "mock-source",
      timestamp: now,
      weather: {
        temperature: Number(temp.toFixed(2)),
        humidity: Number(humidity.toFixed(2))
      },
      market: {
        btc: {
          usd: price
        }
      }
    };
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(payload));
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: "not found" }));
});

server.listen(port, () => {
  console.log(`mock source listening on http://127.0.0.1:${port}/metrics`);
});
