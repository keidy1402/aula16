import os
import json
import re
import urllib.request
import urllib.parse
from typing import List, Dict

import streamlit as st
import google.generativeai as genai

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================

st.set_page_config(
    page_title="Analisador de Privacidade",
    page_icon="🔒",
    layout="wide"
)

# =========================================================
# CHAVES DAS APIs
# =========================================================

GEMINI_API_KEY = os.environ.get("AIzaSyB7S6S4qzxCXTIhT5VlliHzOoT9IEFGcXc")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")

if not GEMINI_API_KEY:
    st.error("Defina a variável de ambiente GEMINI_API_KEY")
    st.stop()

if not NEWSAPI_KEY:
    st.error("Defina a variável de ambiente NEWSAPI_KEY")
    st.stop()

# =========================================================
# CONFIGURAÇÃO GEMINI
# =========================================================

genai.configure(api_key=AIzaSyB7S6S4qzxCXTIhT5VlliHzOoT9IEFGcXc)

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash"
)

# =========================================================
# FUNÇÃO: BUSCAR NOTÍCIAS
# =========================================================

def buscar_noticias(plataforma: str) -> List[Dict]:

    params = urllib.parse.urlencode({
        "q": f"{plataforma} privacidade dados vazamento",
        "language": "pt",
        "sortBy": "relevancy",
        "pageSize": 6,
        "apiKey": NEWSAPI_KEY
    })

    url = f"https://newsapi.org/v2/everything?{params}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())

        if data.get("status") != "ok":
            print(data)
            return []

        noticias = []

        for article in data.get("articles", [])[:6]:

            title = article.get("title")
            article_url = article.get("url")

            if (
                title
                and article_url
                and "[Removed]" not in title
            ):
                noticias.append({
                    "title": title,
                    "source": article.get("source", {}).get("name", ""),
                    "url": article_url,
                    "publishedAt": article.get("publishedAt", "")[:10],
                    "description": article.get("description", "")
                })

        return noticias

    except Exception as e:
        print(f"Erro NewsAPI: {e}")
        return []

# =========================================================
# PROMPT
# =========================================================

def build_prompt(plataforma: str, noticias: List[Dict]) -> str:

    noticias_str = json.dumps(
        noticias,
        ensure_ascii=False,
        indent=2
    )

    return f"""
Você é um especialista em privacidade digital e LGPD.

Analise os termos de privacidade da plataforma "{plataforma}".

Responda SOMENTE JSON válido.

NOTICIAS:
{noticias_str}

Formato obrigatório:

{{
  "platform": "{plataforma}",
  "riskLevel": "alto",
  "riskScore": 3,

  "summary": "Resumo simples da política.",

  "attentionPoints": [
    {{
      "title": "Coleta de dados",
      "description": "Descrição"
    }}
  ],

  "criticalWords": [
    {{
      "word": "dados",
      "size": 40
    }}
  ],

  "topWord": "dados",

  "topWordExplanation": "Explicação.",

  "platformRisks": [
    {{
      "name": "Instagram",
      "score": 3
    }}
  ],

  "news": [
    {{
      "tag": "Privacidade",
      "title": "Título",
      "source": "Fonte",
      "url": "URL",
      "publishedAt": "2026-01-01",
      "summary": "Resumo"
    }}
  ]
}}

REGRAS:
- Responda SOMENTE JSON
- Não use markdown
- Não explique nada
- riskScore:
  1 = baixo
  2 = médio
  3 = alto
"""

# =========================================================
# EXTRAIR JSON
# =========================================================

def extrair_json(texto: str):

    texto = re.sub(r"```json|```", "", texto).strip()

    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(texto)
        return obj

    except Exception:
        return None

# =========================================================
# CHAMAR GEMINI
# =========================================================

def analisar_plataforma(plataforma: str):

    noticias = buscar_noticias(plataforma)

    prompt = build_prompt(
        plataforma,
        noticias
    )

    try:

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "response_mime_type": "application/json"
            },
            request_options={
                "timeout": 30
            }
        )

        resultado = extrair_json(response.text)

        if not resultado:
            return {
                "erro": "Não foi possível interpretar a resposta da IA."
            }

        # Fallback das notícias
        if not resultado.get("news") and noticias:

            resultado["news"] = [
                {
                    "tag": "Notícia",
                    "title": n["title"],
                    "source": n["source"],
                    "url": n["url"],
                    "publishedAt": n["publishedAt"],
                    "summary": n["description"]
                }
                for n in noticias[:3]
            ]

        return resultado

    except Exception as e:

        print(e)

        return {
            "erro": "Erro ao processar a análise."
        }

# =========================================================
# INTERFACE
# =========================================================

st.title("🔒 Analisador de Privacidade Digital")

st.write(
    """
Analise plataformas digitais, entenda riscos de privacidade,
coleta de dados e notícias relacionadas.
"""
)

# =========================================================
# INPUT
# =========================================================

plataforma = st.text_input(
    "Digite o nome da plataforma",
    placeholder="Ex: Instagram"
)

# =========================================================
# BOTÃO
# =========================================================

if st.button("Analisar"):

    if not plataforma.strip():

        st.warning("Digite o nome de uma plataforma.")

    else:

        # Sanitização
        plataforma = re.sub(
            r"[^a-zA-Z0-9À-ÿ\s\-\._]",
            "",
            plataforma
        )

        with st.spinner("Analisando política de privacidade..."):

            resultado = analisar_plataforma(plataforma)

        # =====================================================
        # ERRO
        # =====================================================

        if resultado.get("erro"):

            st.error(resultado["erro"])

        else:

            # =================================================
            # CABEÇALHO
            # =================================================

            st.header(resultado.get("platform", plataforma))

            risco = resultado.get("riskLevel", "desconhecido")
            score = resultado.get("riskScore", 0)

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Nível de risco", risco.upper())

            with col2:
                st.metric("Score", score)

            # =================================================
            # RESUMO
            # =================================================

            st.subheader("📄 Resumo")

            st.write(resultado.get("summary", ""))

            # =================================================
            # PONTOS DE ATENÇÃO
            # =================================================

            st.subheader("⚠️ Pontos de atenção")

            for ponto in resultado.get("attentionPoints", []):

                st.markdown(
                    f"""
                    ### {ponto.get("title", "")}

                    {ponto.get("description", "")}
                    """
                )

            # =================================================
            # PALAVRAS CRÍTICAS
            # =================================================

            st.subheader("🧠 Palavras críticas")

            critical_words = resultado.get("criticalWords", [])

            if critical_words:

                palavras = []

                for item in critical_words:

                    palavra = item.get("word", "")
                    tamanho = item.get("size", 0)

                    palavras.append(
                        f"""
                        <span style="
                            font-size:{tamanho}px;
                            margin-right:12px;
                            color:#104f7e;
                            font-weight:bold;
                        ">
                            {palavra}
                        </span>
                        """
                    )

                st.markdown(
                    " ".join(palavras),
                    unsafe_allow_html=True
                )

            # =================================================
            # PALAVRA MAIS IMPORTANTE
            # =================================================

            st.subheader("🔍 Palavra mais relevante")

            st.markdown(
                f"""
                ### {resultado.get("topWord", "")}

                {resultado.get("topWordExplanation", "")}
                """
            )

            # =================================================
            # RISCO DAS PLATAFORMAS
            # =================================================

            st.subheader("📊 Comparação de risco")

            platform_risks = resultado.get("platformRisks", [])

            if platform_risks:

                for item in platform_risks:

                    nome = item.get("name", "")
                    score = item.get("score", 0)

                    st.progress(score / 3)

                    st.write(f"{nome} — Score: {score}/3")

            # =================================================
            # NOTÍCIAS
            # =================================================

            st.subheader("📰 Notícias relacionadas")

            noticias = resultado.get("news", [])

            if noticias:

                for noticia in noticias:

                    st.markdown(
                        f"""
### [{noticia.get("title", "")}]({noticia.get("url", "#")})

**Fonte:** {noticia.get("source", "")}  
**Data:** {noticia.get("publishedAt", "")}  
**Categoria:** {noticia.get("tag", "")}

{noticia.get("summary", "")}
"""
                    )

            else:

                st.info("Nenhuma notícia encontrada.")
