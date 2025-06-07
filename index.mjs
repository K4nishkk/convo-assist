import { GoogleGenAI, Modality } from '@google/genai';
import { default as Speaker } from 'speaker';
import { Buffer } from 'buffer';
import { configDotenv } from 'dotenv';

configDotenv();

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
const model = 'gemini-2.5-flash-preview-native-audio-dialog';
const config = { responseModalities: [Modality.AUDIO] };

const speaker = new Speaker({
  channels: 1,
  bitDepth: 16,
  sampleRate: 24000,
});

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

  const session = await ai.live.connect({
    model,
    config,
    callbacks: {
      onopen: () => console.debug('Opened'),
      onmessage: (msg) => responseQueue.push(msg),
      onerror: (e) => console.error('Error:', e.message),
      onclose: (e) => console.debug('Closed:', e.reason),
    },
  });

  const input = 'create a paragraph of story of dungeons and dragons';
  session.sendClientContent({ turns: input });

  while (true) {
    const msg = await responseQueue.shift();

    if (msg?.data) {
      const buffer = Buffer.from(msg.data, 'base64');
      speaker.write(buffer);
    }

    if (msg?.serverContent?.turnComplete) break;
  }

  speaker.end();
  session.close();
}

live().catch(console.error);
