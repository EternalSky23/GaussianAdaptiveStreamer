self.addEventListener('message', async (event) => {
    const {blob, filename} = event.data;
    try {
        const root = await navigator.storage.getDirectory();
        const file = await root.getFileHandle(filename, {create: true});
        const writable = await file.createWritable();
        await writable.write(blob);
        await writable.close();

        self.postMessage({status: 'SUCCESS'});
    } catch (error) {
        self.postMessage({status: 'ERROR', message: error.message});
    }
});