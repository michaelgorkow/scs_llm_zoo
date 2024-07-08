import logging
import sys
from fastapi import FastAPI, Request
import torch
from PIL import Image
import requests
from io import BytesIO
from threading import Thread
from fastapi.responses import StreamingResponse
import os
import base64
os.environ['HF_HOME'] = '/llm_models'
model_id = os.getenv('HUGGINGFACE_MODEL')
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

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

# Loading model
logger.info('Loading Model ...')
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    trust_remote_code=True,
    load_in_4bit=True
)
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
streamer = TextIteratorStreamer(tokenizer, timeout=5, skip_prompt=True)
logger.info('Finished Loading Model.')

def base64_to_pil_image(base64_str: str) -> Image.Image:
    # Decode the base64 string to bytes
    img_byte_data = base64.b64decode(base64_str)
    # Create a BytesIO buffer from the byte data
    img_buffer = BytesIO(img_byte_data)
    # Open the image from the buffer using PIL
    image = Image.open(img_buffer)
    return image

# Standard function with default values, not supporting images
@app.post("/complete", tags=["Endpoints"])
async def complete(request: Request):
    request_body = await request.json()
    request_body = request_body['data']
    return_data = []
    for index, input_prompt, generation_args in request_body:
        inputs = tokenizer.apply_chat_template([{"role": "user", "content": input_prompt}],
                                            add_generation_prompt=True, tokenize=True, return_tensors="pt",
                                            return_dict=True)  
        inputs = inputs.to('cuda')
        with torch.no_grad():
            outputs = model.generate(**inputs, **generation_args)
            outputs = outputs[:, inputs['input_ids'].shape[1]:]
            response = tokenizer.decode(outputs[0]).replace('<|endoftext|>','')
        return_data.append([index, response])
    return {"data": return_data}

@app.post("/complete_image", tags=["Endpoints"])
async def complete_image(request: Request):
    request_body = await request.json()
    request_body = request_body['data']
    return_data = []
    for index, input_prompt, generation_args, image_url in request_body:
        # Fetch the image
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content)).convert('RGB')
        inputs = tokenizer.apply_chat_template([{"role": "user", "image": image, "content": input_prompt}],
                                            add_generation_prompt=True, tokenize=True, return_tensors="pt",
                                            return_dict=True)  
        inputs = inputs.to('cuda')
        with torch.no_grad():
            outputs = model.generate(**inputs, **generation_args)
            outputs = outputs[:, inputs['input_ids'].shape[1]:]
            response = tokenizer.decode(outputs[0]).replace('<|endoftext|>','')
        return_data.append([index, response])
    return {"data": return_data}
    
@app.post("/complete_stream", tags=["Endpoints"])
async def complete_stream(request: Request):
    request_body = await request.json()
    request_body = request_body['data']
    
    input_prompt = request_body[0][0]
    generation_args = request_body[0][1]
    inputs = tokenizer.apply_chat_template([{"role": "user", "content": input_prompt}],
                                        add_generation_prompt=True, tokenize=True, return_tensors="pt",
                                        return_dict=True)  
    inputs = inputs.to('cuda')
    generation_args = {
        **inputs,
        **generation_args,
        'streamer': streamer
    }
    return StreamingResponse(generate_text_stream(generation_args), media_type="text/plain")

# Function for streaming LLM output
def generate_text_stream(generation_args):
    thread = Thread(target=model.generate, kwargs=generation_args)
    thread.start()
    for next_token in streamer:
        yield next_token.replace('<|endoftext|>','')
        
@app.post("/complete_image_stream", tags=["Endpoints"])
async def complete_image_stream(request: Request):
    request_body = await request.json()
    request_body = request_body['data']
    
    input_prompt = request_body[0][0]
    generation_args = request_body[0][1]
    image_url = request_body[0][2]
    
    if 'base64_image_string' in generation_args:
        # if user provided image as part of the API call
        image = base64_to_pil_image(generation_args['base64_image_string'])
        image = image.convert('RGB')
        # remove base64 string from generation_args
        generation_args.pop('base64_image_string')
    else:
        # If not, fetch the image
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content)).convert('RGB')
    inputs = tokenizer.apply_chat_template([{"role": "user", "image": image, "content": input_prompt}],
                                        add_generation_prompt=True, tokenize=True, return_tensors="pt",
                                        return_dict=True)  
    inputs = inputs.to('cuda')
    generation_args = {
        **inputs,
        **generation_args,
        'streamer': streamer
    }
    return StreamingResponse(generate_text_stream(generation_args), media_type="text/plain")