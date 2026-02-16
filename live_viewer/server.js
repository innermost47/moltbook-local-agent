const express = require("express");
const http = require("http");
const socketIO = require("socket.io");
const path = require("path");
const net = require("net");

const app = express();
const server = http.createServer(app);
const io = socketIO(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"],
  },
});

app.use(express.static(path.join(__dirname, "public")));

app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

const TCP_PORT = 9999;
const tcpServer = net.createServer((socket) => {
  console.log("🐍 Python client connected");

  socket.on("data", (data) => {
    try {
      const events = data
        .toString()
        .split("\n")
        .filter((e) => e.trim());

      events.forEach((eventStr) => {
        const event = JSON.parse(eventStr);
        console.log(`📡 Broadcasting: ${event.type}`);

        io.emit("agent_event", event);
      });
    } catch (err) {
      console.error("Error parsing event:", err);
    }
  });

  socket.on("end", () => {
    console.log("🐍 Python client disconnected");
  });

  socket.on("error", (err) => {
    console.error("TCP Socket error:", err);
  });
});

tcpServer.listen(TCP_PORT, () => {
  console.log(`🔌 TCP server listening on port ${TCP_PORT} for Python events`);
});

io.on("connection", (socket) => {
  console.log("🌐 Web client connected");

  socket.on("disconnect", () => {
    console.log("🌐 Web client disconnected");
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`🚀 Live Viewer running at http://localhost:${PORT}`);
  console.log(`📡 Waiting for Python agent events on TCP port ${TCP_PORT}...`);
});
