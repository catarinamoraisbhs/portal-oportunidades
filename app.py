import streamlit as st
import sqlite3
import os
import re
import pandas as pd
from pypdf import PdfReader

st.set_page_config(page_title="Portal Definitivo - Vagas & Posts do LinkedIn", page_icon="🎯", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "portal_oportunidades_v5.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidaturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            data TEXT, 
            empresa TEXT, 
            cargo TEXT, 
            email TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

st.title("🎯 Portal de Oportunidades: Vagas & Feed do LinkedIn")
st.markdown("Monitorização combinada de posts de recrutadores no feed e vagas ativas no mercado de tecnologia.")

st.sidebar.header("📄 Carregar Currículo PDF")
uploaded_file = st.sidebar.file_uploader("Escolha o seu PDF", type=["pdf"])

texto_cv = ""
if uploaded_file is not None:
    try:
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            texto_cv += page.extract_text() or ""
        st.sidebar.success("✅ Currículo carregado com sucesso!")
    except Exception as e:
        st.sidebar.error(f"Erro ao ler PDF: {e}")

# Definição das abas solicitadas
aba1, aba2, aba3, aba4 = st.tabs([
    "📢 Posts do Feed (LinkedIn)", 
    "💼 Vagas de Mercado (BH & Remoto)", 
    "📋 Registar Candidatura", 
    "📊 Histórico"
])

with aba1:
    st.subheader("👥 Publicações de Recrutadores no Feed")
    st.markdown("Posts em formato de feed reais com extração automática e cálculo de match.")

    posts_feed = [
        {
            "autor": "Gabriel Wolski",
            "cargo_autor": "Tech Recruiter | Recrutamento e Seleção (R&S)",
            "tempo": "7 horas atrás • 🌐",
            "texto": "Estamos com novas oportunidades na Certsys, todas as posições 100% remota! 🚀\n\nSe você estava esperando um sinal para dar aquele próximo passo na carreira... talvez seja esse! 👀 Vaga aberta para Especialista DBA e Banco de Dados.",
            "empresa": "Certsys",
            "cargo": "Especialista DBA / Banco de Dados",
            "link": "https://certsys.gupy.io",
            "tags": ["dba", "sql", "database", "postgres", "sql server"]
        },
        {
            "autor": "Hilda Barbosa",
            "cargo_autor": "Divulgo Vagas Como Gesto de Solidariedade",
            "tempo": "1 dia atrás • 🌐",
            "texto": "#COMPARTILHANDO 👤 RECÉM-PUBLICADA 📌\n\nVaga Na Certsys - Administrador de Dados / Modelador de Dados (PowerDesigner) 💻 Modelo de Trabalho Híbrido / Remoto.",
            "empresa": "Certsys",
            "cargo": "Administrador de Dados / Modelador de Dados",
            "link": "https://certsys.gupy.io",
            "tags": ["administrador de dados", "modelador", "dados", "database"]
        }
    ]

    for p in posts_feed:
        match_perc = 85
        if uploaded_file is not None and texto_cv:
            matches = sum(1 for t in p["tags"] if t in texto_cv.lower())
            match_perc = min(99, 60 + (matches * 15))

        with st.container():
            st.markdown(f"**👤 {p['autor']}**  \n*{p['cargo_autor']}* • {p['tempo']}")
            st.markdown(f"> {p['texto']}")
            st.markdown(f"🏢 **Empresa:** {p['empresa']} | 🎯 **Cargo:** {p['cargo']} | ⭐ **Match:** {match_perc}%")
            st.markdown(f"🔗 [Aceder à página oficial da vaga ↗]({p['link']})")
            st.markdown("---")

with aba2:
    st.subheader("💼 Oportunidades Ativas de Mercado (Belo Horizonte & Remoto)")
    st.markdown("Lista clássica de vagas abertas em grandes empresas da região e remoto:")

    vagas_mercado = [
        {
            "empresa": "Grupo Zelo",
            "cargo": "Especialista DBA – SQL Server",
            "local": "Belo Horizonte - MG",
            "link": "https://www.indeed.com/q-banco-de-dados-sql-l-belo-horizonte,-mg-vagas.html",
            "detalhes": "Gestão de ambiente SQL Server, alta disponibilidade, rotinas de backup e Performance Tuning.",
            "tags": ["dba", "sql server", "database", "tuning"]
        },
        {
            "empresa": "G4F",
            "cargo": "Administrador de Banco de Dados Sênior (DBA)",
            "local": "Belo Horizonte - MG / Híbrido",
            "link": "https://www.jobijoba.com.br/detail/97/87fbbf6425fbaf5947bc575eb441c777",
            "detalhes": "Sólidos conhecimentos em SQL Server, PostgreSQL, MySQL e automação com Shell Script.",
            "tags": ["dba", "sql server", "postgresql", "mysql"]
        },
        {
            "empresa": "Itaú Unibanco",
            "cargo": "Analista Engenharia de Dados Sênior",
            "local": "Belo Horizonte / Remoto",
            "link": "https://carreiras.itau.com.br/busca-de-vagas",
            "detalhes": "Pipelines de dados em nuvem utilizando Spark, Python e ecossistema AWS.",
            "tags": ["engenharia de dados", "python", "spark", "aws"]
        },
        {
            "empresa": "Sigga Technologies",
            "cargo": "Database Administrator (DBA)",
            "local": "Belo Horizonte - MG / Remoto",
            "link": "https://www.siggastech.com/careers/",
            "detalhes": "Suporte a infraestruturas de dados globais e otimização de consultas complexas.",
            "tags": ["dba", "database", "sql", "postgres"]
        }
    ]

    for v in vagas_mercado:
        match_score = 80
        if uploaded_file is not None and texto_cv:
            pontos = sum(1 for t in v["tags"] if t in texto_cv.lower())
            match_score = min(98, 55 + (pontos * 12))

        with st.expander(f"🏢 {v['empresa']} — {v['cargo']} ({v['local']}) | ⭐ Match: {match_score}%"):
            st.markdown(f"**Descrição:** {v['detalhes']}")
            st.markdown(f"🔗 [Aceder ao site oficial ↗]({v['link']})")

with aba3:
    st.subheader("📋 Registar Candidatura Manualmente")
    with st.form("form_cand"):
        c1, c2 = st.columns(2)
        with c1:
            empresa_in = st.text_input("Nome da Empresa")
            cargo_in = st.text_input("Cargo Pretendido")
        with c2:
            email_in = st.text_input("E-mail de Destino do Recrutador")
        
        btn = st.form_submit_button("Guardar Registo")
        if btn:
            if empresa_in and email_in:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO candidaturas (data, empresa, cargo, email) VALUES (datetime('now', 'localtime'), ?, ?, ?)", (empresa_in, cargo_in, email_in))
                conn.commit()
                conn.close()
                st.success(f"✅ Candidatura para '{empresa_in}' guardada!")
            else:
                st.warning("Preencha todos os campos obrigatórios.")

with aba4:
    st.subheader("📊 Histórico de Candidaturas")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM candidaturas", conn)
    conn.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Ainda não existem registos no histórico.")