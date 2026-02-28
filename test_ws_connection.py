
import asyncio
import websockets

async def test_connection():
    uri = "ws://localhost:8000/ws/notifications"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for messages...")
            # Keep alive for 10 seconds
            for i in range(10):
                await asyncio.sleep(1)
                print(f"Connection stable for {i+1}s...")
            print("Test complete. Disconnecting.")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
