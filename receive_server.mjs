import WebSocket from 'ws';
import live from './gemini.mjs';

const ws = new WebSocket("ws://localhost:8765");

ws.on('open', () => {
  console.log("Connected to server");
});

ws.on('message', async (data) => {
  const input = data.toString();
  console.log("Received:", input);

  try {
    await live(input);              // Call Gemini + Speaker
    ws.send("Request complete");    // Notify Python to resume
  } catch (e) {
    console.error("Error during Gemini live session:", e);
    ws.send("error");
  }
});

ws.on('close', () => {
  console.log("Connection closed");
});
