import os
import random
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

# Serve static files
app.mount("/media", StaticFiles(directory=BASE_DIR / "media"), name="media")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# WebSocket clients
clients = []

# Event when track finishes
track_finished_event = asyncio.Event()

# Background task control
music_task = None
stop_flag = False


# -------------------------------------------------------------------
# Broadcast to all connected clients
# -------------------------------------------------------------------
async def broadcast(message: dict):
    remove_clients = []
    for ws in clients:
        try:
            await ws.send_json(message)
        except:
            remove_clients.append(ws)
    for ws in remove_clients:
        clients.remove(ws)


# -------------------------------------------------------------------
# WebSocket endpoint (browser sends track_ended here)
# -------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            msg = await websocket.receive_json()

            # Browser informs us that audio has ended
            if msg.get("event") == "track_ended":
                track_finished_event.set()

    except WebSocketDisconnect:
        clients.remove(websocket)


# -------------------------------------------------------------------
# Background loop that plays random music from given directory
# -------------------------------------------------------------------
async def music_loop(dir_name: str):
    global stop_flag

    music_dir = BASE_DIR / "media" / "music" / dir_name

    print("Selected music directory:", music_dir)

    if not music_dir.exists():
        print("Directory does not exist:", music_dir)
        return

    while not stop_flag:
        audio_files = [
            f
            for f in os.listdir(music_dir)
            if f.lower().endswith((".mp3", ".wav", ".ogg"))
        ]

        if not audio_files:
            print("No audio files found in:", music_dir)
            await asyncio.sleep(5)
            continue

        filename = random.choice(audio_files)
        file_url = f"/media/music/{dir_name}/{filename}"

        print("Now playing:", file_url)

        await broadcast({"action": "play_music", "file": file_url})

        # Reset track end event & wait for signal or timeout
        track_finished_event.clear()

        try:
            await asyncio.wait_for(track_finished_event.wait(), timeout=600)
        except asyncio.TimeoutError:
            print("Track timeout – skipping")

        await asyncio.sleep(0.15)

    print("Music loop ended.")


# -------------------------------------------------------------------
# API ENDPOINTS
# -------------------------------------------------------------------


@app.get("/")
async def root():
    return {"message": "Go to /static/index.html to control media"}


@app.get("/show_image/{filename}")
async def show_image(filename: str):
    await broadcast({"action": "show_image", "file": f"/media/images/{filename}"})
    return {"status": "ok"}


@app.get("/play_music/{filename}")
async def play_music(filename: str):
    await broadcast({"action": "play_music", "file": f"/media/music/{filename}"})
    return {"status": "ok"}


@app.get("/stop_music")
async def stop_music():
    await broadcast({"action": "stop_music"})
    return {"status": "ok"}


@app.get("/play_sfx/{filename}")
async def play_sfx(filename: str):
    await broadcast({"action": "play_sfx", "file": f"/media/sfx/{filename}"})
    return {"status": "ok"}


# -------------------------------------------------------------------
# START RANDOM MUSIC LOOP (directory-aware)
# -------------------------------------------------------------------
@app.get("/start_random_music/{dir_name}")
async def start_random_music(dir_name: str):
    global music_task, stop_flag

    if music_task and not music_task.done():
        return {"status": "already_running"}

    stop_flag = False
    music_task = asyncio.create_task(music_loop(dir_name))
    return {"status": "started", "directory": dir_name}


# -------------------------------------------------------------------
# STOP RANDOM MUSIC LOOP (proper task cancellation)
# -------------------------------------------------------------------
@app.get("/stop_random_music")
async def stop_random_music():
    global stop_flag, music_task

    stop_flag = True
    await broadcast({"action": "stop_music"})

    # Cancel running background task
    if music_task and not music_task.done():
        music_task.cancel()
        try:
            await music_task
        except asyncio.CancelledError:
            pass

    music_task = None
    return {"status": "stopped"}
