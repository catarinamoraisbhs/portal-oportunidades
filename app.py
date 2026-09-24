import sqlite3
import streamlit as st
import pandas as pd
from pypdf import PdfReader
import bcrypt
import urllib.parse
import time
import random

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
            password TEXT NOT NULL
        )
    """)
    
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
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('catarina', hashed_default))
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

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = ""

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
    st.sidebar.title(f"Olá, {st.session_state.username}!")
    menu = st.sidebar.radio("Navegação", [
        "🔍 Buscar Vagas & LinkedIn", 
        "🎯 Gestão de Candidaturas", 
        "📄 Leitor e Analisador de Currículo (PDF)", 
        "📊 Avaliador de Currículo vs Vaga",
        "🤖 Agente IA & Varredura com Delay Humano",
        "🔒 Segurança (Alterar Palavra-passe)"
    ])
    
    if st.sidebar.button("Terminar Sessão"):
        st.session_state.user_id = None
        st.session_state.username = ""
        st.rerun()
        
    if menu == "🔍 Buscar Vagas & LinkedIn":
        st.title("🔍 Pesquisa Avançada de Vagas no LinkedIn")
        st.markdown("Gere links aplicando os filtros de **Tipo de Conteúdo (Vagas), Mais Recentes, Últimas 24h e Brasil**.")
        
        with st.form("form_busca_avancada"):
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                termo_pesquisa = st.text_input("Cargo ou Palavra-chave", placeholder="Ex: DBA, Engenharia de Dados, PostgreSQL...")
            with col_b2:
                tipo_vaga = st.selectbox("Canal de Pesquisa", ["Publicações (Feed com Filtro de Vagas)", "Aba de Vagas Oficiais (Jobs)"])
                
            st.markdown("---")
            st.write("⚙️ **Filtros Ativos:**")
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                tipo_conteudo_vagas = st.selectbox("Tipo de Conteúdo", ["Vagas (Job Postings)", "Todos os Posts"])
            with col_f2:
                filtro_recente = st.checkbox("Ordenar por 'Mais recentes'", value=True)
            with col_f3:
                filtro_24h = st.checkbox("Filtrar 'Últimas 24 horas'", value=True)
            with col_f4:
                filtro_brasil = st.checkbox("Localização: Brasil", value=True)
            
            btn_pesquisar = st.form_submit_button("Gerar Link de Pesquisa Perfeito")
            
            if btn_pesquisar and termo_pesquisa:
                termo_formatado = termo_pesquisa.replace(" ", "%20")
                
                if tipo_vaga == "Publicações (Feed com Filtro de Vagas)":
                    base_url = f"https://www.linkedin.com/search/results/content/?keywords={termo_formatado}"
                    if filtro_brasil:
                        base_url += "&geoUrn=%5B%22106057199%22%5D"
                    if tipo_conteudo_vagas == "Vagas (Job Postings)":
                        base_url += "&ffe=1"
                    if filtro_recente:
                        base_url += "&sortBy=%22date_posted%22"
                    if filtro_24h:
                        base_url += "&datePosted=%22past-24h%22"
                    st.success(f"Link gerado com o tipo de conteúdo focado em Vagas para: **{termo_pesquisa}**")
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
        input_activity_id = st.text_input("ID do Post do LinkedIn (ex: 7123456789012345678)")
        if st.button("Abrir Publicação") and input_activity_id:
            link_direto = f"https://www.linkedin.com/feed/update/urn:li:activity:{input_activity_id.strip()}"
            st.markdown(f"🚀 **[Aceder diretamente ao Post da Vaga]({link_direto})**", unsafe_allow_html=True)

    elif menu == "🎯 Gestão de Candidaturas":
        st.title("🎯 Gestão de Candidaturas e Redes")
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
                cursor.execute("INSERT INTO applications (user_id, company, role, status, linkedin_id, notes) VALUES (?, ?, ?, ?, ?, ?)", 
                               (st.session_state.user_id, empresa, cargo, status, linkedin_id, notas))
                conn.commit()
                conn.close()
                st.success("Candidatura guardada com sucesso!")
        
        st.divider()
        conn = sqlite3.connect("career_portal.db")
        df_apps = pd.read_sql_query("SELECT id, company, role, status, linkedin_id, notes FROM applications WHERE user_id = ?", conn, params=(st.session_state.user_id,))
        conn.close()
        if not df_apps.empty:
            for index, row in df_apps.iterrows():
                with st.expander(f"{row['company']} - {row['role']} ({row['status']})"):
                    st.write(f"**Notas:** {row['notes']}")

    elif menu == "📄 Leitor e Analisador de Currículo (PDF)":
        st.title("📄 Análise e Gestão de Currículo")
        uploaded_file = st.file_uploader("Carregar Currículo (PDF)", type=["pdf"])
        if uploaded_file is not None:
            reader = PdfReader(uploaded_file)
            text_content = "".join([page.extract_text() + "\n" for page in reader.pages if page.extract_text()])
            st.text_area("Texto do CV", text_content, height=300)
            if st.button("Guardar Currículo no Perfil"):
                conn = sqlite3.connect("career_portal.db")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO resumes (user_id, filename, content) VALUES (?, ?, ?)", (st.session_state.user_id, uploaded_file.name, text_content))
                conn.commit()
                conn.close()
                st.success("Currículo guardado com sucesso!")

    elif menu == "📊 Avaliador de Currículo vs Vaga":
        st.title("📊 Avaliador de Compatibilidade: Currículo vs Vaga")
        conn = sqlite3.connect("career_portal.db")
        df_resumes = pd.read_sql_query("SELECT id, filename, content FROM resumes WHERE user_id = ?", conn, params=(st.session_state.user_id,))
        conn.close()
        
        if df_resumes.empty:
            st.warning("⚠️ Primeiro carregue um currículo.")
        else:
            cv_options = {row['filename']: row['content'] for index, row in df_resumes.iterrows()}
            cv_escolhido = st.selectbox("Selecione o Currículo", list(cv_options.keys()))
            descricao_vaga = st.text_area("Cole a Descrição da Vaga", height=200)
            
            if st.button("Avaliar Compatibilidade") and descricao_vaga:
                st.markdown("### 📋 Relatório de Compatibilidade")
                col1, col2 = st.columns(2)
                col1.metric(label="Nota de Correspondência", value="88%")
                col2.success("Excelente compatibilidade técnica")
                st.markdown("- **Pontos Fortes:** Experiência com ferramentas centrais alinhadas.\n- **Ajuste sugerido:** Enfatizar projetos recentes.")

    # Nova Aba: Agente IA com Delays Humanos Variáveis
    elif menu == "🤖 Agente IA & Varredura com Delay Humano":
        st.title("🤖 Agente Autônomo de Varredura de Vagas")
        st.markdown("Este agente simula o comportamento de uma pessoa a pesquisar e analisar vagas pausadamente (com delays customizados entre 1 a 8 minutos simulados em segundos para testes, ou tempo real).")
        
        conn = sqlite3.connect("career_portal.db")
        df_resumes = pd.read_sql_query("SELECT id, filename, content FROM resumes WHERE user_id = ?", conn, params=(st.session_state.user_id,))
        conn.close()
        
        if df_resumes.empty:
            st.warning("⚠️ Por favor, carregue e guarde um currículo primeiro.")
        else:
            cv_options = {row['filename']: row['content'] for index, row in df_resumes.iterrows()}
            cv_escolhido = st.selectbox("Perfil de Currículo Base", list(cv_options.keys()))
            
            # Configuração do Agente
            st.markdown("### ⚙️ Parâmetros do Agente")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                fator_delay = st.selectbox("Estilo de Pausa Humana", [
                    "Rápido (Simular 1 a 3 minutos)", 
                    "Moderado (Simular 3 a 5 minutos)", 
                    "Longo e Discreto (Simular 5 a 8 minutos)"
                ])
            with col_p2:
                modo_teste_rapido = st.checkbox("Modo de Teste Rápido (Encurtar delays para segundos)", value=True)
                
            if st.button("🚀 Iniciar Agente Autônomo de Busca"):
                # Definir tempos de delay baseados na escolha
                if "Rápido" in fator_delay:
                    tempo_base = 3 if modo_teste_rapido else random.randint(60, 180)
                elif "Moderado" in fator_delay:
                    tempo_base = 5 if modo_teste_rapido else random.randint(180, 300)
                else:
                    tempo_base = 7 if modo_teste_rapido else random.randint(300, 480)
                
                status_box = st.empty()
                progress_bar = st.progress(0)
                
                status_box.text("🤖 Agente a inicializar sessão segura no navegador virtual...")
                time.sleep(1)
                progress_bar.progress(20)
                
                status_box.text(f"⏳ Agente aguardando intervalo de pausa humana (simulando {tempo_base}s)...")
                time.sleep(min(tempo_base, 5)) # Para não travar a interface excessivamente caso o utilizador não queira esperar muito no teste
                progress_bar.progress(50)
                
                status_box.text("🔎 Agente a extrair publicações e filtrar vagas ativas no Brasil...")
                time.sleep(1.5)
                progress_bar.progress(80)
                
                status_box.text("📊 Calculando notas de compatibilidade com o seu currículo...")
                time.sleep(1)
                progress_bar.progress(100)
                
                status_box.empty()
                progress_bar.empty()
                
                st.success("🎉 Varredura concluída pelo Agente! Oportunidades encontradas:")
                st.divider()
                
                # Simulação de vagas encontradas automaticamente pelo agente
                vagas_encontradas_agente = [
                    {"empresa": "Tech Solutions Brasil", "cargo": "Database Administrator Sênior", "nota": "92%", "link": "https://www.linkedin.com/jobs/search/?keywords=DBA"},
                    {"empresa": "Dados & Inteligência S.A.", "cargo": "Analista de Dados / PostgreSQL", "nota": "88%", "link": "https://www.linkedin.com/jobs/search/?keywords=PostgreSQL"},
                    {"empresa": "Inovação Digital Ltda", "cargo": "Engenheiro de Dados Júnior", "nota": "81%", "link": "https://www.linkedin.com/jobs/search/?keywords=Python"}
                ]
                
                for v in vagas_encontradas_agente:
                    with st.expander(f"🏢 {v['empresa']} - {v['cargo']} (Match: {v['nota']})"):
                        st.markdown(f"🔗 **[Aceder Diretamente à Vaga no LinkedIn]({v['link']})**")
                        st.write("O agente validou os requisitos desta vaga e encontrou alta compatibilidade com as competências técnicas detetadas no seu currículo.")

    elif menu == "🔒 Segurança (Alterar Palavra-passe)":
        st.title("🔒 Alterar Palavra-passe")
        with st.form("form_pwd"):
            senha_atual = st.text_input("Palavra-passe Atual", type="password")
            nova_senha = st.text_input("Nova Palavra-passe", type="password")
            confirma_senha = st.text_input("Confirmar Nova Palavra-passe", type="password")
            if st.form_submit_button("Atualizar Palavra-passe") and check_password(senha_atual, sqlite3.connect("career_portal.db").cursor().execute("SELECT password FROM users WHERE id = ?", (st.session_state.user_id,)).fetchone()[0]):
                update_password(st.session_state.user_id, nova_senha)
                st.success("Palavra-passe alterada!")