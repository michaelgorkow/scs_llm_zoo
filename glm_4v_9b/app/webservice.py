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
import pypdfium2 as pdfium
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
    
def pil_image_to_base64(image: Image.Image) -> str:
    # Create a BytesIO buffer to hold the image data
    buffered = BytesIO()
    # Save the image to the buffer in PNG format
    image.save(buffered, format="PNG")
    # Get the byte data from the buffer
    img_byte_data = buffered.getvalue()
    # Encode the byte data to base64 string
    base64_str = base64.b64encode(img_byte_data).decode("utf-8")
    return base64_str

# Function for streaming LLM output
def generate_text_stream(generation_args):
    thread = Thread(target=model.generate, kwargs=generation_args)
    thread.start()
    for next_token in streamer:
        yield next_token.replace('<|endoftext|>','')

@app.post("/complete", tags=["Endpoints"])
async def complete(request: Request):
    request_body = await request.json()
    request_body = request_body['data']
    return_data = []

    for index, payload in request_body:
        prompt = payload['prompt']
        args = payload['args']
        generation_args = args.get('generation_args', {}) #args['generation_args']
        logger.info(prompt)
        logger.info(args)
        logger.info(generation_args)

        # Function to handle image loading and processing
        def load_image_from_args(args):
            logger.info('Found file')
            if 'file_url' in args:
                response = requests.get(args['file_url'])
                file_bytes = BytesIO(response.content)
                file_bytes_r = file_bytes.read()
                # if file is PNG or JPEG
                if file_bytes_r.startswith((b'\xff\xd8\xff', b'\x89\x50\x4e\x47')):
                    image = Image.open(file_bytes).convert('RGB')
                # if file is PDF
                if file_bytes_r.startswith(b'%PDF'):
                    pdf = pdfium.PdfDocument(file_bytes_r)
                    page = pdf[args['pdf_page']]
                    # Render the page
                    bitmap = page.render(
                        scale = 1,    # 72dpi resolution
                        rotation = 0  # no additional rotation
                    )
                    image = bitmap.to_pil()
            if 'base64_image_string' in args:
                image = base64_to_pil_image(args['base64_image_string']).convert('RGB')
            return image

        # Check if image processing is needed
        image = load_image_from_args(args) if any(key in args for key in ['file_url', 'base64_image_string']) else None

        # Prepare inputs based on whether an image is included
        if image:
            inputs = tokenizer.apply_chat_template([{"role": "user", "image": image, "content": prompt}],
                                                    add_generation_prompt=True, tokenize=True, return_tensors="pt",
                                                    return_dict=True)
        else:
            inputs = tokenizer.apply_chat_template([{"role": "user", "content": prompt}],
                                                    add_generation_prompt=True, tokenize=True, return_tensors="pt",
                                                    return_dict=True)

        inputs = inputs.to('cuda')

        # Handle streaming response
        if args.get('stream'):
            logger.info('STREAMED RESPONSE')
            generation_args = {**inputs, **generation_args, 'streamer': streamer}
            return StreamingResponse(generate_text_stream(generation_args), media_type="text/plain")
        
        # Handle non-streaming response (called via Snowflake Service Function)
        else:
            logger.info('NON STREAMED RESPONSE')
            with torch.no_grad():
                outputs = model.generate(**inputs, **generation_args)
                outputs = outputs[:, inputs['input_ids'].shape[1]:]
                #response = tokenizer.decode(outputs[0]).replace('<|endoftext|>', '')
                response = {'LLM_OUTPUT_TEXT': tokenizer.decode(outputs[0]).replace('<|endoftext|>', '')}
            # if user wants to return base64 image
            if 'return_image_base64' in args:
                logger.info('BASE64 IMAGE:')
                logger.info(pil_image_to_base64(image))
                response['base64_image'] = pil_image_to_base64(image)
            return_data.append([index, response])
    
    return {"data": return_data}