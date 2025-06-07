// recieve.mjs
import WebSocket from 'ws';

const ws = new WebSocket("ws://localhost:8765");

ws.on('open', () => {
  console.log("Connected to server");
});

ws.on('message', (data) => {
  console.log("Received:", data.toString());
});

ws.on('close', () => {
  console.log("Connection closed");
});
