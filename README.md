# Marker Docker

This is a CUDA-enabled Docker wrapper for converting image-based documents to markdown, complete with a cross-platform Python client. I originally enhanced it for my homelab to convert thousands of scanned documents and images into markdown format.

## What's New(ish)?
- **CUDA Support**: Tuned specifically for NVIDIA GPUs  
- **Image Handling**: Added support for images (JPG, PNG, TIFF) by automatically converting them to PDFs  
- **Python Client**: A handy client script that can process thousands of files—tested on Mac, Windows, and Linux  
- **Debug Mode**: Optional debugging that saves all requests and responses for troubleshooting

## ⚠️ Important Security Note
This service has **no** authentication and is meant for use in a secured homelab environment. **Do not** expose it to the internet without adding proper security measures!

## Quick Start
**Using Docker Compose (recommended):**
```bash
# Create debug logs directory (if using debug mode)
mkdir debug_logs

# Build and run with compose
docker compose up --build
```

**Or build and run manually with CUDA:**
```bash
docker build . -t markerwrapper:cuda
docker run --gpus all \
  -e MARKER_ROOT_PATH=/cornvert \
  -e MARKER_HOST=0.0.0.0 \
  -e MARKER_PORT=8001 \
  -p 8001:8001 markerwrapper:cuda
```

**Use the client (from any OS):**
```
pip install requests

python marker_client.py -o /path/to/output -u http://your.server:port/cornvert/ /path/to/scan/files
```

## Debug Mode
To enable debug mode, which saves all requests and responses:

1. Create a debug directory:
```bash
mkdir debug_logs
```

2. Use the provided compose_sample.yaml file, which already includes debug mode settings

OR

3. If running manually, add the debug flag:
```bash
docker run --gpus all \
  -e MARKER_ROOT_PATH=/cornvert \
  -e MARKER_HOST=0.0.0.0 \
  -e MARKER_PORT=8001 \
  -v ./debug_logs:/usr/src/app/marker/debug_logs \
  -p 8001:8001 markerwrapper:cuda \
  /usr/src/app/venv/bin/python /usr/src/app/marker/marker_server.py \
  --port 8001 --host 0.0.0.0 --root-path /cornvert --debug
```

Debug logs will be saved in timestamped folders under `./debug_logs/`.

## Known Issues
- How I'm overwriting `marker_server.py` in the Dockerfile is lame—I need a better process.
- Planning to add Microsoft's MarkItDown for Office documents (`.doc`, `.xls`, etc.), but that project seems unstable; currently, I can't get it to convert anything.
- External LLM support for advanced image analysis isn't implemented yet, even though Marker itself does provide some support.

## Background
I created this for my homelab to convert thousands of scanned documents from various sources into markdown. The client has been battle-tested across Windows, Mac, and Linux. Feel free to adapt it for your own bulk-conversion projects!

## References
- [VikParuchuri's marker](https://github.com/VikParuchuri/marker)  
- [Original Docker wrapper](https://github.com/Dibz15/marker_docker)  
- [Microsoft's MarkItDown](https://github.com/microsoft/markitdown)