import jsonpickle
import websockets
import asyncio

async def handler(websocket):
    logFunction("Got new connection.")
    while True:
        try:
            content = await websocket.recv()
        except websockets.ConnectionClosedOK:
            logFunction(f"Abgelaufene Verbindung.", 4)
            logFunction(f"Meine Antwort wäre gewesen: {reply}", 10)
            break
        #############################
        reply = handleFunction(content)
        #############################
        try:
            reply_encoded = jsonpickle.encode(reply)
            await websocket.send(reply_encoded)
        except websockets.ConnectionClosedOK:
            logFunction('Connection closed. "ok"')
            break

async def main(port):
    async with websockets.serve(handler, "", port):
        await asyncio.Future()  # run forever

logFunction = print
handleFunction = lambda text: None

def run_forever(port, handle_function = None, log_function = None):
    global logFunction, handleFunction
    if log_function is not None:
        logFunction = log_function
    if handle_function is not None:
        handleFunction = handle_function
    for i in range(10):
        asyncio.run(main(port))
        log_function(f"Server died {i+1} times!")