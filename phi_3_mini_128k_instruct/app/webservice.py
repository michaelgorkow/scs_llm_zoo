import logging
import sys
from fastapi import FastAPI, Request
import torch
import os
os.environ['HF_HOME'] = '/llm_models'
hf_access_token = os.getenv('HF_TOKEN')
model_id = os.getenv('HUGGINGFACE_MODEL')
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

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
model = AutoModelForCausalLM.from_pretrained(
    model_id, 
    device_map="auto", 
    torch_dtype="auto", 
    trust_remote_code=True, 
    token=hf_access_token
)
tokenizer = AutoTokenizer.from_pretrained(model_id)
pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
)
logger.info('Finished Loading Model.')

   
@app.post("/complete", tags=["Endpoints"])
async def complete(request: Request):
    # input_prompt
    request_body = await request.json()
    request_body = request_body['data']
    return_data = []
    for index, input_prompt  in request_body:
        generation_args = {
            "max_new_tokens": 500,
            "return_full_text": False,
            "temperature": 0.0,
            "do_sample": False,
        }
        messages = [
            {"role": "system", "content": "You are a helpful digital assistant. Please provide safe, ethical and accurate information to the user."},
            {"role": "user", "content": f"{input_prompt}"}
        ]
        output = pipe(messages, **generation_args)
        response = output[0]['generated_text']
        return_data.append([index, response])
    return {"data": return_data}


@app.post("/complete_custom", tags=["Endpoints"])
async def complete_custom(request: Request):
    # system_prompt, input_prompt, max_new_tokens, temperature
    request_body = await request.json()
    request_body = request_body['data']
    return_data = []
    for index, system_prompt, input_prompt, max_new_tokens, temperature  in request_body:
        generation_args = {
            "max_new_tokens": max_new_tokens,
            "return_full_text": False,
            "temperature": temperature,
            "do_sample": False,
        }
        messages = [
            {"role": "system", "content": f"{system_prompt}"},
            {"role": "user", "content": f"{input_prompt}"}
        ]
        output = pipe(messages, **generation_args)
        response = output[0]['generated_text']
        return_data.append([index, response])
    return {"data": return_data}