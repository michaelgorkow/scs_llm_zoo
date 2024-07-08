FROM nvcr.io/nvidia/pytorch:24.04-py3

RUN pip install --upgrade pip && \
    pip install fastapi gunicorn uvicorn[standard] transformers==4.40.0 torchvision>=0.18.0 tiktoken>=0.7.0 bitsandbytes>=0.43.1 accelerate>=0.30.1

RUN pip install streamlit snowflake-snowpark-python

WORKDIR /app
COPY app /app

# Command to run the Streamlit app in the background
RUN echo "streamlit run llm_spcs_streamed_response.py --server.port 9001 &" > start_streamlit.sh && \
    chmod +x start_streamlit.sh

# Entry point to start the FastAPI server
ENTRYPOINT ["/bin/sh", "-c", "./start_streamlit.sh && uvicorn webservice:app --host 0.0.0.0 --port 9000"]