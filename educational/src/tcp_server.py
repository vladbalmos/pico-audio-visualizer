import time
import threading
import asyncio
import queue
import struct

data_queue = queue.Queue()
stop_event = threading.Event()

_asyncio_loop = None
_thread = None
_server = None
_clients = []
_framerate = None
_frequency_bands_count = None

async def broadcast_fft_data():
    try:
        last_ms = time.time()
        last_output_ms = time.time()
        while True:
            try:
                data = data_queue.get(block=True, timeout=0.001)
            except queue.Empty:
                data = None

            if data is not None:
                # if len(clients):
                #     print(data.tolist())
                data = struct.pack(f'!{len(data)}f', *data.tolist())
                disconnected_clients = []
                for client in _clients:
                    try:
                        client.write(data)
                        await client.drain()
                        now = time.time()
                        diff = now - last_ms
                        
                        if time.time() - last_output_ms >= 1:
                            print(diff * 1000)
                            last_output_ms = now
                        last_ms = now
                    except Exception as e:
                        disconnected_clients.append(client)
                        print("Client disconnected", e)
                        
                if len(disconnected_clients):
                    for client in disconnected_clients:
                        _clients.remove(client)
                continue
            else:
                await asyncio.sleep(0.001)
    except asyncio.CancelledError:
        for client in _clients:
            client.close()
            await client.wait_closed()

async def handle_client(_, writer):
    writer.write(struct.pack('!bb', _framerate, _frequency_bands_count))
    await writer.drain()
    print("Client connected")
    _clients.append(writer)

async def main():
    global _server
    _server = await asyncio.start_server(handle_client, '0.0.0.0', 12345)
    broadcast_task = asyncio.create_task(broadcast_fft_data())
    tasks = asyncio.gather(broadcast_task, _server.serve_forever())
    while True:
        if stop_event.is_set():
            tasks.cancel()
            try:
                await tasks
            except asyncio.CancelledError:
                pass
            await _server.wait_closed()
            asyncio.get_event_loop().stop()
            break
        await asyncio.sleep(1)


def run(asyncio_loop, framerate, frequency_bands_count):
    global _framerate, _frequency_bands_count
    _framerate = framerate
    _frequency_bands_count = frequency_bands_count

    asyncio.set_event_loop(asyncio_loop)
    try:
        asyncio_loop.run_until_complete(main())
    finally:
        asyncio_loop.run_until_complete(asyncio_loop.shutdown_asyncgens())
        asyncio_loop.close()
    
def start(framerate, frequency_bands_count):
    global _asyncio_loop, _thread
    loop = asyncio.new_event_loop()
    _asyncio_loop = loop
    _thread = threading.Thread(target=run, args=(loop, framerate, frequency_bands_count, ))
    _thread.start()

def stop():
    stop_event.set()
    _thread.join()
    