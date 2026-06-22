class ThroughputABR {
    constructor() {
        this._initialized = false;

        this.minProfile = 0;
        this.maxProfile = 3;
        this.profile = 3;

        this.estimateSmoothedBitrate = 0;
        this.estimateSmoothedBandwidth = 0;
        this.lastLatencyMs = 0;

        this.goodStreak = 0;
        this.badStreak = 0;
        this.upgradeRequiredStreak = 20;
        this.upgradeBoundaryMs = 25;
        this.downgradeRequiredStreak = 7;
        this.downgradeBoundaryMs = 50;
        

        this.lastSendTimestemp = 0;
        this.lastReceiveTimestemp = 0;
        this.lastTimeDelta = 0;
        this.accumulateDelta = 0;
        this.timeIncreaseStreak = 0;
        this.timeDeceraseStreak = 0;
        this.increaseStreakBoundary = 10;
        this.decreaseStreakBoundary = 25;

        this.timeBetweenFrame = 0;
        this.smoothTimeBetweenFrame = 0;

        this.renderMs = 0;

        this._timer = null;
        this.fps = 60;

        this.rx = 800;
        this.ry = 600;

        this.timeoutStreak = 0;
        this.timeoutStreakBoundary = 3;
    }

    _ewma(oldVal, newVal, alpha = 0.2) {
        if (oldVal === 0) return newVal;
        return alpha * newVal + (1 - alpha) * oldVal;
    }

    pickProfile() {
        this.tryChangeABRLevel();
        return this.profile;
    }

    updateMetadata(metadata) {
        /* 
            renderMs: the time server renders the frame
            firstSendTime: the last time client sends its position update to the server
            firstReceiveTime: the time when client receives the first chunk of the frame
            finishTime: the time when client finishes processing the frame
            size: the size of the frame in bytes

            We use above metadata to calculate the latency and processing time, which are used for ABR decision
        */
        const renderMs = metadata['renderMs'];
        const firstSendTime = metadata['firstSendTime'];
        const firstReceiveTime = metadata['firstReceiveTime'];
        const finishTime = metadata['finishTime'];
        const size = metadata['size'];

        const totalLatency = finishTime - firstSendTime;
        const estimateBandwidth = size / (finishTime - firstReceiveTime) * 1000 // kbps;
        const estimateRTT = firstReceiveTime - firstSendTime - renderMs;


        this._calcBitrate(size);
        this._updateLatency(totalLatency);
    }

    _calcBitrate(size) {
        this.lastBitrate = size * this.fps;
        this.estimateSmoothedBitrate = this._ewma(this.estimateSmoothedBitrate, this.lastBitrate);
    }

    _updateLatency(latency) {
        console.log(latency);
        if (latency > this.lastLatencyMs) {
            this.timeIncreaseStreak++;
        }
        else {
            this.timeIncreaseStreak = 0;
        }
        this.accumulateDelta = latency - this.lastLatencyMs;
        
        if (latency > this.downgradeBoundaryMs) {
            this.badStreak++;
            this.goodStreak = 0;
        }
        
        if (latency < this.upgradeBoundaryMs) {
            this.goodStreak++;
            this.badStreak = 0;
        }

        this.lastLatencyMs = latency;
    }

    tryChangeABRLevel() {
        if (this.badStreak > this.downgradeRequiredStreak) {
            this.downgrade();
            this.badStreak = 0;
            this.goodStreak = 0;
            this.timeIncreaseStreak = 0;
            this.accumulateDelta = 0;
            console.log("Downgrade based on latency");
            return;
        }

        if (this.timeIncreaseStreak > this.increaseStreakBoundary && this.accumulateDelta > 10) {
            this.downgrade();
            this.badStreak = 0;
            this.goodStreak = 0;
            this.timeIncreaseStreak = 0;
            this.accumulateDelta = 0;
            console.log("Downgrade based on delta");
            return;
        }

        if (this.goodStreak > this.upgradeRequiredStreak) {
            this.upgrade();
            this.goodStreak = 0;
            console.log("Upgrade based on latency");
            return;
        }
    }

    downgrade() {
        this.accumulateDelta = 0;
        if (this.profile < this.maxProfile) {
            this.profile++;
            return;
        }
    }

    upgrade() {
        if (this.profile == this.minProfile) {
            return;
        }

        if (this.processingTimeGoodStreak < this.processingTimeGoodStreakBoundary) {
            console.log("not safe for upgrade");
            return;
        }

        this.accumulateDelta = 0;

        if (this.profile > this.minProfile) {
            this.profile--;
        }
    }

    reset() {
        this._initialized = false;

        this.minProfile = 0;
        this.maxProfile = 3;
        this.profile = 3;

        this.lastBitrate = 0;

        this.goodStreak = 0;
        this.badStreak = 0;
        this.upgradeRequiredStreak = 20;
        this.upgradeBoundaryMs = 30;
        this.downgradeRequiredStreak = 7;
        this.downgradeBoundaryMs = 50;
        
        this.lastProcessingTimeMs = 0;
        this.lastFinishProcessingTime = 0;
        this.processingTimeGoodStreak = 0;
        this.processingTimeGoodStreakBoundary = 15;

        this.estimateLatency = 0;
        this.lastLatencyMs = 0;

        this.lastSendTimestemp = 0;
        this.lastReceiveTimestemp = 0;
        this.lastTimeDelta = 0;
        this.accumulateDelta = 0;
        this.timeIncreaseStreak = 0;
        this.timeDeceraseStreak = 0;
        this.increaseStreakBoundary = 15;
        this.decreaseStreakBoundary = 25;

        this.timeBetweenFrame = 0;
        this.smoothTimeBetweenFrame = 0;

        this.renderMs = 0;

        this._timer = null;
        this.fps = 60;

        this.rx = 800;
        this.ry = 600;
    }

    reportTimeout() {
        this.timeoutStreak++;
        if (this.timeoutStreak > this.timeoutStreakBoundary) {
            this.downgrade();
            this.timeoutStreak = 0;
            console.log("Downgrade based on timeout");
        }
    }
}