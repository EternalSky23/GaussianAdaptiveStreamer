class ChunkBuffer {
    constructor() {
        this.imageID = 0;
        this.chunkBuffer = new Map();
    }
    
    processChunk(data) {
        const view = new DataView(data.buffer, 0, 18);
        const imageId = view.getUint32(0);
        const chunkIdx = view.getUint8(4);
        const totalChunks = view.getUint8(5);
        const timestemp = view.getBigUint64(6, false);
        const render_ms = view.getFloat32(14, false);
        const payload = data.slice(18);
        if (!this.chunkBuffer.has(imageId)) {
            const timeout = setTimeout(() => {
                if (this.chunkBuffer.has(imageId)) {
                    console.warn(`Image ${imageId} timed out. Dropping.`);
                    this.chunkBuffer.delete(imageId);
                    self.postMessage({ type: 'error', errorType: 'timeout', imageId });
                }
            }, 150);

            if (this.imageID > imageId) {
                console.warn(`Received out-of-order image ID ${imageId}. Current image ID is ${this.imageID}. Dropping.`);
                return;
            }

            this.chunkBuffer.set(imageId, {
                data: new Array(totalChunks).fill(null),
                timer: timeout,
                receivedCount: 0,
                firstSendTime: Number(timestemp),
                firstReceiveTime: performance.timeOrigin + performance.now(),
                renderMs: render_ms
            });
        }

        const entry = this.chunkBuffer.get(imageId);
        if (entry.data[chunkIdx] === null) {
            entry.data[chunkIdx] = payload;
            entry.receivedCount++;
        }

        if (entry.receivedCount === totalChunks) {
            clearTimeout(entry.timer);
            const fullImage = new Blob(entry.data, { type: 'image/jpeg' });
            this.assembleImage(imageId);
        }
    }

    assembleImage(imageId) {
        const entry = this.chunkBuffer.get(imageId);
        this.imageID = imageId;

        const fullImage = new Blob(entry.data, { type: 'image/jpeg' });
        const url = URL.createObjectURL(fullImage);
        self.postMessage({ 
            type: 'image', 
            imageId, 
            url,
            metadata: {
                renderMs: entry.renderMs,
                firstSendTime: entry.firstSendTime, 
                firstReceiveTime: entry.firstReceiveTime,
                finishTime: performance.timeOrigin + performance.now(),
                size: fullImage.size
            }
        });

        this.chunkBuffer.delete(imageId);
    }
};

const _buffer = new ChunkBuffer();
self.addEventListener('message', async (e) => {
    if (e.data['type'] === 'chunk') {
        _buffer.processChunk(e.data.chunk);
    }
});