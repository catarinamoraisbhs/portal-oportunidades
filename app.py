import sqlite3
import streamlit as st
import pandas as pd
from pypdf import PdfReader
import bcrypt

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
    
    # Tabela de Utilizadores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    
    # Tabela de Candidaturas e Posts do LinkedIn
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
    
    # Tabela de Currículos
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
    
    # Criar utilizador padrão 'catarina' com senha 'admin123' se não existir
    cursor.execute("SELECT id FROM users WHERE username = 'catarina'")
    if not cursor.fetchone():
        hashed_default = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('catarina', hashed_default))
        conn.commit()
        
    conn.close()

init_db()

# Funções de Autenticação Segura com bcrypt
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def login_user(username, password):
    conn = sqlite3.connect("career_portal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user and check_password(password, user[1]):
        return user[0]
    return None

def update_password(user_id, new_password):
    conn = sqlite3.connect("career_portal.db")
    cursor = conn.cursor()
    hashed = hash_password(new_password)
    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
    conn.commit()
    conn.close()

# Gestão de Sessão
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = ""

# Ecrã de Autenticação (Login)
if st.session_state.user_id is None:
    st.title("💼 Portal de Gestão de Carreira")
    st.subheader("Faça login para aceder às suas candidaturas e currículos.")
    
    st.markdown("### Aceder à Conta")
    login_user_input = st.text_input("Utilizador", key="login_user")
    login_pass_input = st.text_input("Palavra-passe", type="password", key="login_pass")
    
    if st.button("Entrar"):
        uid = login_user(login_user_input, login_pass_input)
        if uid:
            st.session_state.user_id = uid
            st.session_state.username = login_user_input
            st.success("Login efetuado com sucesso!")
            st.rerun()
        else:
            st.error("Utilizador ou palavra-passe incorretos.")

else:
    # Barra Lateral de Navegação
    st.sidebar.title(f"Olá, {st.session_state.username}!")
    menu = st.sidebar.radio("Navegação", [
        "🔍 Buscar Vagas & LinkedIn", 
        "🎯 Gestão de Candidaturas", 
        "📄 Leitor e Analisador de Currículo (PDF)", 
        "🔒 Segurança (Alterar Palavra-passe)"
    ])
    
    if st.sidebar.button("Terminar Sessão"):
        st.session_state.user_id = None
        st.session_state.username = ""
        st.rerun()
        
    # Módulo de Busca com Filtros Avançados
    if menu == "🔍 Buscar Vagas & LinkedIn":
        st.title("🔍 Pesquisa Avançada de Vagas no LinkedIn")
        st.markdown("Filtre as melhores oportunidades por tipo de origem e recência (últimas 24 horas).")
        
        with st.form("form_busca_avancada"):
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                termo_pesquisa = st.text_input("Cargo ou Palavra-chave", placeholder="Ex: DBA, Engenharia de Dados...")
            with col_b2:
                tipo_vaga = st.selectbox("Origem das Vagas", ["Publicações de Pessoas (Feed)", "Aba de Vagas Oficiais (Jobs)"])
                
            filtro_24h = st.checkbox("Filtrar apenas vagas publicadas nas últimas 24 horas")
            
            btn_pesquisar = st.form_submit_button("Gerar Link de Pesquisa Direta")
            
            if btn_pesquisar and termo_pesquisa:
                termo_formatado = termo_pesquisa.replace(" ", "%20")
                
                # Construção dos filtros URL do LinkedIn
                if tipo_vaga == "Publicações de Pessoas (Feed)":
                    # datePosted="r86400" filtra as últimas 24 horas no conteúdo/feed
                    base_url = f"https://www.linkedin.com/search/results/content/?keywords={termo_formatado}"
                    if filtro_24h:
                        base_url += "&datePosted=%22r86400%22"
                    st.success(f"Link gerado para publicações de pessoas sobre: **{termo_pesquisa}**")
                else:
                    # Aba de Vagas (Jobs) com filtro opcional de 24h (f_TPR=r86400)
                    base_url = f"https://www.linkedin.com/jobs/search/?keywords={termo_formatado}"
                    if filtro_24h:
                        base_url += "&f_TPR=r86400"
                    st.success(f"Link gerado para a Aba de Vagas Oficiais sobre: **{termo_pesquisa}**")
                    
                st.markdown(f"🔗 [Clique aqui para abrir os resultados no LinkedIn]({base_url})", unsafe_allow_html=True)
            elif btn_pesquisar:
                st.warning("Por favor, insira uma palavra-chave para pesquisar.")
            
        st.divider()
        st.subheader("Acesso Direto por ID de Publicação (Activity URN)")
        st.markdown("Se tem o ID numérico de um post específico do LinkedIn, insira-o abaixo para aceder instantaneamente:")
        
        col_id1, col_id2 = st.columns([2, 1])
        with col_id1:
            input_activity_id = st.text_input("ID do Post do LinkedIn (ex: 7123456789012345678)")
        with col_id2:
            st.markdown("<br>", unsafe_allow_html=True)
            btn_abrir_post = st.button("Abrir Publicação")
            
        if btn_abrir_post and input_activity_id:
            link_direto = f"https://www.linkedin.com/feed/update/urn:li:activity:{input_activity_id.strip()}"
            st.markdown(f"🚀 **[Aceder diretamente ao Post da Vaga]({link_direto})**", unsafe_allow_html=True)
        elif btn_abrir_post:
            st.warning("Insira um ID de post válido.")

    # Módulo 1: Gestão de Candidaturas
    elif menu == "🎯 Gestão de Candidaturas":
        st.title("🎯 Gestão de Candidaturas e Redes")
        st.markdown("Registe as suas oportunidades profissionais e acompanhe os seus processos seletivos.")
        
        with st.form("form_candidatura"):
            col1, col2 = st.columns(2)
            with col1:
                empresa = st.text_input("Empresa")
                cargo = st.text_input("Cargo Pretendido")
            with col2:
                status = st.selectbox("Estado", ["Em Análise", "Entrevista", "Proposta", "Rejeitado"])
                linkedin_id = st.text_input("ID do Post do LinkedIn (Activity ID)")
            
            notas = st.text_area("Notas / Observações")
            submit_cand = st.form_submit_button("Guardar Candidatura")
            
            if submit_cand and empresa and cargo:
                conn = sqlite3.connect("career_portal.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO applications (user_id, company, role, status, linkedin_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (st.session_state.user_id, empresa, cargo, status, linkedin_id, notas))
                conn.commit()
                conn.close()
                st.success("Candidatura guardada com sucesso!")
        
        st.divider()
        st.subheader("As Suas Candidaturas Registadas")
        
        conn = sqlite3.connect("career_portal.db")
        df_apps = pd.read_sql_query(
            "SELECT id, company, role, status, linkedin_id, notes FROM applications WHERE user_id = ?",
            conn, params=(st.session_state.user_id,)
        )
        conn.close()
        
        if not df_apps.empty:
            for index, row in df_apps.iterrows():
                with st.expander(f"{row['company']} - {row['role']} ({row['status']})"):
                    st.write(f"**Notas:** {row['notes']}")
                    if row['linkedin_id']:
                        link_post = f"https://www.linkedin.com/feed/update/urn:li:activity:{row['linkedin_id']}"
                        st.markdown(f"🔗 [Ver publicação original no LinkedIn]({link_post})")
                    else:
                        st.info("Nenhum ID de post do LinkedIn associado a esta candidatura.")
        else:
            st.info("Ainda não tem candidaturas registadas.")

    # Módulo 2: Leitor de Currículos em PDF
    elif menu == "📄 Leitor e Analisador de Currículo (PDF)":
        st.title("📄 Análise e Gestão de Currículo")
        st.markdown("Carregue o seu currículo em formato PDF para extrair o conteúdo e guardar no seu perfil.")
        
        uploaded_file = st.file_uploader("Carregar Currículo (PDF)", type=["pdf"])
        
        if uploaded_file is not None:
            reader = PdfReader(uploaded_file)
            text_content = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
            
            st.subheader("Pré-visualização do Conteúdo Extraído:")
            st.text_area("Texto do CV", text_content, height=300)
            
            if st.button("Guardar Currículo no Perfil"):
                conn = sqlite3.connect("career_portal.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO resumes (user_id, filename, content)
                    VALUES (?, ?, ?)
                """, (st.session_state.user_id, uploaded_file.name, text_content))
                conn.commit()
                conn.close()
                st.success("Currículo guardado com sucesso na base de dados!")
        
        st.divider()
        st.subheader("Currículos Guardados")
        conn = sqlite3.connect("career_portal.db")
        df_resumes = pd.read_sql_query(
            "SELECT id, filename FROM resumes WHERE user_id = ?",
            conn, params=(st.session_state.user_id,)
        )
        conn.close()
        
        if not df_resumes.empty:
            st.dataframe(df_resumes, use_container_width=True)
        else:
            st.info("Ainda não guardou nenhum currículo.")

    # Módulo 3: Segurança (Alteração de Palavra-passe)
    elif menu == "🔒 Segurança (Alterar Palavra-passe)":
        st.title("🔒 Alterar Palavra-passe")
        st.markdown("Atualize as suas credenciais de acesso à conta.")
        
        with st.form("form_pwd"):
            senha_atual = st.text_input("Palavra-passe Atual", type="password")
            nova_senha = st.text_input("Nova Palavra-passe", type="password")
            confirma_senha = st.text_input("Confirmar Nova Palavra-passe", type="password")
            
            submit_pwd = st.form_submit_button("Atualizar Palavra-passe")
            
            if submit_pwd:
                if not senha_atual or not nova_senha or not confirma_senha:
                    st.warning("Preencha todos os campos.")
                elif nova_senha != confirma_senha:
                    st.error("A nova palavra-passe e a confirmação não coincidem.")
                else:
                    conn = sqlite3.connect("career_portal.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT password FROM users WHERE id = ?", (st.session_state.user_id,))
                    db_pass = cursor.fetchone()[0]
                    conn.close()
                    
                    if check_password(senha_atual, db_pass):
                        update_password(st.session_state.user_id, nova_senha)
                        st.success("Palavra-passe alterada com sucesso!")
                    else:
                        st.error("A palavra-passe atual está incorreta.")