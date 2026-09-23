import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from pypdf import PdfReader

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Portal de Oportunidades: DBA & Dados",
    page_icon="🎯",
    layout="wide"
)

DB_NAME = "portal_oportunidades_v5.db"

# --- 2. FUNÇÕES DE SEGURANÇA E BASE DE DADOS ---
def make_hash(password):
    """Gera um hash seguro da palavra-passe."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password, hashed_text):
    """Verifica se a palavra-passe corresponde ao hash guardado."""
    return make_hash(password) == hashed_text

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela de candidaturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidaturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa TEXT,
            cargo TEXT,
            status TEXT,
            data TEXT,
            observacoes TEXT
        )
    ''')
    
    # Tabela de utilizadores (para login seguro)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    
    # Criar um utilizador admin padrão se a tabela estiver vazia (Catarina / admin123)
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        default_user = "catarina"
        default_pass = make_hash("00252318@Ca") # Podes alterar aqui a senha inicial se desejares
        cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", (default_user, default_pass))
    
    conn.commit()
    conn.close()

init_db()

# --- 3. SISTEMA DE LOGIN COM BASE DE DADOS ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["username"] = ""

if not st.session_state["autenticado"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>🎯 Portal de Oportunidades</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>Painel Restrito de Gestão de Carreira (DBA / Engenharia de Dados)</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### 🔒 Acesso Restrito (Base de Dados)")
            user_input = st.text_input("Utilizador")
            senha_input = st.text_input("Palavra-passe", type="password")
            
            if st.button("Entrar no Portal", use_container_width=True, type="primary"):
                if user_input and senha_input:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("SELECT password FROM usuarios WHERE username = ?", (user_input,))
                    resultado = cursor.fetchone()
                    conn.close()
                    
                    if resultado and check_hash(senha_input, resultado[0]):
                        st.session_state["autenticado"] = True
                        st.session_state["username"] = user_input
                        st.rerun()
                    else:
                        st.error("❌ Utilizador ou palavra-passe incorretos!")
                else:
                    st.warning("⚠️ Por favor, preencha todos os campos.")
    
    st.stop()  # Impede que o resto da aplicação seja carregado sem autenticação

# --- 4. FUNÇÕES DE SUPORTE (PDF E MATCH) ---
def extrair_texto_pdf(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() or ""
        return texto
    except Exception as e:
        st.error(f"Erro ao ler PDF: {e}")
        return ""

def calcular_match(texto_curriculo, requisitos_vaga):
    if not texto_curriculo:
        return 50 # Match padrão se não houver currículo carregado
    
    texto_curriculo_lower = texto_curriculo.lower()
    palavras_chave = ["sql", "python", "dba", "etl", "aws", "azure", "postgres", "mysql", "oracle", "power bi", "pandas", "git", "linux", "docker"]
    
    encontradas = sum(1 for p in palavras_chave if p in texto_curriculo_lower and p in requisitos_vaga.lower())
    match_base = 60 + (encontradas * 7)
    return min(match_base, 98) # Limita a 98% máximo

# --- 5. BARRA LATERAL (UPLOAD DE CURRÍCULO & UTILIZADOR) ---
with st.sidebar:
    st.markdown(f"👤 **Sessão iniciada:** `{st.session_state['username']}`")
    st.markdown("---")
    st.markdown("## 📄 Carregar Currículo PDF")
    uploaded_file = st.file_uploader("Escolha o seu PDF", type=["pdf"])
    
    texto_curriculo = ""
    if uploaded_file is not None:
        texto_curriculo = extrair_texto_pdf(uploaded_file)
        st.success("Currículo carregado com sucesso!")
    
    st.markdown("---")
    if st.button("🚪 Terminar Sessão"):
        st.session_state["autenticado"] = False
        st.session_state["username"] = ""
        st.rerun()

# --- 6. CORPO PRINCIPAL DO PORTAL ---
st.title("🎯 Portal de Oportunidades: Vagas & Feed do LinkedIn")
st.markdown("Monitorização combinada de posts de recrutadores no feed e vagas ativas no mercado de tecnologia em Belo Horizonte e Remoto.")

tab1, tab2, tab3, tab4 = st.tabs([
    "📢 Posts do Feed (LinkedIn)", 
    "💼 Vagas de Mercado (BH & Remoto)", 
    "📝 Registar Candidatura", 
    "📊 Histórico & Relatórios"
])

# --- ABA 1: POSTS DO FEED (LINKEDIN) ---
with tab1:
    st.subheader("👥 Publicações de Recrutadores no Feed")
    st.markdown("Posts em formato de feed reais com extração automática e cálculo de match com o seu perfil.")
    
    posts_feed = [
        {
            "recrutador": "Gabriel Wolski",
            "cargo_info": "Tech Recruiter | Recrutamento e Seleção (R&S)",
            "tempo": "7 horas atrás",
            "conteudo": "Estamos com novas oportunidades na Certsys, todas as posições 100% remota! 🚀\n\nSe você estava esperando um sinal para dar aquele próximo passo na carreira... talvez seja esse!  👀 Vaga aberta para Especialista DBA e Banco de Dados.",
            "empresa": "Certsys",
            "cargo": "Especialista DBA / Banco de Dados",
            "requisitos": "sql dba postgresql oracle aws",
            "link": "https://www.linkedin.com"
        },
        {
            "recrutador": "Hilda Barbosa",
            "cargo_info": "Divulgo Vagas Como Gesto de Solidariedade",
            "tempo": "1 dia atrás",
            "conteudo": "Vaga Na Certsys - Administrador de Dados / Modelador de Dados (PowerDesigner) 🖥️ Modelo de Trabalho Híbrido / Remoto.",
            "empresa": "Certsys",
            "cargo": "Administrador de Dados / Modelador de Dados",
            "requisitos": "modelagem de dados sql powerdesigner dba",
            "link": "https://www.linkedin.com"
        }
    ]
    
    for post in posts_feed:
        with st.container(border=True):
            st.markdown(f"**👤 {post['recrutador']}** • *{post['cargo_info']}* • 🕒 {post['tempo']}")
            st.write(post['conteudo'])
            
            match_val = calcular_match(texto_curriculo, post['requisitos'])
            
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"🏢 **Empresa:** {post['empresa']} | 🎯 **Cargo:** {post['cargo']} | ⭐ **Match:** {match_val}%")
            with col_b:
                st.link_button("🔗 Aceder à vaga", post['link'])

# --- ABA 2: VAGAS DE MERCADO (BH & REMOTO) ---
with tab2:
    st.subheader("💼 Vagas Ativas no Mercado (Belo Horizonte & Remoto)")
    
    vagas_mercado = [
        {"empresa": "BHS Soluções Digitais", "cargo": "Database Administrator Pleno", "local": "Belo Horizonte, MG (Híbrido)", "tipo": "Remoto/Presencial", "link": "https://www.linkedin.com"},
        {"empresa": "Localiza & Co", "cargo": "Engenheiro de Dados Sénior", "local": "Belo Horizonte, MG", "tipo": "Híbrido", "link": "https://www.linkedin.com"},
        {"empresa": "Totvs", "cargo": "Analista de Banco de Dados SQL", "local": "Remoto", "tipo": "100% Remoto", "link": "https://www.linkedin.com"}
    ]
    
    for v in vagas_mercado:
        with st.container(border=True):
            st.markdown(f"### 🏢 {v['empresa']}")
            st.write(f"**Cargo:** {v['cargo']} | 📍 **Local:** {v['local']} | 💻 **Modelo:** {v['tipo']}")
            st.link_button("Ver Oportunidade", v['link'])

# --- ABA 3: REGISTAR CANDIDATURA ---
with tab3:
    st.subheader("📝 Registar Nova Candidatura")
    
    with st.form("form_candidatura"):
        col1, col2 = st.columns(2)
        with col1:
            empresa = st.text_input("Nome da Empresa")
            cargo = st.text_input("Cargo Pretendido")
        with col2:
            status = st.selectbox("Status da Candidatura", ["Enviado", "Em Entrevista", "Proposta Recebida", "Rejeitado"])
            data_cand = st.date_input("Data da Candidatura")
            
        obs = st.text_area("Observações / Notas")
        submitted = st.form_submit_button("Guardar Candidatura")
        
        if submitted:
            if empresa and cargo:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO candidaturas (empresa, cargo, status, data, observacoes) VALUES (?, ?, ?, ?, ?)",
                               (empresa, cargo, status, str(data_cand), obs))
                conn.commit()
                conn.close()
                st.success(f"Candidatura para {empresa} guardada com sucesso!")
            else:
                st.warning("Por favor, preencha pelo menos a empresa e o cargo.")

# --- ABA 4: HISTÓRICO & RELATÓRIOS ---
with tab4:
    st.subheader("📊 Histórico de Candidaturas")
    
    conn = sqlite3.connect(DB_NAME)
    df_cand = pd.read_sql_query("SELECT * FROM candidaturas", conn)
    conn.close()
    
    if not df_cand.empty:
        st.dataframe(df_cand, use_container_width=True)
        total = len(df_cand)
        st.metric("Total de Candidaturas Registadas", total)
    else:
        st.info("Ainda não existem candidaturas registadas. Utilize a aba anterior para começar.")