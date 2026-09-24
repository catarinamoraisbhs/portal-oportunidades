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
    
    # Tabela de Utilizadores com campo para forçar alteração de palavra-passe no primeiro login
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            must_change_password INTEGER DEFAULT 0
        )
    """)
    
    # Garantir compatibilidade se a tabela já existir sem a coluna nova
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
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
    
    # Criar utilizador administrador padrão 'catarina' com senha 'admin123' se não existir
    cursor.execute("SELECT id FROM users WHERE username = 'catarina'")
    if not cursor.fetchone():
        hashed_default = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO users (username, password, must_change_password) VALUES (?, ?, ?)", ('catarina', hashed_default, 0))
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
    cursor.execute("SELECT id, password, must_change_password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user and check_password(password, user[1]):
        return user[0], user[2] # Retorna ID e flag de alteração obrigatória
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

# Gestão de Sessão
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = ""
if "must_change_password" not in st.session_state:
    st.session_state.must_change_password = 0

# Ecrã de Autenticação (Login)
if st.session_state.user_id is None:
    st.title("💼 Portal de Gestão de Carreira")
    st.subheader("Faça login para aceder ao sistema.")
    
    st.markdown("### Aceder à Conta")
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

# Ecrã Obrigatório de Alteração de Palavra-passe no Primeiro Acesso
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
    # Definição dos itens do menu com base nas permissões (Apenas a 'catarina' vê a Gestão de Utilizadores)
    lista_menu = [
        "🔍 Buscar Vagas & LinkedIn", 
        "🎯 Gestão de Candidaturas", 
        "📄 Leitor e Analisador de Currículo (PDF)", 
        "🔒 Segurança (Alterar Palavra-passe)"
    ]
    
    if st.session_state.username == "catarina":
        lista_menu.append("👥 Gestão de Utilizadores (Admin)")

    # Barra Lateral de Navegação
    st.sidebar.title(f"Olá, {st.session_state.username}!")
    menu = st.sidebar.radio("Navegação", lista_menu)
    
    if st.sidebar.button("Terminar Sessão"):
        st.session_state.user_id = None
        st.session_state.username = ""
        st.session_state.must_change_password = 0
        st.rerun()
        
    # Módulo de Busca Avançada
    if menu == "🔍 Buscar Vagas & LinkedIn":
        st.title("🔍 Pesquisa Avançada de Vagas no LinkedIn")
        st.markdown("Gere links aplicando rigorosamente todos os filtros: **Publicações, Mais Recentes, Últimas 24h, Tipo de Conteúdo (Vagas) e Brasil**.")
        
        with st.form("form_busca_avancada"):
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                termo_pesquisa = st.text_input("Cargo ou Palavra-chave", placeholder="Ex: DBA, Engenharia de Dados, PostgreSQL...")
            with col_b2:
                tipo_vaga = st.selectbox("Canal de Pesquisa", ["Publicações (Feed com Filtro)", "Aba de Vagas Oficiais (Jobs)"])
                
            st.markdown("---")
            st.write("⚙️ **Filtros Ativos:**")
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                filtro_tipo_conteudo_vagas = st.checkbox("Tipo de Conteúdo: Vagas", value=True)
            with col_f2:
                filtro_recente = st.checkbox("Ordenar por 'Mais recentes'", value=True)
            with col_f3:
                filtro_24h = st.checkbox("Filtrar 'Últimas 24 horas'", value=True)
            with col_f4:
                filtro_brasil = st.checkbox("Localização: Brasil", value=True)
            
            btn_pesquisar = st.form_submit_button("Gerar Link de Pesquisa Perfeito")
            
            if btn_pesquisar and termo_pesquisa:
                termo_formatado = termo_pesquisa.replace(" ", "%20")
                
                if tipo_vaga == "Publicações (Feed com Filtro)":
                    base_url = f"https://www.linkedin.com/search/results/content/?keywords={termo_formatado}&origin=FACETED_SEARCH"
                    
                    if filtro_brasil:
                        base_url += "&geoUrn=%5B%22106057199%22%5D"
                    if filtro_tipo_conteudo_vagas:
                        base_url += "&contentType=%22jobs%22"
                    if filtro_recente:
                        base_url += "&sortBy=%22date_posted%22"
                    if filtro_24h:
                        base_url += "&datePosted=%22past-24h%22"
                        
                    st.success(f"Link gerado com o filtro exato de Tipo de Conteúdo (Vagas) para: **{termo_pesquisa}**")
                else:
                    base_url = f"https://www.linkedin.com/jobs/search/?keywords={termo_formatado}"
                    if filtro_brasil:
                        base_url += "&location=Brasil"
                    if filtro_24h:
                        base_url += "&f_TPR=r86400"
                    if filtro_recente:
                        base_url += "&sortBy=DD"
                        
                    st.success(f"Link gerado para a Aba de Vagas Oficiais sobre: **{termo_pesquisa}**")
                    
                st.markdown(f"🔗 [Clique aqui para abrir os resultados perfeitamente filtrados no LinkedIn]({base_url})", unsafe_allow_html=True)
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
                        update_password(st.session_state.user_id, nova_senha, clear_flag=False)
                        st.success("Palavra-passe alterada com sucesso!")
                    else:
                        st.error("A palavra-passe atual está incorreta.")

    # Módulo 4: Gestão de Utilizadores (Exclusivo para o Admin 'catarina')
    elif menu == "👥 Gestão de Utilizadores (Admin)":
        st.title("👥 Gestão de Utilizadores")
        st.markdown("Área restrita de administração. Registe novos utilizadores no sistema.")
        
        with st.form("form_novo_utilizador"):
            novo_user = st.text_input("Nome de Utilizador")
            temp_pass = st.text_input("Palavra-passe Temporária", type="password")
            submit_criacao = st.form_submit_button("Criar Utilizador")
            
            if submit_criacao:
                if not novo_user or not temp_pass:
                    st.warning("Preencha todos os campos para criar o utilizador.")
                else:
                    sucesso = create_user_by_admin(novo_user, temp_pass)
                    if sucesso:
                        st.success(f"Utilizador '{novo_user}' criado com sucesso! No primeiro login, será obrigatório alterar a palavra-passe.")
                    else:
                        st.error(f"O nome de utilizador '{novo_user}' já existe. Escolha outro.")
        
        st.divider()
        st.subheader("Utilizadores Registados no Sistema")
        conn = sqlite3.connect("career_portal.db")
        df_users = pd.read_sql_query("SELECT id, username, must_change_password FROM users", conn)
        conn.close()
        
        if not df_users.empty:
            # Renomear colunas para melhor visualização
            df_users.columns = ["ID", "Utilizador", "Primeiro Acesso Pendente"]
            st.dataframe(df_users, use_container_width=True)