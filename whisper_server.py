import asyncio
import websockets

clients = set()

async def send_transcription(websocket):
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)

async def broadcast(message):
    if clients:
        await asyncio.gather(*[client.send(message) for client in clients])

async def start_websocket():
    print("WebSocket server started on ws://localhost:8765")
    return await websockets.serve(send_transcription, "localhost", 8765)
