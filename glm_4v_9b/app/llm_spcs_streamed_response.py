# Import python packages
import streamlit as st
import pandas as pd
from io import BytesIO
from PIL import Image
import requests
import base64
import os
import snowflake.connector
from snowflake.snowpark import Session

image_url = ''

with st.sidebar:
    # Write directly to the app
    st.title("Multimodal Model in Snowflake! 🤖📄🖼️")
    st.markdown("Model: [THUDM/glm-4v-9b model.](https://huggingface.co/THUDM/glm-4v-9b)")
    prompt = st.text_area('Prompt: ', value='Describe this image.')
    max_length = st.slider('max_length:', value=2500, min_value=10, max_value=5000)
    top_k = st.slider('top_k:', value=1, min_value=1, max_value=100)
    top_p = st.slider('top_p:', value=0.8, min_value=0.0, max_value=1.0)
    temperature = st.slider('temperature:', value=0.8, min_value=0.0, max_value=1.0)
    
# Snowflake Session
def create_snowpark_session():
    creds = {
        'host': os.getenv('SNOWFLAKE_HOST'),
        'protocol': "https",
        'account': os.getenv('SNOWFLAKE_ACCOUNT'),
        'authenticator': "oauth",
        'token': open('/snowflake/session/token', 'r').read(),
        'warehouse': 'COMPUTE_WH',
        'database': os.getenv('SNOWFLAKE_DATABASE'),
        'schema': os.getenv('SNOWFLAKE_SCHEMA'),
        'client_session_keep_alive': True
    }
    connection = snowflake.connector.connect(**creds)
    session = Session.builder.configs({"connection": connection}).create()
    return session

session = create_snowpark_session()

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

def streamed_response(llm_url, prompt):
    with requests.post(llm_url, json=prompt, stream=True) as response:
        if response.status_code == 200:
            print(response)
            for chunk in response.iter_content():
                if chunk:  # Filter out keep-alive new chunks
                    try:
                        chunk = chunk.decode("utf-8")
                    except Exception as e:
                        chunk = ''
                    yield chunk

tab1, tab2, tab3, tab4 = st.tabs(['Standard Chatting', 'Query Image data in Snowflake','Query Image data from URLs','Upload Image from Local'])

with tab1:
    if st.button('Ask!'):
        llm_url = 'http://localhost:9000/complete_stream'
        generation_args = {'max_length':max_length,'top_k':top_k,'top_p':top_p,'temperature':temperature}
        prompt = {
            "data":[[prompt, generation_args]]
        }
        st.write_stream(streamed_response(llm_url, prompt))
        
with tab2:
    stages = pd.DataFrame(session.sql("SHOW STAGES like 'IMAGE_FILES'").collect())
    stages['FULL_PATH'] = stages['database_name'] + '.' + stages['schema_name'] + '.' + stages['name']
    stages = stages.sort_values(by=['database_name', 'schema_name', 'name'])
    stage_selection = st.selectbox('Select Stage:', stages['FULL_PATH'])
    files = pd.DataFrame(session.sql(f"SELECT RELATIVE_PATH FROM DIRECTORY(@{stage_selection})").collect())
    files = files.sort_values(by=['RELATIVE_PATH'])
    file_selection = st.selectbox('Select File:', files['RELATIVE_PATH'])
    image = session.file.get_stream(f"@{stage_selection}/{file_selection}")
    image = Image.open(BytesIO(image.read())).convert('RGB')
    st.image(image, caption='Image in Snowflake', use_column_width=True)
    if st.button('Query my image in Snowflake!'):
        llm_url = 'http://localhost:9000/complete_image_stream'
        image = pil_image_to_base64(image)
        generation_args = {'max_length':max_length,'top_k':top_k,'top_p':top_p,'temperature':temperature,'base64_image_string':image}
        prompt = {
            "data":[[prompt, generation_args, image_url]]
        }
        st.write_stream(streamed_response(llm_url, prompt))

with tab3:
    image_url = st.text_input('URL:', value='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTGtsjtT26xLbvGO_eRAcJJ2drgv6wC9S7REQ&s')
    if st.button('Query my image url!'):
        llm_url = 'http://localhost:9000/complete_image_stream'
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content)).convert('RGB')
        st.image(image, caption='Uploaded Image', use_column_width=True)
        generation_args = {'max_length':max_length,'top_k':top_k,'top_p':top_p,'temperature':temperature}
        prompt = {
            "data":[[prompt, generation_args, image_url]]
        }
        st.write_stream(streamed_response(llm_url, prompt))
        
with tab4:
    # Create a file uploader widget
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        # Convert the uploaded file to a PIL image
        image = Image.open(BytesIO(uploaded_file.read())).convert('RGB')
        
        # Display the image
        st.image(image, caption='Uploaded Image', use_column_width=True)
    
        if st.button('Query my image file!'):
            llm_url = 'http://localhost:9000/complete_image_stream'
            image = pil_image_to_base64(image)
            generation_args = {'max_length':max_length,'top_k':top_k,'top_p':top_p,'temperature':temperature,'base64_image_string':image}
            prompt = {
                "data":[[prompt, generation_args, image_url]]
            }
            st.write_stream(streamed_response(llm_url, prompt))
    else:
        st.write("Please upload an image file.")