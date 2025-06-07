// recieve.mjs
import WebSocket from 'ws';

const ws = new WebSocket("ws://localhost:8765");

ws.on('open', () => {
  console.log("Connected to server");
});

ws.on('message', (data) => {
  console.log("Received:", data.toString());

  setTimeout(() => {
    ws.send("message sent after 5 seconds");
    console.log("sent message after 5 seconds")
  }, 5000);
});

ws.on('close', () => {
  console.log("Connection closed");
});
