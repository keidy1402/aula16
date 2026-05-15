!pip install google-genai

import os 
from google.colab import userdata

from google import genai
client = genai.Client()
model_id = "gemini-2.5-flash"

from IPython.display import HTML, Markdown

resposta = client.models.generate_content(
    model=model_id,
    contents='Me diga o que você sabe sobre o BTS',
)
display(Markdown(f"Resposta:\n {resposta.text}"))
