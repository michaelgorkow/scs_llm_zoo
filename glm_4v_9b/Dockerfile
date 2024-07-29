FROM nvcr.io/nvidia/pytorch:24.04-py3

RUN pip install --upgrade pip && \
    pip install fastapi gunicorn uvicorn[standard] transformers==4.42.4 torchvision>=0.18.0 tiktoken>=0.7.0 bitsandbytes>=0.43.1 accelerate>=0.30.1 \
                streamlit snowflake-snowpark-python pypdfium2

WORKDIR /app
COPY app /app

# Command to run the Streamlit app in the background
RUN echo "streamlit run glm-4v-9b-app.py --server.port 9001 --browser.gatherUsageStats false &" > start_streamlit.sh && \
    chmod +x start_streamlit.sh

# Entry point to start the FastAPI server
ENTRYPOINT ["/bin/sh", "-c", "./start_streamlit.sh && uvicorn webservice:app --host 0.0.0.0 --port 9000"]