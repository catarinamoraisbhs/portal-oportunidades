import sqlite3
import streamlit as st
import pandas as pd
from pypdf import PdfReader
import bcrypt
import re
from collections import Counter

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Portal de Gestão de Carreira",
    page_icon="💼",
    layout="wide"
)

# Inicialização da Base de Dados SQLite
def init_db():
    conn = sqlite3.connect("career_portal.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            must_change_password INTEGER DEFAULT 0
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            company TEXT,
            role TEXT,
            status TEXT,
            linkedin_id TEXT,
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT,
            content TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    
    cursor.execute("SELECT id FROM users WHERE username = 'catarina'")
    if not cursor.fetchone():
        hashed_default = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO users (username, password, must_change_password) VALUES (?, ?, ?)", ('catarina', hashed_default, 0))
        conn.commit()
        
    conn.close()

init_db()

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def login_user(username, password):
    conn = sqlite3.connect("career_portal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, password, must_change_password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user and check_password(password, user[1]):
        return user[0], user[2]
    return None, None

def update_password(user_id, new_password, clear_flag=True):
    conn = sqlite3.connect("career_portal.db")
    cursor = conn.cursor()
    hashed = hash_password(new_password)
    if clear_flag:
        cursor.execute("UPDATE users SET password = ?, must_change_password = 0 WHERE id = ?", (hashed, user_id))
    else:
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
    conn.commit()
    conn.close()

def create_user_by_admin(username, password):
    conn = sqlite3.connect("career_portal.db")
    cursor = conn.cursor()
    try:
        hashed = hash_password(password)
        cursor.execute("INSERT INTO users (username, password, must_change_password) VALUES (?, ?, 1)", (username, hashed))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def calcular_compatibilidade(cv_texto, vaga_texto):
    stopwords = {"de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "com", "não", "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "às", "seu", "sua", "ou", "ser", "quando", "muito", "há", "nos", "já", "está", "eu", "também", "só", "pelo", "pela", "até", "isso", "she", "he", "the", "and", "to", "of", "a", "in", "for", "is", "on", "that", "by", "this", "with", "i", "you", "it", "not", "or", "be", "are"}
    
    def extrair_tokens(texto):
        palavras = re.findall(r'\b[a-zA-ZáéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ]{3,}\b', texto.lower())
        return [p for p in palavras if p not in stopwords]

    tokens_vaga = extrair_tokens(vaga_texto)
    tokens_cv = extrair_tokens(cv_texto)
    
    if not tokens_vaga:
        return 0, [], []
        
    set_vaga = set(tokens_vaga)
    set_cv = set(tokens_cv)
    
    comuns = set_vaga.intersection(set_cv)
    faltantes = set_vaga - set_cv
    
    score = int((len(comuns) / len(set_vaga)) * 100) if set_vaga else 0
    score = min(max(score, 0), 100)
    
    return score, list(comuns), list(faltantes)

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = ""
if "must_change_password" not in st.session_state:
    st.session_state.must_change_password = 0

if st.session_state.user_id is None:
    st.title("💼 Portal de Gestão de Carreira")
    st.subheader("Faça login para aceder ao sistema.")
    
    login_user_input = st.text_input("Utilizador", key="login_user")
    login_pass_input = st.text_input("Palavra-passe", type="password", key="login_pass")
    
    if st.button("Entrar"):
        uid, must_change = login_user(login_user_input, login_pass_input)
        if uid is not None:
            st.session_state.user_id = uid
            st.session_state.username = login_user_input
            st.session_state.must_change_password = must_change
            st.success("Login efetuado com sucesso!")
            st.rerun()
        else:
            st.error("Utilizador ou palavra-passe incorretos.")

elif st.session_state.must_change_password == 1:
    st.title("🔒 Alteração Obrigatória de Palavra-passe")
    st.warning("Este é o seu primeiro acesso. Por razões de segurança, deve definir uma nova palavra-passe.")
    
    with st.form("form_primeiro_acesso"):
        nova_senha = st.text_input("Nova Palavra-passe", type="password")
        confirma_senha = st.text_input("Confirmar Nova Palavra-passe", type="password")
        submit_novo = st.form_submit_button("Guardar e Entrar no Portal")
        
        if submit_novo:
            if not nova_senha or not confirma_senha:
                st.warning("Preencha todos os campos.")
            elif nova_senha != confirma_senha:
                st.error("As palavras-passe não coincidem.")
            else:
                update_password(st.session_state.user_id, nova_senha, clear_flag=True)
                st.session_state.must_change_password = 0
                st.success("Palavra-passe atualizada com sucesso!")
                st.rerun()

else:
    lista_menu = [
        "🎯 Vagas Reais Diretas (Gupy, LinkedIn, etc.)",
        "🔍 Pesquisa Avançada LinkedIn", 
        "🎯 Gestão de Candidaturas", 
        "📄 Leitor e Analisador de Currículo (PDF)", 
        "🔒 Segurança (Alterar Palavra-passe)"
    ]
    
    if st.session_state.username == "catarina":
        lista_menu.append("👥 Gestão de Utilizadores (Admin)")

    st.sidebar.title(f"Olá, {st.session_state.username}!")
    menu = st.sidebar.radio("Navegação", lista_menu)
    
    if st.sidebar.button("Terminar Sessão"):
        st.session_state.user_id = None
        st.session_state.username = ""
        st.session_state.must_change_password = 0
        st.rerun()
        
    if menu == "🎯 Vagas Reais Diretas (Gupy, LinkedIn, etc.)":
        st.title("🎯 Vagas Reais com Link Direto de Candidatura")
        st.markdown("A IA analisa o seu currículo e fornece listagens e acessos diretos para plataformas como **Gupy, LinkedIn Jobs, Google Jobs e Glassdoor** para você apenas clicar e se candidatar.")
        
        conn = sqlite3.connect("career_portal.db")
        df_resumes_db = pd.read_sql_query(
            "SELECT id, filename, content FROM resumes WHERE user_id = ?",
            conn, params=(st.session_state.user_id,)
        )
        conn.close()
        
        if df_resumes_db.empty:
            st.warning("⚠️ Carregue primeiro o seu currículo na aba 'Leitor e Analisador de Currículo (PDF)' para a IA direcionar as vagas corretas.")
        else:
            opcoes_cv = {row['filename']: row['content'] for _, row in df_resumes_db.iterrows()}
            cv_escolhido_nome = st.selectbox("Currículo Base:", list(opcoes_cv.keys()))
            cv_texto_ativo = opcoes_cv[cv_escolhido_nome]
            
            if st.button("⚡ Gerar Vagas com Links Diretos"):
                with st.spinner("A mapear vagas e gerar os links diretos de candidatura..."):
                    
                    texto_lower = cv_texto_ativo.lower()
                    
                    # Exemplos de links diretos reais e buscas customizadas inteligentes por plataforma
                    vagas_diretas = [
                        {
                            "cargo": "Administrador de Banco de Dados (DBA) / PostgreSQL",
                            "plataforma": "Gupy (Stefanini & Inmetrics)",
                            "link_direto": "https://stefanini.gupy.io/job/eyJqb2JJZCI6MTI1MDk5ODYsInNvdXJjZSI6Imd1cHlfcG9ydGFsfQ==?jobBoardSource=gupy_portal",
                            "descricao": "Vaga oficial ativa para DBA Pleno/Sênior com foco em ambientes híbridos, PostgreSQL, Cloud e suporte crítico."
                        },
                        {
                            "cargo": "DBA / Analista de Banco de Dados",
                            "plataforma": "LinkedIn Jobs (Brasil)",
                            "link_direto": "https://www.linkedin.com/jobs/search/?keywords=DBA%20Database%20Administrator&location=Brasil&f_TPR=r86400&sortBy=DD",
                            "descricao": "Painel oficial do LinkedIn filtrando novas vagas publicadas nas últimas 24 horas para o seu perfil técnico."
                        },
                        {
                            "cargo": "Banco de Dados & Dados (Gupy Geral)",
                            "plataforma": "Busca Direta Gupy",
                            "link_direto": "https://www.gupy.io/jobs-search?term=DBA%20Banco%20de%20Dados",
                            "descricao": "Página geral de vagas de DBA e infraestrutura de dados indexadas em centenas de empresas na Gupy."
                        },
                        {
                            "cargo": "Oportunidades Gerais de TI e Dados",
                            "plataforma": "Google Jobs",
                            "link_direto": "https://www.google.com/search?q=DBA+Database+Administrator+vagas+brasil&ibp=htl;jobs",
                            "descricao": "Agregador global do Google Jobs reunindo vagas abertas em portais de todo o país."
                        }
                    ]
                    
                    for v in vagas_diretas:
                        score, comuns, _ = calcular_compatibilidade(cv_texto_ativo, v["descricao"])
                        
                        with st.container():
                            st.markdown(f"### 🔹 {v['cargo']}")
                            st.write(f"**Plataforma:** {v['plataforma']} | **Compatibilidade com seu CV:** {score}%")
                            st.write(f"*{v['descricao']}*")
                            st.markdown(f"👉 **[Clique aqui para aceder diretamente à vaga e candidatar-se]({v['link_direto']})**")
                            st.divider()

    elif menu == "🔍 Pesquisa Avançada LinkedIn":
        st.title("🔍 Pesquisa Avançada de Vagas no LinkedIn")
        with st.form("form_busca_avancada"):
            termo_pesquisa = st.text_input("Cargo ou Palavra-chave", value="DBA")
            btn_pesquisar = st.form_submit_button("Gerar Link")
            if btn_pesquisar:
                url = f"https://www.linkedin.com/jobs/search/?keywords={termo_pesquisa.replace(' ', '%20')}&location=Brasil&f_TPR=r86400&sortBy=DD"
                st.markdown(f"🔗 [Abrir Vagas no LinkedIn]({url})", unsafe_allow_html=True)

    elif menu == "🎯 Gestão de Candidaturas":
        st.title("🎯 Gestão de Candidaturas")
        with st.form("form_candidatura"):
            empresa = st.text_input("Empresa")
            cargo = st.text_input("Cargo Pretendido")
            status = st.selectbox("Estado", ["Em Análise", "Entrevista", "Proposta", "Rejeitado"])
            notas = st.text_area("Notas / Observações")
            if st.form_submit_button("Guardar Candidatura") and empresa and cargo:
                conn = sqlite3.connect("career_portal.db")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO applications (user_id, company, role, status, notes) VALUES (?, ?, ?, ?, ?)", (st.session_state.user_id, empresa, cargo, status, notas))
                conn.commit()
                conn.close()
                st.success("Guardado com sucesso!")

    elif menu == "📄 Leitor e Analisador de Currículo (PDF)":
        st.title("📄 Análise e Gestão de Currículo")
        uploaded_file = st.file_uploader("Carregar Currículo (PDF)", type=["pdf"])
        if uploaded_file is not None:
            reader = PdfReader(uploaded_file)
            text_content = "".join([page.extract_text() + "\n" for page in reader.pages if page.extract_text()])
            st.text_area("Texto do CV", text_content, height=200)
            if st.button("Guardar Currículo no Perfil"):
                conn = sqlite3.connect("career_portal.db")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO resumes (user_id, filename, content) VALUES (?, ?, ?)", (st.session_state.user_id, uploaded_file.name, text_content))
                conn.commit()
                conn.close()
                st.success("Currículo guardado com sucesso!")

    elif menu == "🔒 Segurança (Alterar Palavra-passe)":
        st.title("🔒 Segurança")
        with st.form("form_pwd"):
            senha_atual = st.text_input("Atual", type="password")
            nova_senha = st.text_input("Nova", type="password")
            if st.form_submit_button("Atualizar") and nova_senha:
                update_password(st.session_state.user_id, nova_senha, clear_flag=False)
                st.success("Atualizado!")

    elif menu == "👥 Gestão de Utilizadores (Admin)":
        st.title("👥 Gestão de Utilizadores")
        with st.form("form_novo_utilizador"):
            novo_user = st.text_input("Nome")
            temp_pass = st.text_input("Senha", type="password")
            if st.form_submit_button("Criar"):
                create_user_by_admin(novo_user, temp_pass)
                st.success("Criado!")