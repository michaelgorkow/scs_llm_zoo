import logging
import sys
from fastapi import FastAPI, Request
import torch
import open_clip
from io import BytesIO
from PIL import Image
import requests
import os
model_id = os.getenv('OPENCLIP_MODEL')
model_cp = os.getenv('OPENCLIP_CHECKPOINT')

# Set the cache directory to /tmp
cache_dir = '/llm_models'

# Logging
def get_logger(logger_name):
   logger = logging.getLogger(logger_name)
   logger.setLevel(logging.DEBUG)
   handler = logging.StreamHandler(sys.stdout)
   handler.setLevel(logging.DEBUG)
   handler.setFormatter(
      logging.Formatter(
      '%(name)s [%(asctime)s] [%(levelname)s] %(message)s'))
   logger.addHandler(handler)
   return logger
logger = get_logger('snowpark-container-service')

app = FastAPI()

logger.info(f'cuda.is_available(): {torch.cuda.is_available()}')
logger.info(f'cuda.device_count(): {torch.cuda.device_count()}')

torch.random.manual_seed(0)

# Loading model
logger.info('Loading Model ...')
# Load the model and preprocess with the specified cache directory
model, _, preprocess = open_clip.create_model_and_transforms(
    model_id, 
    pretrained=model_cp, 
    cache_dir=cache_dir
)
model.eval()  # model in train mode by default, impacts some models with BatchNorm or stochastic depth active
tokenizer = open_clip.get_tokenizer(model_id)
logger.info('Finished Loading Model.')

   
@app.post("/encode_image", tags=["Endpoints"])
async def encode_image(request: Request):
    # input_prompt
    request_body = await request.json()
    request_body = request_body['data']
    return_data = []
    for index, url  in request_body:
        # Load image
        response = requests.get(url)
        image = Image.open(BytesIO(response.content))
        image = preprocess(image).unsqueeze(0)
        # Generate embeddings
        with torch.no_grad(), torch.cuda.amp.autocast():
            image_features = model.encode_image(image)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            image_features = image_features.tolist()[0]
        return_data.append([index, image_features])
    return {"data": return_data}

@app.post("/encode_text", tags=["Endpoints"])
async def encode_text(request: Request):
    # input_prompt
    request_body = await request.json()
    request_body = request_body['data']
    return_data = []
    for index, text  in request_body:
        text = tokenizer([text])
        # Generate embeddings
        with torch.no_grad(), torch.cuda.amp.autocast():
            text_features = model.encode_text(text)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            text_features = text_features.tolist()[0]
        return_data.append([index, text_features])
    return {"data": return_data}