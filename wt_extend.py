import json
import asyncio
import struct
import time
import logging

from routes import render_image_raw
from encoding import encode_jpeg
from models import get_model, ensure_started

from starlette.types import Scope, Receive, Send
from aioquic.h3.connection import H3Connection

nextAvailableUserID = 0
userid_lock = asyncio.Lock()

class UserState:
    def __init__(self):
        self.angle = 180.0
        self.elevation = 0.0
        self.x = 0.0
        self.y = 0.0
        self.z = 5.0
        self.fx = 1300.0
        self.fy = 800.0
        self.cx = 400.0
        self.cy = 300.0
        self.width = 800
        self.height = 600
        self.profile = 0
        self.modelID = None
        self.model = None
        self.timestemp = 0
        self.lock = asyncio.Lock()
        self.fps = 60

        self.image_id = 0
        self.imageIDLock = asyncio.Lock()

        self.should_stop = False

    async def updatePos(self, msg_json):
        async with self.lock:
            for item, val in msg_json.items():
                if item in ["angle", "elevation", 
                            "x", "y", "z", 
                            "fx", "fy", "cx", "cy"]:
                    try:
                        setattr(self, item, float(val))
                    except ValueError:
                        logging.warning(f"Invalid value for {item}: {val}")
                        continue
                    
                elif item in ["profile", "timestemp", "fps", "width", "height"]:
                    try:
                        setattr(self, item, int(val))
                    except ValueError:
                        logging.warning(f"Invalid value for {item}: {val}")
                        continue
                
                elif item == "modelId":
                    if self.modelID != msg_json["modelId"]:
                        self.modelID = msg_json["modelId"]
                        self.model = get_model(self.modelID)    

    async def getFPS(self):
        async with self.lock:
            return self.fps

    async def getData(self):
        async with self.lock:
            ret = (
                self.angle, self.elevation, 
                self.x, self.y, self.z, 
                self.fx, self.fy, self.cx, self.cy,
                self.width, self.height, self.profile, self.model
            )
            timestemp = self.timestemp

        return ret, timestemp
    
    async def getNextImageId(self):
        async with self.imageIDLock:
            ret = self.image_id
            self.image_id = (self.image_id + 1) % 4294967296

        return ret

users_data: dict[int, UserState] = {}

async def wt(scope: Scope, receive: Receive, send: Send, connection: H3Connection):
    message = await receive()
    await send({"type": "webtransport.accept"})

    global nextAvailableUserID, users_data
    userID = None

    async with userid_lock:
        userID = nextAvailableUserID
        nextAvailableUserID += 1

    await ensure_started()
    users_data[userID] = UserState()

    task = asyncio.create_task(TimedSend(send, userID))

    buffer = b""
    while not users_data[userID].should_stop:
        message = await receive()
        if message["type"] == "webtransport.stream.receive":
            buffer += message["data"]
            while len(buffer) >= 4:
                length = int.from_bytes(buffer[:4], byteorder="big")
                if len(buffer) >= 4 + length:
                    payload = buffer[4:4 + length]

                    msg_json = json.loads(payload)
                    buffer = buffer[4 + length:]

                    if "closed" in msg_json:
                        users_data[userID].should_stop = True
                        await send({"type": "webtransport.close"})
                    else:
                        await users_data[userID].updatePos(msg_json)
                
                else:
                    break

        else:
            print(message["type"])


async def TimedSend(send: Send, userID: int):
    deadline_ms = time.time_ns() // 1e6

    while not users_data[userID].should_stop:
        asyncio.create_task(RenderAndSendImage(send, userID))

        fps = await users_data[userID].getFPS()
        deadline_ms += 1000 / fps
        await asyncio.sleep((deadline_ms - time.time_ns() // 1e6) / 1e3)

async def RenderAndSendImage(send: Send, userID: int):
    MAX_DATAGRAM_SIZE = 1350

    await ensure_started()
    user = users_data[userID]
    user_data, timestemp = await user.getData()
    if user_data[-1] is None:
        return 0.0
    
    quality_level = user_data[-2]
    render_start_time_ms = int(time.time_ns() // 1e6)
    img_stream, render_ms = render_image_raw(*user_data)
    jpeg = encode_jpeg(img_stream, quality=70 - quality_level)

    total_chunks = (len(jpeg) + MAX_DATAGRAM_SIZE - 1) // MAX_DATAGRAM_SIZE
    image_id = await user.getNextImageId()
    for i in range(total_chunks):
        start = i * MAX_DATAGRAM_SIZE
        end = start + MAX_DATAGRAM_SIZE
        chunk_data = jpeg[start:end]
        header = struct.pack("!IBBQf", image_id, i, total_chunks, timestemp, render_ms)
        await send(
            {
                "data": header + chunk_data,
                "type": "webtransport.datagram.send",
                "image_id": image_id
            }
        )

    fin_time = time.time()
    return render_ms