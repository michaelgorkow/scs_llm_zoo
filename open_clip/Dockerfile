FROM nvcr.io/nvidia/pytorch:24.04-py3

RUN pip install --upgrade pip && \
    pip install fastapi gunicorn uvicorn[standard] transformers==4.42.4 torchvision>=0.18.0 tiktoken>=0.7.0 bitsandbytes>=0.43.1 accelerate>=0.30.1 \
                streamlit snowflake-snowpark-python pypdfium2 

RUN pip install open_clip_torch

WORKDIR /app
COPY app /app

ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:9000", "--workers", "1", "--timeout", "0", "webservice:app", "-k", "uvicorn.workers.UvicornWorker"]