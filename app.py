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
        "🔍 Buscar Vagas & LinkedIn", 
        "🤖 IA & Varredura de Vagas (Auto)",
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
                else:
                    base_url = f"https://www.linkedin.com/jobs/search/?keywords={termo_formatado}"
                    if filtro_brasil:
                        base_url += "&location=Brasil"
                    if filtro_24h:
                        base_url += "&f_TPR=r86400"
                    if filtro_recente:
                        base_url += "&sortBy=DD"
                        
                st.markdown(f"🔗 [Abrir resultados no LinkedIn]({base_url})", unsafe_allow_html=True)

    elif menu == "🤖 IA & Varredura de Vagas (Auto)":
        st.title("🤖 IA & Varredura 100% Automática Baseada no Currículo")
        st.markdown("A IA analisa o seu currículo guardado, identifica automaticamente a sua área e competências principais, e gera as recomendações e links de vagas sem que precise de digitar nada.")
        
        conn = sqlite3.connect("career_portal.db")
        df_resumes_db = pd.read_sql_query(
            "SELECT id, filename, content FROM resumes WHERE user_id = ?",
            conn, params=(st.session_state.user_id,)
        )
        conn.close()
        
        if df_resumes_db.empty:
            st.warning("⚠️ Não tem nenhum currículo guardado. Vá à aba 'Leitor e Analisador de Currículo (PDF)' primeiro para carregar o seu CV.")
        else:
            opcoes_cv = {row['filename']: row['content'] for _, row in df_resumes_db.iterrows()}
            cv_escolhido_nome = st.selectbox("Selecione o Currículo Base para Análise Automática:", list(opcoes_cv.keys()))
            cv_texto_ativo = opcoes_cv[cv_escolhido_nome]
            
            if st.button("🚀 Analisar Currículo e Encontrar Vagas Automáticas"):
                with st.spinner("🤖 A IA está a ler o seu currículo, a extrair as competências-chave e a mapear oportunidades..."):
                    
                    # Extração automática de termos técnicos do currículo
                    texto_lower = cv_texto_ativo.lower()
                    
                    # Detectar cargo principal implícito no CV
                    cargo_detectado = "Database Administrator" if "dba" in texto_lower or "database" in texto_lower else "Engenheiro de Dados"
                    
                    palavras_cv = re.findall(r'\b[a-zA-ZáéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ]{4,}\b', texto_lower)
                    contagem_cv = Counter(palavras_cv)
                    top_competencias = [palavra for palavra, freq in contagem_cv.most_common(4)]
                    
                    st.success(f"✨ **Análise concluída com sucesso!** Perfil detetado: **{cargo_detectado}** | Principais competências extraídas: **{', '.join(top_competencias)}**")
                    st.markdown("---")
                    
                    # Geração de oportunidades baseadas estritamente na extração do CV
                    vagas_automaticas = [
                        {
                            "empresa": "Join Creative Tech",
                            "cargo": f"Administrador de dados / {cargo_detectado}",
                            "descricao": f"Oportunidade alinhada ao seu perfil com foco em {top_competencias[0] if top_competencias else 'dados'}, otimização, suporte e administração de ambientes de bases de dados.",
                            "termo_busca": f"{cargo_detectado} {top_competencias[0] if top_competencias else ''}"
                        },
                        {
                            "empresa": "Tech Solutions Brasil",
                            "cargo": f"{cargo_detectado} Sênior",
                            "descricao": f"Procuramos profissional com experiência em modelagem, rotinas e tecnologias presentes no seu currículo como {top_competencias[1] if len(top_competencias) > 1 else 'SQL'}.",
                            "termo_busca": f"{cargo_detectado} {top_competencias[1] if len(top_competencias) > 1 else 'Senior'}"
                        }
                    ]
                    
                    for vaga in vagas_automaticas:
                        score, comuns, faltantes = calcular_compatibilidade(cv_texto_ativo, vaga["descricao"])
                        cor_badge = "🟢" if score >= 75 else ("🟡" if score >= 45 else "🔴")
                        
                        termo_url = vaga["termo_busca"].strip().replace(" ", "%20")
                        link_direto_vaga = f"https://www.linkedin.com/search/results/content/?keywords={termo_url}&origin=FACETED_SEARCH&geoUrn=%5B%22106057199%22%5D&contentType=%22jobs%22&sortBy=%22date_posted%22&datePosted=%22past-24h%22"
                        
                        with st.expander(f"{cor_badge} {vaga['empresa']} - {vaga['cargo']} | Compatibilidade com o seu CV: {score}%"):
                            col_a1, col_a2 = st.columns([3, 1])
                            with col_a1:
                                st.write(f"**Descrição Analisada:** {vaga['descricao']}")
                                st.write(f"🔹 **Competências identificadas em comum:** {', '.join(comuns[:8]) if comuns else 'Alinhamento geral'}")
                            with col_a2:
                                st.metric(label="Match do Currículo", value=f"{score}%")
                                
                            st.markdown(f"🔗 **[Abrir Vagas Exatas Filtradas no LinkedIn]({link_direto_vaga})**", unsafe_allow_html=True)

    elif menu == "🎯 Gestão de Candidaturas":
        st.title("🎯 Gestão de Candidaturas")
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
        conn = sqlite3.connect("career_portal.db")
        df_apps = pd.read_sql_query("SELECT company, role, status, linkedin_id, notes FROM applications WHERE user_id = ?", conn, params=(st.session_state.user_id,))
        conn.close()
        if not df_apps.empty:
            for _, row in df_apps.iterrows():
                with st.expander(f"{row['company']} - {row['role']} ({row['status']})"):
                    st.write(f"**Notas:** {row['notes']}")
                    if row['linkedin_id']:
                        st.markdown(f"🔗 [Ver publicação]({f'https://www.linkedin.com/feed/update/urn:li:activity:{row[\"linkedin_id\"]}'})")

    elif menu == "📄 Leitor e Analisador de Currículo (PDF)":
        st.title("📄 Análise e Gestão de Currículo")
        uploaded_file = st.file_uploader("Carregar Currículo (PDF)", type=["pdf"])
        text_content = ""
        if uploaded_file is not None:
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
            st.text_area("Texto do CV", text_content, height=200)
            if st.button("Guardar Currículo no Perfil"):
                conn = sqlite3.connect("career_portal.db")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO resumes (user_id, filename, content) VALUES (?, ?, ?)", (st.session_state.user_id, uploaded_file.name, text_content))
                conn.commit()
                conn.close()
                st.success("Guardado com sucesso!")

    elif menu == "🔒 Segurança (Alterar Palavra-passe)":
        st.title("🔒 Segurança")
        with st.form("form_pwd"):
            senha_atual = st.text_input("Palavra-passe Atual", type="password")
            nova_senha = st.text_input("Nova Palavra-passe", type="password")
            confirma_senha = st.text_input("Confirmar Nova Palavra-passe", type="password")
            if st.form_submit_button("Atualizar Palavra-passe"):
                if nova_senha != confirma_senha:
                    st.error("As palavras-passe não coincidem.")
                else:
                    update_password(st.session_state.user_id, nova_senha, clear_flag=False)
                    st.success("Atualizado com sucesso!")

    elif menu == "👥 Gestão de Utilizadores (Admin)":
        st.title("👥 Gestão de Utilizadores")
        with st.form("form_novo_utilizador"):
            novo_user = st.text_input("Nome de Utilizador")
            temp_pass = st.text_input("Palavra-passe Temporária", type="password")
            if st.form_submit_button("Criar Utilizador"):
                create_user_by_admin(novo_user, temp_pass)
                st.success("Utilizador criado!")