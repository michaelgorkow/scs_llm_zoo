# Import necessary packages
import streamlit as st
import pandas as pd
from io import BytesIO
from PIL import Image
import pypdfium2 as pdfium
import requests
import os
import base64
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session
import snowflake.connector


# Function to create a Snowpark session
@st.cache_resource
def create_snowpark_session(cache_id):
    # if running in SPCS
    if os.path.isfile("/snowflake/session/token"):
        creds = {
            'host': os.getenv('SNOWFLAKE_HOST'),
            'protocol': "https",
            'account': os.getenv('SNOWFLAKE_ACCOUNT'),
            'authenticator': "oauth",
            'token': open('/snowflake/session/token', 'r').read(),
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
            'database': os.getenv('SNOWFLAKE_DATABASE'),
            'schema': os.getenv('SNOWFLAKE_SCHEMA'),
            'client_session_keep_alive': True
        }
    # if running Streamlit externally, use environment variables from .env file
    elif os.path.isfile(".env"):
        from dotenv import load_dotenv
        load_dotenv()
        creds = {
            'account': os.getenv('SNOWFLAKE_ACCOUNT'),
            'user': os.getenv('SNOWFLAKE_USER'),
            'password': os.getenv('SNOWFLAKE_PASSWORD'),
            'role': os.getenv('SNOWFLAKE_ROLE'),
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
            'database': os.getenv('SNOWFLAKE_DATABASE'),
            'schema': os.getenv('SNOWFLAKE_SCHEMA'),
            'client_session_keep_alive': True
        }
    else:
        session = get_active_session()
        return session
    connection = snowflake.connector.connect(**creds)
    session = Session.builder.configs({"connection": connection}).create()
    return session
    
# Function to retrieve an Oauth-Token-header
# only required if calling SPCS functions directly from an external location
def get_header_token(session):
    session.sql("ALTER SESSION SET PYTHON_CONNECTOR_QUERY_RESULT_FORMAT = 'json'").collect()
    token_data = session.connection._rest._token_request('ISSUE')
    token_extract = token_data["data"]["sessionToken"]
    token = f'\"{token_extract}\"'
    header = {'Authorization': f'Snowflake Token={token}'}
    return header

# Function to reset the conversation state
def reset():
    st.session_state["max_length_slider"] = 2500
    st.session_state["top_k_slider"] = 1
    st.session_state["top_p_slider"] = 0.8
    st.session_state["temperature_slider"] = 0.8
    st.session_state["stream_toggle"] = False
    st.session_state['payload'] = {}
    st.session_state.messages = []
    st.session_state.image = None
    st.session_state.file_url = None
    st.session_state.file_selection = None
    # Add initial assistant messages
    content = [{'type':'text', 'text':'What can I help you with?'}]
    st.session_state.messages.append({"role": "assistant", "content": content})

def file_handler(file_bytes):
    if file_bytes.startswith((b'\xff\xd8\xff', b'\x89\x50\x4e\x47')):
        # PNG/JPG
        image = Image.open(BytesIO(file_bytes)).convert('RGB')
    if file_bytes.startswith(b'%PDF'):
        # PDF
        file = pdfium.PdfDocument(file_bytes)
        n_pages = len(file)
        page_selection = st.selectbox('Select Page:', list(range(n_pages)))
        st.session_state.pdf_page = page_selection
        page = file[page_selection]
        bitmap = page.render(scale=1, rotation=0)
        image = bitmap.to_pil()
    resized_image = resize_image_to_max_height(image, 500)
    return resized_image
    
@st.cache_data
def retrieve_stages():
    stages = pd.DataFrame(session.sql("SHOW STAGES like 'IMAGE_FILES'").collect()) ### remove like statement here
    stages['FULL_PATH'] = stages['database_name'] + '.' + stages['schema_name'] + '.' + stages['name']
    stages = stages.sort_values(by=['database_name', 'schema_name', 'name'])
    stages = stages['FULL_PATH']
    return stages

@st.cache_data
def retrieve_stage_files(stage):
    files = pd.DataFrame(session.sql(f"SELECT RELATIVE_PATH FROM DIRECTORY(@{stage})").collect())
    files = files.sort_values(by=['RELATIVE_PATH'])
    files = files['RELATIVE_PATH']
    return files

@st.cache_data
def retrieve_stage_file_bytes(stage_selection, file_selection):
    file_bytes = session.file.get_stream(f"@{stage_selection}/{file_selection}").read()
    return file_bytes

# Function to retrieve stage and file from Snowflake
def get_file_from_snowflake(key):
    st.session_state.base64_image_string = None
    with st.expander('Select a file', expanded=True):
        stages = retrieve_stages()
        stage_selection = st.selectbox('Select Stage:', stages, key=key+'_stage_selection')
        files = retrieve_stage_files(stage_selection)
        file_selection = st.selectbox('Select File:', files, key=key+'_file_selection')
        file_bytes = retrieve_stage_file_bytes(stage_selection, file_selection)
        image = file_handler(file_bytes)
        st.image(image)
        if st.button('Select file', key+'_file_button'):
            st.session_state.file_url = session.sql(f"SELECT GET_PRESIGNED_URL('@{stage_selection}','{file_selection}') AS FILE_URL").collect()[0]['FILE_URL']
            st.session_state.image = image
            st.session_state.file_selection = file_selection
            st.session_state.messages[-1]['content'][0]['misc'] = image
            return image

def get_file_from_url(key):
    st.session_state.base64_image_string = None
    with st.expander('Provide URL', expanded=True):
        url = st.text_area('URL to file:', key=key+'_input_url')
        if st.button('Select URL', key+'_url_button'):
            st.session_state.messages[-1]['content'][0]['misc'] = url
            st.session_state.file_url = url
            st.session_state.image = None
            st.session_state.file_selection = None
            return url

def get_file_from_upload(key):
    try:
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "pdf"], key=key+'_uploader')
        if uploaded_file is not None:
            uploaded_file = uploaded_file.getvalue()
            image = file_handler(uploaded_file)
            st.image(image, caption='Uploaded Image', use_column_width=True)
            if st.button('Select File', key+'_upload_button'):
                st.session_state.image = image
                st.session_state.base64_image_string = pil_image_to_base64(image)
                st.session_state.messages[-1]['content'][0]['misc'] = image
                return uploaded_file
    except Exception as e:
        st.error(e)

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


# Function to stream response
def streamed_response(prompt):
    prompt = {'data':[[1,prompt]]}
    if st.session_state.execution_location == 'EXTERNAL':
        llm_url = st.session_state.ingress_url
        header = get_header_token(token_session)
    if st.session_state.execution_location == 'SPCS':
        llm_url = 'http://localhost:9000/complete'
        header = {}
    with requests.post(llm_url, json=prompt, headers=header, stream=True) as response:
        if response.status_code == 200:
            for chunk in response.iter_content():
                if chunk:  # Filter out keep-alive new chunks
                    try:
                        chunk = chunk.decode("utf-8")
                    except Exception as e:
                        chunk = ''
                    yield chunk
        else:
            st.error(response.status_code)

def query_snowflake(payload):
    prompt = payload['prompt'].replace("'", "\\'")
    args = payload['args']
    sql = f"SELECT GLM_V4_9B({{'prompt': '{prompt}', 'args': {args}}})['LLM_OUTPUT_TEXT']::TEXT AS LLM_RESPONSE;"
    return sql

# Function to resize an image to a maximum height while maintaining the aspect ratio
def resize_image_to_max_height(image, max_height):
    # Get original dimensions
    original_width, original_height = image.size
    
    # Check if resizing is necessary
    if original_height <= max_height:
        return image  # No resizing needed
    
    # Calculate the new dimensions while maintaining the aspect ratio
    aspect_ratio = original_width / original_height
    new_height = max_height
    new_width = int(new_height * aspect_ratio)
    
    # Resize the image
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)
    return resized_image

def update_payload(prompt):
    generation_args = {
        'max_length':st.session_state.max_length,
        'top_k': st.session_state.top_k,
        'top_p': st.session_state.top_p,
        'temperature':st.session_state.temperature
    }
    args = {
        'stream': st.session_state.stream,
        'generation_args':generation_args
    }
    
    if st.session_state.file_url is not None:
        args['file_url'] = st.session_state.file_url
    if st.session_state.pdf_page is not None:
        args['pdf_page'] = st.session_state.pdf_page
    if st.session_state.base64_image_string is not None:
        args['base64_image_string'] = st.session_state.base64_image_string
    
    payload = {
        'prompt':prompt,
        'args':args
    }
    st.session_state.payload = payload
    
cmd_file = ['/file']
cmd_url = ['/url']
cmd_upload = ['/upload']
def handle_prompt(payload):
    if payload['prompt'] in cmd_file:
        update_payload(payload['prompt'])
        return [{'type':'file','payload':payload, 'misc':None}]
    
    if payload['prompt'] in cmd_url:
        update_payload(payload['prompt'])
        return [{'type':'url','payload':payload, 'misc': None}]
    
    if payload['prompt'] in cmd_upload:
        update_payload(payload['prompt'])
        return [{'type':'upload','payload':payload, 'misc':None}]
    else:
        if st.session_state['stream'] == False:
            update_payload(payload['prompt'])
            query = query_snowflake(payload)
            return [{"type":"query",'query':query, 'misc':None}]
        else:
            return [{"type":"query",'query':payload, 'misc':None}]
            

def process_message(payload: dict) -> None:
    """Processes a message and adds the response to the chat."""
    st.session_state.messages.append({"role": "user", "content": [{"type": "text", "text": payload['prompt']}]})
    with st.chat_message("user"):
        st.markdown(payload['prompt'])
    with st.chat_message("assistant"):
            content = handle_prompt(payload)
            display_content(content=content)
    content[0]['misc'] = st.session_state['misc']
    st.session_state.messages.append({"role": "assistant", "content": content})
    st.session_state['misc'] = None # to avoid reloading images


def display_content(content: list, message_index: int = None) -> None:
    """Displays a content item for a message."""
    message_index = message_index or len(st.session_state.messages)
    for item in content:
        if item["type"] == "text":
            st.markdown(item["text"])
        if item["type"] == "query":
            if st.session_state['stream']:
                if item['misc'] is None:
                    response = st.write_stream(streamed_response(item["query"]))
                    st.session_state['misc'] = response
                else:
                    st.markdown(item['misc'])
            else:
                if item['misc'] is None:
                    response = session.sql(item['query']).collect()[0]['LLM_RESPONSE']
                    st.session_state['misc'] = response
                    st.markdown(response)
                else:
                    st.markdown(item['misc'])
        if item['type'] == "file":
            if item['misc'] is None:
                image = get_file_from_snowflake(f"{message_index}")
            else:
                st.markdown('Selected Image:')
                st.image(item['misc'])
        if item['type'] == "url":
            if item['misc'] is None:
                url = get_file_from_url(f"{message_index}")
            else:
                st.markdown('Selected URL:')
                st.markdown(item['misc'])
        if item['type'] == "upload":
            if item['misc'] is None:
                file = get_file_from_upload(f"{message_index}")
                #st.session_state['misc'] = st.session_state['file_url']
            else:
                st.markdown('Uploaded File:')
                st.image(item['misc'])

if "messages" not in st.session_state:
    st.session_state.messages = []
    content = [{'type':'text', 'text':'What can I help you with?'}]
    st.session_state.messages.append({"role": "assistant", "content": content})

if 'max_length_slider' not in st.session_state:
    st.session_state["max_length_slider"] = 2500
    st.session_state["max_length"] = 2500

if 'top_k_slider' not in st.session_state:
    st.session_state["top_k_slider"] = 1
    st.session_state["top_k"] = 1

if 'top_p_slider' not in st.session_state:
    st.session_state["top_p_slider"] = 0.8
    st.session_state["top_p"] = 0.8

if 'temperature_slider' not in st.session_state:
    st.session_state["temperature_slider"] = 0.8
    st.session_state["temperature"] = 0.8

if 'stream_toggle' not in st.session_state:
    st.session_state["stream_toggle"] = False
    st.session_state["stream"] = False

if 'payload' not in st.session_state:
    st.session_state['payload'] = {}
  
if 'image' not in st.session_state:
    # save PIL images for visualization
    st.session_state.image = None

if 'file_url' not in st.session_state:
    # save urls to files
    st.session_state.file_url = None

if 'file_selection' not in st.session_state:
    # save path to files
    st.session_state.file_selection = None

if 'pdf_page' not in st.session_state:
    # save path to files
    st.session_state.pdf_page = None

if 'misc' not in st.session_state:
    # save path to files
    st.session_state.misc = None

if 'execution_location' not in st.session_state:
    # save path to files
    st.session_state.execution_location = None

if 'ingress_url' not in st.session_state:
    # save path to files
    st.session_state.ingress_url = False

if 'base64_image_string' not in st.session_state:
    # save path to files
    st.session_state.base64_image_string = None

# Find out where streamlit is running
if os.path.isfile("/snowflake/session/token"):
    st.session_state.execution_location  = 'SPCS'
elif os.path.isfile(".env"):
    st.session_state.execution_location  = 'EXTERNAL'
else:
    st.session_state.execution_location  = 'SIS'

# Get the current session from Snowflake
session = create_snowpark_session(1)
token_session = create_snowpark_session(2)

def retrieve_endpoint():
    ingress_url = None
    endpoints = session.sql('SHOW ENDPOINTS IN SERVICE GLM_V4_9B_SERVICE').collect()
    for endpoint in endpoints:
        if endpoint['name'] == 'api':
            ingress_url = f"https://{endpoint['ingress_url']}/complete"
    if ingress_url is not None:
        st.session_state.ingress_url = ingress_url
    else:
        st.error('Ingress URL is not available.')

# Sidebar content
with st.sidebar:
    st.title("Multimodal Model in Snowflake! 🤖📄🖼️")
    st.markdown("Model: [THUDM/glm-4v-9b model.](https://huggingface.co/THUDM/glm-4v-9b)")
    st.button('Reset Chat', on_click=reset, use_container_width=True)
    st.write(f'Streamlit App Location: {st.session_state.execution_location}')
    st.subheader('LLM Settings:')
    st.session_state.max_length = st.slider('max_length:', min_value=20, max_value=5000, on_change=update_payload(''), key='max_length_slider')
    st.session_state.top_k = st.slider('top_k:', min_value=1, max_value=100, on_change=update_payload(''), key='top_k_slider')
    st.session_state.top_p = st.slider('top_p:', min_value=0.01, max_value=1.0, on_change=update_payload(''), key='top_p_slider')
    st.session_state.temperature = st.slider('temperature:', min_value=0.01, max_value=1.0, on_change=update_payload(''), key='temperature_slider')
    # Disable streaming which is not supported in SIS because we can't create an ouath token to call SPCS directly
    if st.session_state.execution_location != 'SIS':
        st.session_state.stream = st.toggle('Stream Responses?', key='stream_toggle', on_change=retrieve_endpoint)
    if st.button('Show Cache Data'):
        st.json(st.session_state)

#if st.session_state.ingress_url:
#    st.sidebar.write(f'Ingress URL:  \n  {st.session_state.ingress_url}')

for message_index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        display_content(content=message["content"], message_index=message_index)

# Display the active image in the sidebar if available
if st.session_state.image:
    if st.session_state.file_selection is not None:
        caption = st.session_state.file_selection
    else:
        caption = 'Uploaded File'
    st.sidebar.image(st.session_state.image, caption=caption)

# Display the active file url in the sidebar if available
if st.session_state.file_url:
    st.sidebar.markdown(f'[Link to File]({st.session_state.file_url})')

if user_input := st.chat_input("What is your question?"):
    st.session_state.payload['prompt'] = user_input
    process_message(st.session_state.payload)