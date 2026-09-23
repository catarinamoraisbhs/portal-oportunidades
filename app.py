import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
from pypdf import PdfReader

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Portal de Oportunidades: Multi-Perfil",
    page_icon="🎯",
    layout="wide"
)

DB_NAME = "portal_oportunidades_v8.db"

# --- 2. FUNÇÕES DE SEGURANÇA (BCRYPT) E BASE DE DADOS ---
def make_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_hash(password, hashed_text):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_text.encode('utf-8'))

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidaturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            empresa TEXT,
            cargo TEXT,
            status TEXT,
            data TEXT,
            observacoes TEXT
        )
    ''')
    
    cursor.execute("PRAGMA table_info(candidaturas)")
    colunas = [col[1] for col in cursor.fetchall()]
    if "username" not in colunas:
        cursor.execute("ALTER TABLE candidaturas ADD COLUMN username TEXT")
    
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
    st.markdown("<p style='text-align: center; color: #888;'>Painel Restrito de Gestão de Carreira Multi-Perfil (Dev, Suporte, DBA, SysAdmin)</p>", unsafe_allow_html=True)
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

# --- 4. FUNÇÕES DE SUPORTE (PDF E MATCH MULTI-PERFIL DINÂMICO) ---
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

def calcular_match_dinamico(texto_curriculo, requisitos_vaga):
    if not texto_curriculo:
        return 0, []
    
    texto_curriculo_lower = texto_curriculo.lower()
    
    universo_skills = [
        "sql", "python", "dba", "etl", "aws", "azure", "postgres", "mysql", "oracle", 
        "power bi", "pandas", "git", "linux", "docker", "modelagem de dados", "powerdesigner",
        "javascript", "react", "node", "java", "spring", "c#", ".net", "suporte", "helpdesk",
        "redes", "incidentes", "itil", "scrum", "agile", "kubernetes", "terraform", "ci/cd"
    ]
    
    encontradas = [p for p in universo_skills if p in texto_curriculo_lower and p in requisitos_vaga.lower()]
    
    if encontradas:
        match_base = 45 + (len(encontradas) * 12)
        return min(match_base, 98), encontradas
    else:
        return 35, []

currículo_padrao_inicial = """
Candidato - Perfil Tecnológico Multi-Área
Competências: SQL, Python, Suporte Técnico, Redes, Gestão de Incidentes, Git, Linux, Metodologias Ágeis.
Formação em Tecnologia da Informação / Ciência da Computação.
"""

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()
cursor.execute("SELECT curriculo_texto FROM usuarios WHERE username = ?", (st.session_state["username"],))
res_cv = cursor.fetchone()

if res_cv and (not res_cv[0] or res_cv[0].strip() == ""):
    cursor.execute("UPDATE usuarios SET curriculo_texto = ? WHERE username = ?", (currículo_padrao_inicial, st.session_state["username"]))
    conn.commit()
    res_cv = (currículo_padrao_inicial,)

conn.close()
texto_curriculo_salvo = res_cv[0] if res_cv else ""

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.markdown(f"👤 **Utilizador:** `{st.session_state['username']}`")
    st.markdown("---")
    st.markdown("## 📄 Gestão de Currículo PDF")
    
    if texto_curriculo_salvo:
        st.success("✅ Currículo ativo no perfil!")
    else:
        st.warning("⚠️ Nenhum currículo carregado.")
    
    with st.form("form_upload_cv_unico"):
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
st.title("🎯 Portal de Oportunidades: Vagas & Feed Multi-Perfil")
st.markdown("Monitorização inteligente de oportunidades adaptada automaticamente ao perfil técnico carregado (Dev, Suporte, DBA, Infra).")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📢 Posts do Feed (LinkedIn)", 
    "💼 Vagas de Mercado (BH & Remoto)", 
    "📝 Registar Candidatura", 
    "📊 Histórico & Relatórios",
    "⚙️ Gestão de Utilizadores"
])

# Oportunidades mapeadas com base exata na estrutura visual e publicações reais do LinkedIn
lista_oportunidades = [
    {
        "tipo_origem": "Feed LinkedIn",
        "recrutador": "Tales Augusto",
        "cargo_info": "Gerente de Desenvolvimento de Sistemas | Tech Manager | Lead",
        "tempo": "2 m",
        "conteudo": "Vaga Home Office: Especialista Oracle Database (DBA Oracle) – Certsys",
        "empresa": "Certsys",
        "cargo": "Especialista Oracle Database (DBA Oracle)",
        "local": "100% Remoto (Home Office)",
        "requisitos": "sql dba oracle postgresql pl/sql",
        "link": "https://www.linkedin.com/feed/"
    },
    {
        "tipo_origem": "Feed LinkedIn",
        "recrutador": "Anderson R.",
        "cargo_info": "Coordenador de Dados | Gestão de Dados | Power BI",
        "tempo": "7 h",
        "conteudo": "Novas oportunidades abertas na Certsys para posições de Administração de Banco de Dados e Engenharia de Dados.",
        "empresa": "Certsys",
        "cargo": "Administrador Banco de Dados (DBA)",
        "local": "Recife, PE / Remoto",
        "requisitos": "sql dba postgresql oracle aws python",
        "link": "https://www.linkedin.com/feed/"
    },
    {
        "tipo_origem": "Feed LinkedIn",
        "recrutador": "André Degaut",
        "cargo_info": "Administrador de dados na empresa Certsys",
        "tempo": "1 d",
        "conteudo": "Partilhando alerta de vaga em equipa de dados e infraestrutura corporativa.",
        "empresa": "Certsys",
        "cargo": "Administrador de Dados Pleno",
        "local": "Brasília e Região",
        "requisitos": "sql dba modelagem de dados powerdesigner",
        "link": "https://www.linkedin.com/feed/"
    },
    {
        "tipo_origem": "Vaga de Mercado",
        "recrutador": "BHS Soluções Digitais",
        "cargo_info": "Empresa de Tecnologia",
        "tempo": "Ativo",
        "conteudo": "Oportunidade para Desenvolvedor Fullstack / Back-end com foco em APIs REST, Python, C# ou .Net.",
        "empresa": "BHS Soluções Digitais",
        "cargo": "Desenvolvedor Software Pleno",
        "local": "Belo Horizonte, MG (Híbrido)",
        "requisitos": "python c# .net git docker ci/cd api",
        "link": "https://www.linkedin.com/jobs/"
    },
    {
        "tipo_origem": "Vaga de Mercado",
        "recrutador": "Localiza & Co",
        "cargo_info": "Grandes Corporações",
        "tempo": "Ativo",
        "conteudo": "Desenvolvimento de pipelines de dados, engenharia analítica e arquitetura moderna na nuvem (AWS/Azure).",
        "empresa": "Localiza & Co",
        "cargo": "Engenheiro de Dados Sénior",
        "local": "Belo Horizonte, MG",
        "requisitos": "python etl aws pandas sql azure",
        "link": "https://www.linkedin.com/jobs/"
    }
]

for op in lista_oportunidades:
    match_val, keywords = calcular_match_dinamico(texto_curriculo_salvo, op["requisitos"])
    op["match_val"] = match_val
    op["keywords"] = keywords

lista_oportunidades_ordenadas = sorted(lista_oportunidades, key=lambda x: x["match_val"], reverse=True)

# --- ABA 1: POSTS DO FEED (LINKEDIN) ---
with tab1:
    st.subheader("👥 Publicações de Recrutadores e Conexões no Feed")
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
                st.caption(f"💡 **Competências identificadas no seu perfil:** {', '.join([k.upper() for k in post['keywords']])}")
            else:
                st.caption("💡 *Nenhuma competência direta cruzada com este anúncio específico.*")
            
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"🏢 **Empresa:** {post['empresa']} | 🎯 **Cargo:** {post['cargo']}")
            with col_b:
                st.link_button("🔗 Ver Publicação no LinkedIn", post['link'])

# --- ABA 2: VAGAS DE MERCADO ---
with tab2:
    st.subheader("💼 Vagas de Mercado Ativas")
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
                st.caption(f"💡 **Competências identificadas no seu perfil:** {', '.join([k.upper() for k in v['keywords']])}")
            else:
                st.caption("💡 *Nenhuma competência direta cruzada com este anúncio específico.*")
            st.link_button("Ver Oportunidade", v['link'])

# --- ABA 3: REGISTAR CANDIDATURA ---
with tab3:
    st.subheader("📝 Registar Nova Candidatura")
    with st.form("form_candidatura_nova"):
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
                cursor.execute("INSERT INTO candidaturas (username, empresa, cargo, status, data, observacoes) VALUES (?, ?, ?, ?, ?, ?)",
                               (st.session_state["username"], empresa, cargo, status, str(data_cand), obs))
                conn.commit()
                conn.close()
                st.success(f"Candidatura para {empresa} guardada com sucesso!")
            else:
                st.warning("Por favor, preencha pelo menos a empresa e o cargo.")

# --- ABA 4: HISTÓRICO & RELATÓRIOS ---
with tab4:
    st.subheader("📊 Histórico de Candidaturas")
    conn = sqlite3.connect(DB_NAME)
    df_cand = pd.read_sql_query("SELECT empresa, cargo, status, data, observacoes FROM candidaturas WHERE username = ?", 
                                conn, params=(st.session_state["username"],))
    conn.close()
    
    if not df_cand.empty:
        st.dataframe(df_cand, use_container_width=True)
        st.metric("Total das suas Candidaturas Registadas", len(df_cand))
    else:
        st.info("Ainda não existem candidaturas registadas para a sua conta.")

# --- ABA 5: GESTÃO DE UTILIZADORES ---
with tab5:
    st.subheader("⚙️ Criar Novo Utilizador")
    with st.form("form_new_user_novo"):
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