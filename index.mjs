import { GoogleGenAI, Modality } from '@google/genai';
import * as fs from "node:fs";
import pkg from 'wavefile';
import { configDotenv } from 'dotenv';

const { WaveFile } = pkg;
configDotenv();

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
const model = 'gemini-2.5-flash-preview-native-audio-dialog';
const config = { responseModalities: [Modality.AUDIO] };

// Simple promise queue
function createMessageQueue() {
  let resolveNext;
  const queue = [];

  return {
    push(message) {
      if (resolveNext) {
        resolveNext(message);
        resolveNext = null;
      } else {
        queue.push(message);
      }
    },
    async shift() {
      if (queue.length > 0) return queue.shift();
      return new Promise(resolve => resolveNext = resolve);
    }
  };
}

async function live() {
  const responseQueue = createMessageQueue();
  const audioChunks = [];

  const session = await ai.live.connect({
    model,
    config,
    callbacks: {
      onopen: () => console.debug('Opened'),
      onmessage: (msg) => responseQueue.push(msg),
      onerror: (e) => console.error('Error:', e.message),
      onclose: (e) => console.debug('Close:', e.reason),
    }
  });

  // Send text input
  const input = 'How is the weather in chandigarh?';
  session.sendClientContent({ turns: input });

  // Handle streaming response
  while (true) {
    const msg = await responseQueue.shift();

    if (msg?.data) {
      const buffer = Buffer.from(msg.data, 'base64');
      const int16 = new Int16Array(buffer.buffer, buffer.byteOffset, buffer.length / 2);
      audioChunks.push(...int16);
    }

    if (msg?.serverContent?.turnComplete) break;
  }

  // Save to .wav
  const wf = new WaveFile();
  wf.fromScratch(1, 24000, '16', new Int16Array(audioChunks));
  fs.writeFileSync('output.wav', wf.toBuffer());

  session.close();
}
live().catch(console.error);
