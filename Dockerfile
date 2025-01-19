# Use NVIDIA CUDA image as a parent image - this is tuned for CUDA for now
FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu20.04

# Set default environment variables - the current values are for local development
ENV MARKER_ROOT_PATH=""
ENV MARKER_HOST="127.0.0.1"
ENV MARKER_PORT="8000"    

# Set the working directory in the container
WORKDIR /usr/src/app
ARG DEBIAN_FRONTEND=noninteractive

# Install Python 3.10 and system requirements - this version of Ubuntu uses Python 3.8 by default
RUN apt-get update && apt-get install -y \
    software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y \
    git wget lsb-release apt-transport-https \
    ffmpeg libsm6 libxext6 python3.10 python3.10-venv python3.10-distutils vim && \
    rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default Python
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 && \
    update-alternatives --config python3

# Install pip for Python 3.10
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3

# Clone the repository
RUN git clone https://github.com/VikParuchuri/marker.git

# Set the working directory in the container
WORKDIR /usr/src/app/marker

# Install Tesseract
RUN wget -qO - https://notesalexp.org/debian/alexp_key.asc | apt-key add - && \
    echo "deb https://notesalexp.org/tesseract-ocr5/$(lsb_release -cs)/ $(lsb_release -cs) main" \
    | tee /etc/apt/sources.list.d/notesalexp.list > /dev/null && \
    apt-get update && \
    apt-get install -y tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

# Install Ghostscript
RUN wget https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10012/ghostscript-10.01.2.tar.gz && \
    tar -xvf ghostscript-10.01.2.tar.gz && \
    cd ghostscript-10.01.2 && \
    ./configure && \
    make install && \
    cd .. && \
    rm -rf ghostscript-10.01.2 ghostscript-10.01.2.tar.gz

# Find the tessdata directory and create a local.env file with the TESSDATA_PREFIX
RUN tessdata_path=$(find / -name tessdata -print -quit) && \
    echo "TESSDATA_PREFIX=${tessdata_path}" > local.env

# Create Python virtual environment - you can not install pip stuff globally
RUN python3 -m venv /usr/src/app/venv

# Install Poetry
RUN /usr/src/app/venv/bin/pip install --upgrade pip && \
    /usr/src/app/venv/bin/pip install poetry

# Install Python dependencies
RUN /usr/src/app/venv/bin/poetry install

# Remove existing PyTorch installation - no AMD stuff for now
RUN /usr/src/app/venv/bin/pip uninstall -y torch torchvision torchaudio

# Install CUDA-enabled PyTorch
RUN /usr/src/app/venv/bin/pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121

# Install additional Python dependencies
RUN /usr/src/app/venv/bin/pip install --no-cache-dir PyMuPDF pydantic ftfy python-dotenv \
    pydantic-settings tabulate pyspellchecker ocrmypdf nltk thefuzz scikit-learn texify \
    python-magic bs4 tabled-pdf markdownify google-cloud-vision google-cloud google-generativeai markdown2 \
    uvicorn fastapi python-multipart  img2pdf Pillow

# Set NVIDIA environment variables
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility
ENV LD_LIBRARY_PATH /usr/local/cuda/lib64:$LD_LIBRARY_PATH
ENV PATH /usr/local/cuda/bin:$PATH
ENV CUDA_HOME /usr/local/cuda

# Copy server file
COPY marker_server.py /usr/src/app/marker/marker_server.py

# Expose port for API
EXPOSE 8001

# The command to run the application - with the option to set the port, host, and root path
CMD ["/bin/bash", "-c", "/usr/src/app/venv/bin/python /usr/src/app/marker/marker_server.py --port ${MARKER_PORT} --host ${MARKER_HOST} --root-path ${MARKER_ROOT_PATH}"]