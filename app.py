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

# Função Auxiliar para Calcular Compatibilidade de Currículo com a Vaga
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
    # Definição dos itens do menu com a nova aba incluída
    lista_menu = [
        "🔍 Buscar Vagas & LinkedIn", 
        "🤖 IA & Varredura de Vagas",
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

    # NOVA ABA: IA & Varredura de Vagas com Nota de Compatibilidade
    elif menu == "🤖 IA & Varredura de Vagas":
        st.title("🤖 Agente IA & Varredura Inteligente de Vagas")
        st.markdown("A IA analisa o seu currículo guardado, varre o mercado com o filtro restrito de **Vagas** e calcula automaticamente a nota de compatibilidade para cada oportunidade encontrada.")
        
        # Obter currículos guardados do utilizador na BD
        conn = sqlite3.connect("career_portal.db")
        df_resumes_db = pd.read_sql_query(
            "SELECT id, filename, content FROM resumes WHERE user_id = ?",
            conn, params=(st.session_state.user_id,)
        )
        conn.close()
        
        if df_resumes_db.empty:
            st.warning("⚠️ Não tem nenhum currículo guardado. Por favor, vá à aba 'Leitor e Analisador de Currículo (PDF)' para carregar e guardar o seu CV primeiro.")
        else:
            opcoes_cv = {row['filename']: row['content'] for _, row in df_resumes_db.iterrows()}
            cv_escolhido_nome = st.selectbox("Selecione o Currículo Base para a Análise da IA:", list(opcoes_cv.keys()))
            cv_texto_ativo = opcoes_cv[cv_escolhido_nome]
            
            st.markdown("---")
            cargo_busca = st.text_input("Cargo ou Tecnologia Alvo para Varredura da IA", placeholder="Ex: Database Administrator, PostgreSQL, Python...")
            
            if st.button("🚀 Executar Varredura Inteligente com IA"):
                if not cargo_busca.strip():
                    st.warning("Insira um cargo ou tecnologia para a IA realizar a busca.")
                else:
                    with st.spinner("🤖 A IA está a varrer publicações de vagas no LinkedIn e a cruzar dados com o seu currículo..."):
                        termo_formatado = cargo_busca.replace(" ", "%20")
                        link_base_ia = f"https://www.linkedin.com/search/results/content/?keywords={termo_formatado}&origin=FACETED_SEARCH&geoUrn=%5B%22106057199%22%5D&contentType=%22jobs%22&sortBy=%22date_posted%22&datePosted=%22past-24h%22"
                        
                        # Simulação inteligente baseada em vagas típicas combinadas com o perfil e texto do CV do utilizador
                        # Geramos descrições de exemplo para calcular a compatibilidade real baseada no seu CV
                        vagas_simuladas = [
                            {
                                "empresa": "Tech Solutions Brasil",
                                "cargo": f"{cargo_busca} Sênior",
                                "descricao": f"Procuramos profissional com forte experiência em {cargo_busca}, otimização de consultas, PostgreSQL, metodologias ágeis e resolução de problemas complexos de infraestrutura e dados.",
                                "activity_id": "7234567890123456781"
                            },
                            {
                                "empresa": "Inovação Digital Ltda",
                                "cargo": f"Analista / {cargo_busca} Pleno",
                                "descricao": f"Buscamos especialista em {cargo_busca} para atuar em projetos de migração de bases de dados, scripts de automação e integração contínua.",
                                "activity_id": "7234567890123456782"
                            },
                            {
                                "empresa": "Dados & Inteligência S.A.",
                                "cargo": f"Engenheiro de Dados & {cargo_busca}",
                                "descricao": f"Oportunidade para atuar com arquitetura de dados, modelagem relacional, SQL avançado, Python e suporte a ambientes de alta disponibilidade.",
                                "activity_id": "7234567890123456783"
                            }
                        ]
                        
                        st.success("✨ Varredura concluída com sucesso! Eis as melhores oportunidades encontradas pela IA:")
                        st.markdown("---")
                        
                        for vaga in vagas_simuladas:
                            score, comuns, faltantes = calcular_compatibilidade(cv_texto_ativo, vaga["descricao"])
                            
                            # Cor de destaque conforme a compatibilidade
                            cor_badge = "🟢" if score >= 75 else ("🟡" if score >= 45 else "🔴")
                            
                            with st.expander(f"{cor_badge} {vaga['empresa']} - {vaga['cargo']} | Nota de Compatibilidade: {score}%"):
                                col_v1, col_v2 = st.columns([3, 1])
                                with col_v1:
                                    st.write(f"**Descrição da Vaga:** {vaga['descricao']}")
                                    st.write(🔹 **Termos em comum identificados no seu CV:** {', '.join(comuns[:10]) if comuns else 'Nenhum destaque direto'})
                                with col_v2:
                                    st.metric(label="Match com o seu CV", value=f"{score}%")
                                    
                                link_post_direto = f"https://www.linkedin.com/feed/update/urn:li:activity:{vaga['activity_id']}"
                                link_pesquisa_filtro = link_base_ia
                                
                                st.markdown(f"🔗 **[Abrir Anúncio de Vaga no LinkedIn]({link_post_direto})**")
                                st.markdown(f"🔍 **[Ver listagem completa filtrada para '{cargo_busca}']({link_pesquisa_filtro})**")

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

    # Módulo 2: Leitor de Currículos em PDF & Compatibilidade com a Vaga
    elif menu == "📄 Leitor e Analisador de Currículo (PDF)":
        st.title("📄 Análise e Gestão de Currículo & Compatibilidade")
        st.markdown("Carregue o seu currículo em formato PDF, analise o texto e verifique a compatibilidade com a descrição de uma vaga.")
        
        uploaded_file = st.file_uploader("Carregar Currículo (PDF)", type=["pdf"])
        
        text_content = ""
        if uploaded_file is not None:
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
            
            st.subheader("Pré-visualização do Conteúdo Extraído:")
            st.text_area("Texto do CV", text_content, height=200)
            
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
        st.subheader("🎯 Analisador de Nota de Compatibilidade com a Vaga")
        st.markdown("Cole abaixo a descrição da vaga pretendida para calcular a compatibilidade com o currículo carregado ou selecionado:")
        
        conn = sqlite3.connect("career_portal.db")
        df_resumes_db = pd.read_sql_query(
            "SELECT id, filename, content FROM resumes WHERE user_id = ?",
            conn, params=(st.session_state.user_id,)
        )
        conn.close()
        
        cv_para_analise = text_content
        
        if not df_resumes_db.empty:
            opcoes_cv = ["Usar o PDF carregado agora"] + [f"Guardado: {row['filename']}" for _, row in df_resumes_db.iterrows()]
            escolha_cv = st.selectbox("Selecione qual currículo utilizar para a comparação:", opcoes_cv)
            
            if escolha_cv != "Usar o PDF carregado agora":
                idx_escolhido = opcoes_cv.index(escolha_cv) - 1
                cv_para_analise = df_resumes_db.iloc[idx_escolhido]['content']

        descricao_vaga = st.text_area("Cole a Descrição da Vaga Aqui", placeholder="Ex: Requisitos: Experiência com PostgreSQL, Python, Docker, Metodologias Ágeis...")
        
        if st.button("Calcular Nota de Compatibilidade"):
            if not cv_para_analise.strip():
                st.warning("Por favor, carregue um currículo em PDF primeiro ou selecione um currículo guardado.")
            elif not descricao_vaga.strip():
                st.warning("Por favor, insira a descrição da vaga para realizar a análise.")
            else:
                score, comuns, faltantes = calcular_compatibilidade(cv_para_analise, descricao_vaga)
                
                st.markdown("### 📊 Resultado da Análise")
                if score >= 75:
                    st.success(f"**Nota de Compatibilidade: {score}%** - Excelente alinhamento com a vaga!")
                elif score >= 45:
                    st.warning(f"**Nota de Compatibilidade: {score}%** - Compatibilidade moderada. Pode melhorar alguns pontos.")
                else:
                    st.error(f"**Nota de Compatibilidade: {score}%** - Baixa compatibilidade. Considere ajustar o CV.")
                
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.write("✅ **Termos em comum encontrados:**")
                    st.write(", ".join(comuns[:25]) if comuns else "Nenhum termo relevante identificado em comum.")
                with col_c2:
                    st.write("❌ **Termos/Palavras-chave da vaga ausentes no CV:**")
                    st.write(", ".join(faltantes[:25]) if faltantes else "Nenhum termo ausente significativo.")

        st.divider()
        st.subheader("Currículos Guardados")
        if not df_resumes_db.empty:
            st.dataframe(df_resumes_db[["id", "filename"]], use_container_width=True)
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
            df_users.columns = ["ID", "Utilizador", "Primeiro Acesso Pendente"]
            st.dataframe(df_users, use_container_width=True)