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

DB_NAME = "portal_oportunidades_v7.db"

# --- 2. FUNÇÕES DE SEGURANÇA E BASE DE DADOS ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password, hashed_text):
    return make_hash(password) == hashed_text

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            primeiro_acesso INTEGER DEFAULT 1,
            curriculo_texto TEXT
        )
    ''')
    
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        default_user = "catarina"
        default_pass = make_hash("admin123")
        cursor.execute("INSERT INTO usuarios (username, password, primeiro_acesso) VALUES (?, ?, ?)", 
                       (default_user, default_pass, 1))
        conn.commit()
        
    conn.close()

init_db()

# --- 3. SISTEMA DE LOGIN E MUDANÇA OBRIGATÓRIA DE SENHA ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["username"] = ""
    st.session_state["mudar_senha"] = False

if not st.session_state["autenticado"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>🎯 Portal de Oportunidades</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>Painel Restrito de Gestão de Carreira (DBA / Engenharia de Dados)</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            if st.session_state.get("mudar_senha", False):
                st.markdown("### 🔑 Alterar Senha Obrigatória")
                st.info("Este é o seu primeiro acesso. Por favor, defina uma nova palavra-passe segura.")
                
                nova_senha = st.text_input("Nova Palavra-passe", type="password")
                confirma_senha = st.text_input("Confirme a Nova Palavra-passe", type="password")
                
                if st.button("Atualizar Senha e Entrar", use_container_width=True, type="primary"):
                    if nova_senha and nova_senha == confirma_senha:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET password = ?, primeiro_acesso = 0 WHERE username = ?", 
                                       (make_hash(nova_senha), st.session_state["temp_user"]))
                        conn.commit()
                        conn.close()
                        
                        st.session_state["autenticado"] = True
                        st.session_state["username"] = st.session_state["temp_user"]
                        st.session_state["mudar_senha"] = False
                        st.success("Senha alterada com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ As palavras-passe não coincidem ou estão vazias.")
            
            else:
                st.markdown("### 🔒 Acesso Restrito")
                user_input = st.text_input("Utilizador")
                senha_input = st.text_input("Palavra-passe", type="password")
                
                if st.button("Entrar no Portal", use_container_width=True, type="primary"):
                    if user_input and senha_input:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("SELECT password, primeiro_acesso FROM usuarios WHERE username = ?", (user_input,))
                        resultado = cursor.fetchone()
                        conn.close()
                        
                        if resultado and check_hash(senha_input, resultado[0]):
                            primeiro_acesso = resultado[1] if resultado[1] is not None else 0
                            if primeiro_acesso == 1:
                                st.session_state["mudar_senha"] = True
                                st.session_state["temp_user"] = user_input
                                st.rerun()
                            else:
                                st.session_state["autenticado"] = True
                                st.session_state["username"] = user_input
                                st.rerun()
                        else:
                            st.error("❌ Utilizador ou palavra-passe incorretos!")
                    else:
                        st.warning("⚠️ Por favor, preencha todos os campos.")
    
    st.stop()

# --- 4. FUNÇÕES DE SUPORTE (PDF E MATCH INTELIGENTE) ---
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
        return 0, []
    
    texto_curriculo_lower = texto_curriculo.lower()
    palavras_chave = ["sql", "python", "dba", "etl", "aws", "azure", "postgres", "mysql", "oracle", "power bi", "pandas", "git", "linux", "docker", "modelagem de dados", "powerdesigner"]
    
    encontradas = [p for p in palavras_chave if p in texto_curriculo_lower and p in requisitos_vaga.lower()]
    match_base = 50 + (len(encontradas) * 10)
    return min(match_base, 98), encontradas

# Obter o currículo guardado na base de dados para o utilizador atual
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()
cursor.execute("SELECT curriculo_texto FROM usuarios WHERE username = ?", (st.session_state["username"],))
res_cv = cursor.fetchone()
conn.close()
texto_curriculo_salvo = res_cv[0] if res_cv and res_cv[0] else ""

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.markdown(f"👤 **Utilizador:** `{st.session_state['username']}`")
    st.markdown("---")
    st.markdown("## 📄 Gestão de Currículo PDF")
    
    if texto_curriculo_salvo:
        st.success("✅ Currículo ativo no perfil!")
    else:
        st.warning("⚠️ Nenhum currículo carregado. As vagas e o feed permanecerão ocultos até efetuar o upload.")
    
    with st.form("form_upload_cv"):
        uploaded_file = st.file_uploader("Carregar / Substituir PDF", type=["pdf"])
        submitted_cv = st.form_submit_button("💾 Guardar / Atualizar Currículo", use_container_width=True)
        
        if submitted_cv:
            if uploaded_file is not None:
                novo_texto = extrair_texto_pdf(uploaded_file)
                if novo_texto.strip():
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE usuarios SET curriculo_texto = ? WHERE username = ?", (novo_texto, st.session_state["username"]))
                    conn.commit()
                    conn.close()
                    st.success("✅ Currículo atualizado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ O PDF parece estar vazio ou não foi possível extrair texto.")
            else:
                st.warning("⚠️ Selecione um ficheiro PDF primeiro.")
            
    st.markdown("---")
    if st.button("🚪 Terminar Sessão", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["username"] = ""
        st.rerun()

# --- 6. CORPO PRINCIPAL DO PORTAL ---
st.title("🎯 Portal de Oportunidades: Vagas & Feed do LinkedIn")
st.markdown("Monitorização inteligente de posts de recrutadores e vagas de mercado adaptadas automaticamente ao seu perfil profissional.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📢 Posts do Feed (LinkedIn)", 
    "💼 Vagas de Mercado (BH & Remoto)", 
    "📝 Registar Candidatura", 
    "📊 Histórico & Relatórios",
    "⚙️ Gestão de Utilizadores"
])

lista_oportunidades = [
    {
        "tipo_origem": "Feed LinkedIn",
        "recrutador": "Gabriel Wolski",
        "cargo_info": "Tech Recruiter | Recrutamento e Seleção",
        "tempo": "7 horas atrás",
        "conteudo": "Estamos com novas oportunidades na Certsys, todas as posições 100% remota! 🚀 Vaga aberta para Especialista DBA e Banco de Dados.",
        "empresa": "Certsys",
        "cargo": "Especialista DBA / Banco de Dados",
        "local": "100% Remoto",
        "requisitos": "sql dba postgresql oracle aws python",
        "link": "https://www.linkedin.com"
    },
    {
        "tipo_origem": "Feed LinkedIn",
        "recrutador": "Hilda Barbosa",
        "cargo_info": "Divulgo Vagas Como Gesto de Solidariedade",
        "tempo": "1 dia atrás",
        "conteudo": "Vaga Na Certsys - Administrador de Dados / Modelador de Dados (PowerDesigner) 🖥️ Modelo de Trabalho Híbrido / Remoto.",
        "empresa": "Certsys",
        "cargo": "Administrador de Dados / Modelador de Dados",
        "local": "Híbrido / Remoto",
        "requisitos": "modelagem de dados sql powerdesigner dba",
        "link": "https://www.linkedin.com"
    },
    {
        "tipo_origem": "Vaga de Mercado",
        "recrutador": "BHS Soluções Digitais",
        "cargo_info": "Empresa de Tecnologia",
        "tempo": "Ativo",
        "conteudo": "Procuramos profissional focado em gestão de bases de dados, otimização de queries e suporte à infraestrutura corporativa.",
        "empresa": "BHS Soluções Digitais",
        "cargo": "Database Administrator Pleno",
        "local": "Belo Horizonte, MG (Híbrido)",
        "requisitos": "sql dba mysql postgresql linux git",
        "link": "https://www.linkedin.com"
    },
    {
        "tipo_origem": "Vaga de Mercado",
        "recrutador": "Localiza & Co",
        "cargo_info": "Grandes Corporações",
        "tempo": "Ativo",
        "conteudo": "Desenvolvimento de pipelines de dados, integração de grandes volmetrias e arquitetura de dados moderna na nuvem.",
        "empresa": "Localiza & Co",
        "cargo": "Engenheiro de Dados Sénior",
        "local": "Belo Horizonte, MG",
        "requisitos": "python etl aws pandas sql azure",
        "link": "https://www.linkedin.com"
    },
    {
        "tipo_origem": "Vaga de Mercado",
        "recrutador": "Totvs",
        "cargo_info": "Software & Soluções",
        "tempo": "Ativo",
        "conteudo": "Análise, tuning e suporte a bases de dados relacionais para clientes de grande porte em ambiente corporativo.",
        "empresa": "Totvs",
        "cargo": "Analista de Banco de Dados SQL",
        "local": "Remoto",
        "requisitos": "sql dba oracle mysql",
        "link": "https://www.linkedin.com"
    }
]

# Recarregar o texto atualizado da base de dados
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()
cursor.execute("SELECT curriculo_texto FROM usuarios WHERE username = ?", (st.session_state["username"],))
res_cv = cursor.fetchone()
conn.close()
texto_atual = res_cv[0] if res_cv and res_cv[0] else ""

# Calcular o match utilizando o currículo atualizado
for op in lista_oportunidades:
    match_val, keywords = calcular_match(texto_atual, op["requisitos"])
    op["match_val"] = match_val
    op["keywords"] = keywords

lista_oportunidades_ordenadas = sorted(lista_oportunidades, key=lambda x: x["match_val"], reverse=True)

# --- ABA 1: POSTS DO FEED (LINKEDIN) ---
with tab1:
    st.subheader("👥 Publicações de Recrutadores no Feed")
    if not texto_atual:
        st.info("ℹ️ Por favor, carregue o seu currículo PDF na barra lateral para desbloquear e visualizar as oportunidades adaptadas ao seu perfil.")
    else:
        posts_feed = [op for op in lista_oportunidades_ordenadas if op["tipo_origem"] == "Feed LinkedIn"]
        
        for post in posts_feed:
            with st.container(border=True):
                col_head1, col_head2 = st.columns([4, 1])
                with col_head1:
                    st.markdown(f"**👤 {post['recrutador']}** • *{post['cargo_info']}* • 🕒 {post['tempo']}")
                with col_head2:
                    st.markdown(f"⭐ **Match: {post['match_val']}%**")
                    
                st.write(post['conteudo'])
                if post['keywords']:
                    st.caption(f"💡 **Competências identificadas no seu perfil para esta vaga:** {', '.join([k.upper() for k in post['keywords']])}")
                
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"🏢 **Empresa:** {post['empresa']} | 🎯 **Cargo:** {post['cargo']}")
                with col_b:
                    st.link_button("🔗 Aceder à vaga", post['link'])

# --- ABA 2: VAGAS DE MERCADO ---
with tab2:
    st.subheader("💼 Vagas Ativas no Mercado (Belo Horizonte & Remoto)")
    if not texto_atual:
        st.info("ℹ️ Por favor, carregue o seu currículo PDF na barra lateral para desbloquear e visualizar as vagas adaptadas ao seu perfil.")
    else:
        vagas_mercado = [op for op in lista_oportunidades_ordenadas if op["tipo_origem"] == "Vaga de Mercado"]
        
        for v in vagas_mercado:
            with st.container(border=True):
                col_v1, col_v2 = st.columns([4, 1])
                with col_v1:
                    st.markdown(f"### 🏢 {v['empresa']} - {v['cargo']}")
                with col_v2:
                    st.markdown(f"⭐ **Match: {v['match_val']}%**")
                    
                st.write(v['conteudo'])
                st.write(f"📍 **Local:** {v['local']}")
                if v['keywords']:
                    st.caption(f"💡 **Competências identificadas no seu perfil para esta vaga:** {', '.join([k.upper() for k in v['keywords']])}")
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
        st.metric("Total de Candidaturas Registadas", len(df_cand))
    else:
        st.info("Ainda não existem candidaturas registadas.")

# --- ABA 5: GESTÃO DE UTILIZADORES ---
with tab5:
    st.subheader("⚙️ Criar Novo Utilizador")
    with st.form("form_new_user"):
        novo_user = st.text_input("Nome de Utilizador (Username)")
        senha_prov = st.text_input("Palavra-passe Provisória", type="password")
        btn_criar = st.form_submit_button("Criar Utilizador")
        
        if btn_criar:
            if novo_user and senha_prov:
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO usuarios (username, password, primeiro_acesso) VALUES (?, ?, 1)",
                                   (novo_user, make_hash(senha_prov)))
                    conn.commit()
                    conn.close()
                    st.success(f"Utilizador `{novo_user}` criado com sucesso!")
                except sqlite3.IntegrityError:
                    st.error("❌ O nome de utilizador já existe.")
            else:
                st.warning("⚠️ Preencha todos os campos.")
                
    st.markdown("---")
    st.subheader("👥 Utilizadores Registados no Sistema")
    conn = sqlite3.connect(DB_NAME)
    df_users = pd.read_sql_query("SELECT id, username, primeiro_acesso FROM usuarios", conn)
    conn.close()
    st.dataframe(df_users, use_container_width=True)