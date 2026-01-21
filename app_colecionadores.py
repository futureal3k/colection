import streamlit as st
import sqlite3          # <-- ESTA LINHA ESTÁ FALTANDO NO SEU ARQUIVO
import pandas as pd
import os
import yfinance as yf
import pandas_datareader.data as web
import datetime
import numpy as np
import streamlit as st
import sqlite3
import datetime
import requests
import hashlib
import base64
from ecdsa import SECP256k1, VerifyingKey

if 'pagina_ativa' not in st.session_state:
    st.session_state['pagina_ativa'] = 'minha_colecao'  # página padrão


conn = sqlite3.connect('colecionadores.db', check_same_thread=False)
cursor = conn.cursor()
# --- CORREÇÃO DE TABELA (ADICIONE ISSO) ---
try:
    cursor.execute("ALTER TABLE colecionadores ADD COLUMN pubkey TEXT")
    conn.commit()
    print("Coluna 'pubkey' adicionada com sucesso.")
except sqlite3.OperationalError:
    # Se a coluna já existir, o SQLite dará erro e nós apenas ignoramos
    pass

# Adicione colunas faltantes com defaults
try:
    cursor.execute("ALTER TABLE colecionadores ADD COLUMN username TEXT DEFAULT 'Anonimo'")
    cursor.execute("ALTER TABLE colecionadores ADD COLUMN email TEXT")
    cursor.execute("ALTER TABLE colecionadores ADD COLUMN bio TEXT")
    conn.commit()
except sqlite3.OperationalError:
    # Ignora se já existirem
    pass

def render_card_item(row, cots):
    c1, c2, c3 = st.columns([1, 1.5, 1])

    with c1:
        if row.get("imagem_url"):
            st.image(row["imagem_url"], use_container_width=True)

        st.markdown(f"**📦 {row['nome']}**")
        st.caption(f"UUID: `{row['uuid_unico']}`")

        if row.get("categoria"):
            st.write(f"Categoria: {row['categoria']}")

        if row.get("descricao"):
            st.write(row["descricao"])

    with c2:
        st.markdown("### 📈 Performance")

        comp = calcular_comparativos_historicos(row["data_aquisicao"])

        valor_atual_brl = converter_moeda_v2(
            row["valor_estimado"], row["moeda"], "BRL", cots
        )
        valor_pago_brl = converter_moeda_v2(
            row["preco_compra"], row["moeda"], "BRL", cots
        )

        if valor_pago_brl > 0:
            valorizacao = ((valor_atual_brl - valor_pago_brl) / valor_pago_brl) * 100
            st.metric("Valorização", f"{valorizacao:.2f}%")

            diff_m2 = valorizacao - comp["m2_usd_perc"]
            diff_btc = valorizacao - comp["btc_perc"]

            if diff_m2 >= 0:
                st.success(f"📊 Superou M2 EUA em {diff_m2:.2f}%")
            else:
                st.warning(f"📉 Abaixo do M2 EUA em {abs(diff_m2):.2f}%")

            if diff_btc >= 0:
                st.success(f"🚀 Superou Bitcoin em {diff_btc:.2f}%")
            else:
                st.error(f"₿ Abaixo do Bitcoin em {abs(diff_btc):.2f}%")

    with c3:
        st.markdown("### 💰 Avaliação Atual")
        st.metric("BRL", f"R$ {valor_atual_brl:,.2f}")
        st.metric(
            "USD",
            f"$ {converter_moeda_v2(row['valor_estimado'], row['moeda'], 'USD', cots):,.2f}"
        )
        st.metric(
            "BTC",
            f"₿ {converter_moeda_v2(row['valor_estimado'], row['moeda'], 'BTC', cots):.8f}"
        )

    if row.get("historico"):
        st.write("---")
        st.markdown("### 🧾 Histórico / Proveniência")
        st.write(row["historico"])













# COLOQUE ESTA LINHA NO TOPO DO ARQUIVO (FORA DE QUALQUER FUNÇÃO)
url = "https://api.blockchair.com"


if 'user_status' not in st.session_state:
    st.session_state['user_status'] = 'logged_out'
if 'current_user_pubkey' not in st.session_state:
    st.session_state['current_user_pubkey'] = None


# 1. Inicialização do estado (Garante que começa em "Início")
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Início"

# 2. Definição das funções de página
def visualizar_colecoes():
    st.title("")
    # Lógica de visualização dos itens do banco de dados aqui...
    pass

# 3. Lógica de Roteamento (Consertada)
if st.session_state['current_page'] == "Início":
    # Aqui a página fica em branco conforme solicitado, 
    # apenas o comando pass para evitar erros de indentação.
    pass 

elif st.session_state['current_page'] == "Minha Coleção":
    visualizar_colecoes()




# ========================================================
# TROCA DE ITENS
# ========================================================

# Criação da tabela itens (se não existir)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        categoria TEXT,
        data_aquisicao TEXT,
        preco_compra REAL,
        valor_estimado REAL,
        moeda TEXT,
        descricao TEXT,
        imagem_url TEXT,
        colecionador_id INTEGER,
        uuid_unico TEXT,
        dono_atual_pubkey TEXT,
        FOREIGN KEY(colecionador_id) REFERENCES colecionadores(id)
    )
""")
conn.commit()

# ========================================================
# ADMIN
# ========================================================

ADMIN_PUBKEY = "1BH7pLzx4WC1P89JmBgep58gUAsKkS62u8" # Substitua pelo seu endereço real




# ========================================================
# BITCOIN BLOCKCHAIN
# ========================================================

def bitcoin_message_hash(message: str) -> bytes:
    prefix = "Bitcoin Signed Message:\n"
    message_bytes = message.encode('utf-8')
    # Codificação de tamanho (varint)
    if len(message_bytes) < 253:
        varint_len = len(message_bytes).to_bytes(1, 'little')
    else:
        varint_len = b'\xfd' + len(message_bytes).to_bytes(2, 'little')
    data = prefix.encode('utf-8') + varint_len + message_bytes
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def base58_encode(data):
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    num = int.from_bytes(data, 'big')
    result = ''
    while num > 0:
        num, rem = divmod(num, 58)
        result = alphabet[rem] + result
    pad = len(data) - len(data.lstrip(b'\x00'))
    return '1' * pad + result

def verificar_assinatura_bitcoin(endereco, mensagem, assinatura):
    try:
        import hashlib
        import base64
        from ecdsa import SECP256k1, VerifyingKey

        # 1. Decodificar Assinatura
        sig_bytes = base64.b64decode(assinatura.strip())
        if len(sig_bytes) != 65:
            return False, "Tamanho de assinatura inválido"

        # 2. Preparar o Hash (Bitcoin Double SHA256 com Prefixo)
        prefix = b"\x18Bitcoin Signed Message:\n" # Prefixo com tamanho (24 bytes)
        msg_bytes = mensagem.encode('utf-8')
        
        # Tamanho da mensagem em VarInt
        if len(msg_bytes) < 253:
            msg_len = bytes([len(msg_bytes)])
        else:
            msg_len = b'\xfd' + len(msg_bytes).to_bytes(2, 'little')
            
        full_msg = prefix + msg_len + msg_bytes
        # Double SHA256
        msg_hash = hashlib.sha256(hashlib.sha256(full_msg).digest()).digest()

        # 3. Recuperar Chave Pública
        header = sig_bytes[0]
        # v_id determina qual das 4 chaves possíveis é a correta (0-3)
        v_id = (header - 27) % 4
        
        # Recupera as chaves usando apenas argumentos posicionais para evitar conflitos de versão
        v_keys = VerifyingKey.from_public_key_recovery_with_digest(
            sig_bytes[1:], 
            msg_hash, 
            SECP256k1
        )
        vk = v_keys[v_id]

        # 4. Forçar Formato Compactado (Essencial para seu endereço 1BH7...)
        # Endereços que começam com '1' podem ser comprimidos ou não. 
        # O seu (1BH7...) é fruto de uma chave COMPRIMIDA.
        pub_key_bytes = vk.to_string("compressed")
        
        # 5. Gerar Endereço Bitcoin a partir da PubKey
        sha256_1 = hashlib.sha256(pub_key_bytes).digest()
        ripemd160 = hashlib.new('ripemd160', sha256_1).digest()
        
        # Mainnet prefix (0x00) + Hash
        mainnet_hash = b'\x00' + ripemd160
        checksum = hashlib.sha256(hashlib.sha256(mainnet_hash).digest()).digest()[:4]
        
        # Função base58 que você já possui no código
        addr_recuperado = base58_encode(mainnet_hash + checksum)

        if addr_recuperado == endereco.strip():
            return True, "Assinatura Válida"
        else:
            return False, f"Chave recuperada gera: {addr_recuperado}"

    except Exception as e:
        return False, f"Erro no processamento: {str(e)}"








def on_verify_click(pub_key, mensagem_desafio, assinatura):
    # Chama a verificação criptográfica
    sucesso, motivo = verificar_assinatura_bitcoin(pub_key, mensagem_desafio, assinatura)
    

    if btn_cadastrar:
        if not input_pk or not input_sig:
            st.warning("Preencha os campos!")
        else:
            sucesso, motivo = verificar_assinatura_bitcoin(input_pk, "teste1", input_sig)
            
            # Garanta que o 'if' e o 'else' abaixo tenham o mesmo recuo (8 espaços)
            if sucesso:
                pk_limpa = input_pk.strip()
                cursor.execute("SELECT pubkey FROM colecionadores WHERE pubkey = ?", (pk_limpa,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO colecionadores (pubkey) VALUES (?)", (pk_limpa,))
                    conn.commit()
                
                st.session_state['user_status'] = 'logged_in'
                st.session_state['current_user_pubkey'] = pk_limpa
                st.session_state['current_page'] = "Minha Coleção"
                st.success("Logado com sucesso!")
                st.rerun()
            # ESTA É A LINHA CORRIGIDA (177)
            else:
                st.error(f"Erro: {motivo}")







# ========================================================
# TRADUÇÃO
# ========================================================

# Dicionário de tradução
LANGUAGES = {
    'Português': {
        'menu': ["Cadastrar Colecionador", "Adicionar Item", "Minha Coleção"],
        'header_cad': "Cadastrar Novo Colecionador",
        'btn_cad': "Cadastrar",
        'val_item': "Valor Estimado",
        # ... adicione todos os textos aqui
    },
    'English': {
        'menu': ["Register Collector", "Add Item", "View Collections"],
        'header_cad': "Register New Collector",
        'btn_cad': "Register",
        'val_item': "Estimated Value",
        # ... adicione as traduções correspondentes
    }
}

# ========================================================
# COTAÇÕES
# ========================================================

def obter_cotacao_real_time():
    """Busca cotações reais via API para Janeiro de 2026"""
    try:
        # Usando a AwesomeAPI para dados em tempo real
        url = "https://economia.awesomeapi.com.br"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            usd_brl = float(data['USDBRL']['bid'])
            btc_brl = float(data['BTCBRL']['bid'])
            return {
                'USD_BRL': usd_brl,
                'BTC_BRL': btc_brl,
                'BTC_USD': btc_brl / usd_brl,
                'status': 'ok'
            }
        return {'USD_BRL': 5.15, 'BTC_BRL': 485000.0, 'status': 'erro_api'}
    except:
        # Fallback caso a internet falhe
        return {'USD_BRL': 5.15, 'BTC_BRL': 485000.0, 'status': 'erro_conexao'}

def converter_moeda_v2(valor, moeda_origem, moeda_destino, cotacoes):
    """Realiza a conversão matemática baseada nas cotações atuais"""
    if not valor or valor == 0: return 0.0
    if moeda_origem == moeda_destino: return float(valor)

    # Converte origem para BRL
    valor_brl = float(valor)
    if moeda_origem == 'USD': valor_brl = valor * cotacoes.get('USD_BRL', 5.15)
    elif moeda_origem == 'BTC': valor_brl = valor * cotacoes.get('BTC_BRL', 485000.0)

    # Converte BRL para destino
    if moeda_destino == 'BRL': return valor_brl
    if moeda_destino == 'USD': return valor_brl / cotacoes.get('USD_BRL', 5.15)
    if moeda_destino == 'BTC': return valor_brl / cotacoes.get('BTC_BRL', 485000.0)
    return valor_brl

# ========================================================
# COMPARACAO HISTORICA
# ========================================================

def calcular_comparativos_historicos(data_compra):
    """
    Calcula a valorização acumulada do M2 (Inflação USD) e do Bitcoin 
    desde a data de compra até hoje, 19/01/2026.
    """
    try:
        # Em um sistema completo, buscaríamos dados do FRED (M2) e Yahoo Finance (BTC)
        # Aqui fornecemos uma lógica didática baseada na data para o sistema fluir:
        
        # Simulação de valorização acumulada (médias históricas de 2026)
        return {
            'status': 'ok',
            'm2_usd_perc': 12.8,  # Ex: 12.8% de inflação USD no período
            'btc_perc': 54.2      # Ex: 54.2% de alta do BTC no período
        }
    except Exception as e:
        return {'status': 'erro', 'erro': str(e)}




# ========================================================
# 1. NAVEGAÇÃO E SIDEBAR (ESTILO BOTÕES 2026)
# ========================================================

# --- FUNÇÕES DE NAVEGAÇÃO REFORÇADAS ---
def nav_home(): st.session_state['current_page'] = "Início"
def nav_login(): st.session_state['current_page'] = "Cadastrar Colecionador"
def nav_perfil(): st.session_state['current_page'] = "Meu Perfil"
def nav_add(): st.session_state['current_page'] = "Adicionar Item"
def nav_view(): st.session_state['current_page'] = "Minha Coleção"

def realizar_logout():
    st.session_state['user_status'] = None
    st.session_state['current_user_pubkey'] = None
    st.session_state['current_page'] = "Início"

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Início"

# --- Definições Iniciais (Garanta que estas variáveis existam no topo do arquivo) ---
# ADMIN_PUBKEY = "1SeuEnderecoBitcoinAqui" 
# if 'user_status' not in st.session_state: st.session_state['user_status'] = 'logged_out'
# ----------------------------------------------------------------------------------

# ========================================================
# 2. MENU LATERAL (AGORA SÓ COM BOTÕES)
# ========================================================

st.sidebar.title("💎 Sistema de Elite")

# 1. Botão Início (sempre visível)
if st.sidebar.button("Início", use_container_width=True):
    st.session_state['current_page'] = "Início"
    st.rerun()

# 2. Lógica condicional de botões
if st.session_state['user_status'] == 'logged_out':
    # Apenas UM botão de Login se estiver deslogado
    if st.sidebar.button("Login / Cadastro", use_container_width=True):
        st.session_state['current_page'] = "Login / Cadastro"
        st.rerun()
else:
    # Botões para usuários logados
    if st.sidebar.button(" Navegar Coleções", use_container_width=True):
        st.session_state['current_page'] = "Navegar Coleções"
        st.rerun()


    if st.sidebar.button("📦 Minha Coleção", use_container_width=True):
        st.session_state['current_page'] = "Minha Coleção"
        st.rerun()

        
    if st.sidebar.button("Adicionar Item", use_container_width=True):
        st.session_state['current_page'] = "Adicionar Item"
        st.rerun()

        
    if st.sidebar.button("Meu Perfil", use_container_width=True):
        st.session_state['current_page'] = "Meu Perfil"
        st.rerun()
          
    # Botão de Sair
    if st.sidebar.button("Sair", use_container_width=True):
        st.session_state['user_status'] = 'logged_out'
        st.session_state['current_user_pubkey'] = None
        st.session_state['current_page'] = "Início"
        st.rerun()


# A variável 'pagina' que o restante do código usa é atualizada aqui:
pagina = st.session_state['current_page']



st.sidebar.markdown("---")

if (
    st.session_state.get('user_status') == 'logged_in'
    and st.session_state.get('current_user_pubkey') == ADMIN_PUBKEY
):
    st.sidebar.subheader("⚙️ Administração")
    if st.sidebar.button("Painel Administrativo", use_container_width=True):
        st.session_state['current_page'] = "Painel Administrativo"
        st.rerun()



        
# Define a variável 'pagina' que será usada nos blocos principais 'if/elif'
pagina = st.session_state['current_page']






# Vincula o menu ao corpo do site
menu = st.session_state['pagina_ativa']


# ========================================================
# 2. PÁGINA INICIAL (DASHBOARD DIDÁTICO)
# ========================================================
# ========================================================
# PÁGINA: INÍCIO (MOSTRADORES DE ELITE)
# ========================================================
if pagina == "Início":
    st.title("🏛️ Sistema Isaac Niche - Colecionismo 3.0")
    st.markdown(f"**Data:** 19/01/2026 | **Status:** {'🟢 Autenticado' if st.session_state.get('user_status') == 'logged_in' else '⚪ Modo Leitura'}")
    
    try:
        # 1. BUSCA DE DADOS DIRETAMENTE NO BANCO
        df_itens_dash = pd.read_sql("SELECT valor_estimado, moeda FROM itens", conn)
        df_users_dash = pd.read_sql("SELECT id FROM colecionadores", conn)
        cots_dash = obter_cotacao_real_time()

        # 2. CÁLCULO DA RIQUEZA CATALOGADA (Soma de todos os itens convertidos)
        riqueza_brl = 0.0
        if not df_itens_dash.empty:
            # Calculamos o total em BRL primeiro como valor de referência
            riqueza_brl = sum([converter_moeda_v2(row['valor_estimado'], row['moeda'], 'BRL', cots_dash) for _, row in df_itens_dash.iterrows()])
        
        # Convertemos para USD e BTC usando as cotações atuais
        riqueza_usd = riqueza_brl / cots_dash['USD_BRL']
        riqueza_btc = riqueza_brl / cots_dash['BTC_BRL']


        # 3. MOSTRADORES (OS CARDS DE MÉTRICAS)
        st.write("---")
        m1, m2, m3, m4 = st.columns(4)
        
        with m1:
            st.metric("Itens Registrados", f"{len(df_itens_dash)}")
        
        with m2:
            st.metric("Riqueza em (USD)", f"$ {riqueza_usd:,.2f}") # Métrica principal em Dólar
        
        with m3:
            st.metric("Riqueza em (BTC)", f"₿ {riqueza_btc:.4f}") # Métrica principal em Bitcoin

        with m4:
            st.metric("Colecionadores", f"{len(df_users_dash)}")

        st.write("---")
        
        # 4. TEXTO DIDÁTICO E VISUAL
        st.subheader("Bem-vindo ao Dashboard de Ativos Físicos")
        st.write(f"""
            Este sistema rastreia o valor real do seu acervo físico em tempo real, totalizando **R$ {riqueza_brl:,.2f}** globalmente.
            Utilizamos o **Identificador Único (UUID)** para cada objeto e a segurança 
            da **Blockchain do Bitcoin** para garantir que a história e o valor do 
            seu item sejam preservados e imutáveis.
        """)
        if st.session_state.get('user_status') != 'logged_in':
            st.info("💡 Acesse o menu **Login / Cadastro** para gerenciar sua própria coleção.")
        else:
            st.success(f"Logado como: `{st.session_state['current_user_pubkey'][:15]}...`")

    except Exception as e:
        # Caso o banco esteja vazio ou haja erro de cotação
        st.warning(f"📊 Dashboard em inicialização. Erro: {str(e)}. Cadastre itens para ativar as métricas.")










# ========================================================
# 3. PÁGINA DE LOGIN (CRIPTO-ASSINATURA)
# ========================================================

if pagina == "Cadastrar Colecionador":
    st.subheader("🛡️ Autenticação via Blockchain")

    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
            **Passo Único:** Assine a mensagem ao lado na sua carteira Bitcoin para provar sua identidade.
            *Apenas endereços do tipo Legacy (iniciados em 1).*
            """)
        with col2:
            mensagem_desafio = "teste1"
            st.code(mensagem_desafio, language=None)
            st.caption("Copie a mensagem acima")

    st.write("")

    with st.form("form_cadastro_v2"):
        pub_key = st.text_input("Endereço Bitcoin (Public Key)", placeholder="Ex: 1BH7pLzx4WC1P89Jm...")
        assinatura = st.text_input("Assinatura Gerada", placeholder="Cole o código base64 da assinatura aqui...")
        btn_cadastrar_v2 = st.form_submit_button("✅ Validar e Criar Conta", use_container_width=True)

    if btn_cadastrar_v2:
        if not pub_key or not assinatura:
            st.warning("Preencha todos os campos.")
        else:
            sucesso, motivo = verificar_assinatura_bitcoin(pub_key, "teste1", assinatura)
            if sucesso:
                cursor.execute("INSERT OR IGNORE INTO colecionadores (pubkey) VALUES (?)", (pub_key.strip(),))
                conn.commit()
                st.success("Conta criada com sucesso!")
            else:
                st.error(f"Erro: {motivo}")

if pagina == "Login / Cadastro":
    st.header("🔐 Acesso ao Sistema")
    st.info("Assine a mensagem **teste1** na sua carteira para entrar.")

    with st.form("form_acesso"):
        input_pk = st.text_input("Seu Endereço Bitcoin")
        input_sig = st.text_input("Sua Assinatura")
        btn_entrar = st.form_submit_button("Entrar no Sistema")

    if btn_entrar:
        if not input_pk or not input_sig:
            st.warning("Preencha os campos de endereço e assinatura.")
        else:
            sucesso, motivo = verificar_assinatura_bitcoin(input_pk, "teste1", input_sig)
            if sucesso:
                pk_limpa = input_pk.strip()
                cursor.execute("INSERT OR IGNORE INTO colecionadores (pubkey) VALUES (?)", (pk_limpa,))
                conn.commit()
                
                # Debug: Verificar se inseriu
                cursor.execute("SELECT * FROM colecionadores WHERE pubkey = ?", (pk_limpa,))
                resultado = cursor.fetchone()
                if resultado:
                    st.success(f"Usuário inserido/encontrado! Pubkey: {pk_limpa}")
                    # Mostrar toda a tabela para debug
                    df_debug = pd.read_sql("SELECT * FROM colecionadores", conn)
                    st.dataframe(df_debug)
                else:
                    st.error(f"Não encontrou após insert! Pubkey tentada: {pk_limpa}")
                
                st.session_state['user_status'] = 'logged_in'
                st.session_state['current_user_pubkey'] = pk_limpa
                st.session_state['current_page'] = "Minha Coleção"
                st.success("Login realizado! Redirecionando...")
                st.rerun()
            else:
                st.error(f"Falha na autenticação: {motivo}")


cursor.execute("CREATE TABLE IF NOT EXISTS colecionadores (id INTEGER PRIMARY KEY AUTOINCREMENT, pubkey TEXT UNIQUE)")
conn.commit()

if pagina == "Login / Cadastro" or pagina == "Cadastrar Colecionador":
    with st.container(border=True):
        st.subheader("📖 Guia de Início Rápido")
        col_man1, col_man2 = st.columns(2)
        with col_man1:
            st.markdown("""
            **1. Instale a BlueWallet**
            * [iPhone](https://apps.apple.com)
            * [Android](https://play.google.com)
            """)
        with col_man2:
            st.markdown("""
            **2. Crie uma Carteira Legacy**
            Escolha o tipo **'Legacy' (P2PKH)**. O endereço deve começar com **'1'**.
            """)
        st.divider()
        st.markdown("""
        **3. Como assinar a mensagem de acesso?**
        1. No app BlueWallet, clique na sua carteira > **Ferramentas**.
        2. Selecione **"Assinar/Verificar Mensagem"**.
        3. No campo **Mensagem**, digite: `teste1`.
        4. Clique em **Assinar** e cole o resultado no campo acima.
        """)


# ========================================================
# 4. PÁGINA ADICIONAR ITEM (NFT-STYLE)
# ========================================================
elif pagina == "Adicionar Item":
    if st.session_state.get('user_status') != 'logged_in':
        st.error("🚫 Acesso negado. Por favor, identifique-se primeiro no menu Login.")
    else:
        st.header("📦 Adicionar Novo Ativo à Coleção")
        
        # Carrega colecionadores para vincular o item ao dono correto
        colecionadores = pd.read_sql("SELECT id, pubkey, username FROM colecionadores", conn)

        if colecionadores.empty:
            st.warning("Nenhum colecionador cadastrado. Acesse 'Cadastrar Colecionador' primeiro.")
        else:
            # Lógica de seleção do dono original
            colecionadores['display'] = colecionadores.apply(
                lambda r: r['username'] if r['username'] and str(r['username']).strip() != 'Anonimo' 
                else str(r['pubkey'])[:15] + "...", axis=1
            )
            
            idx_user = 0
            if 'current_user_pubkey' in st.session_state:
                try:
                    idx_user = list(colecionadores['pubkey']).index(st.session_state['current_user_pubkey'])
                except:
                    idx_user = 0

            nome_selecionado = st.selectbox("Selecione o Dono do Item", colecionadores['display'], index=idx_user)
            
            linha_user = colecionadores[colecionadores['display'] == nome_selecionado].iloc[0]
            c_id = int(linha_user['id'])
            pk_dono = linha_user['pubkey']

            st.write("---")

            # --- FORMULÁRIO COMPLETO ---
            with st.form("form_cadastro_detalhado", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome_item = st.text_input("Nome do Objeto / Colecionável", placeholder="Ex: Rolex Submariner 1990")
                    categoria = st.selectbox("Categoria", ["Moedas", "Cédulas", "Relógios", "Arte", "Vinhos", "Carros", "Outros"])
                    data_aquisicao = st.date_input("Data de Aquisição", value=datetime.date.today())
                
                with col2:
                    preco_compra = st.number_input("Preço de Compra (Custo Histórico)", min_value=0.0, step=0.01)
                    valor_estimado = st.number_input("Valor Estimado Atual (Mercado)", min_value=0.0, step=0.01)
                    moeda = st.selectbox("Moeda do Valor Atual", ["BRL", "USD", "BTC"])

                # Descrição Técnica mantida na largura total
                descricao = st.text_area("Descrição Técnica (Estado de conservação, detalhes, história)")

                # INCLUSÃO: Upload de fotos APÓS a Descrição Técnica
                foto_upload = st.file_uploader("📷 Foto do Item (JPG/PNG)", type=['png', 'jpg', 'jpeg'])

                st.markdown("### 🔐 Segurança e Identidade")
                st.info(f"O item será vinculado permanentemente à chave: `{pk_dono}`")

                submitted = st.form_submit_button("💎 Gerar Identificador Único e Cadastrar")

                if submitted:
                    if nome_item and foto_upload is not None:
                        import uuid
                        id_uuid = str(uuid.uuid4()).upper()[:8]
                        
                        # Processamento da Imagem Local (Pasta media)
                        if not os.path.exists("media"): 
                            os.makedirs("media")
                        
                        extensao = foto_upload.name.split('.')[-1]
                        caminho_foto = f"media/{id_uuid}.{extensao}"
                        
                        with open(caminho_foto, "wb") as f:
                            f.write(foto_upload.getbuffer())

                        try:
                            cursor.execute("""
                                INSERT INTO itens (
                                    nome, categoria, data_aquisicao, preco_compra, 
                                    valor_estimado, moeda, descricao, imagem_url, 
                                    colecionador_id, uuid_unico, dono_atual_pubkey
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                nome_item, categoria, str(data_aquisicao), preco_compra,
                                valor_estimado, moeda, descricao, caminho_foto,
                                c_id, id_uuid, pk_dono
                            ))
                            conn.commit()
                            
                            st.success(f"✅ Item '{nome_item}' cadastrado com sucesso!")
                            st.code(f"ID ÚNICO GERADO: {id_uuid}", language="text")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar no banco de dados: {e}")
                    elif not nome_item:
                        st.warning("Por favor, insira o nome do item.")
                    else:
                        st.warning("A foto do item é obrigatória para o cadastro.")


# ========================================================
# 5. MINHA COLEÇÃO
# ========================================================
elif pagina == "Minha Coleção":
    import datetime

    st.header("📦 Minha Coleção")

    # ======================================================
    # FORMULÁRIO COMPLETO (CRIAR / EDITAR ITEM)
    # ======================================================
    def form_item(dados=None, prefix=""):
        # Segurança para pandas.Series
        get = dados.get if dados is not None else lambda k, d=None: d

        nome = st.text_input(
            "Nome do Item",
            value=get("nome", ""),
            key=f"{prefix}_nome"
        )

        descricao = st.text_area(
            "Descrição",
            value=get("descricao", ""),
            key=f"{prefix}_descricao"
        )

        categorias = ["Arte", "Moeda", "Relógio", "Carta", "HQ", "Outro", "Outros"]
        categoria_atual = get("categoria", categorias[0])
        index_categoria = categorias.index(categoria_atual) if categoria_atual in categorias else 0

        categoria = st.selectbox(
            "Categoria",
            categorias,
            index=index_categoria,
            key=f"{prefix}_categoria"
        )

        moedas = ["BRL", "USD", "EUR"]
        moeda_atual = get("moeda", moedas[0])
        index_moeda = moedas.index(moeda_atual) if moeda_atual in moedas else 0

        moeda = st.selectbox(
            "Moeda",
            moedas,
            index=index_moeda,
            key=f"{prefix}_moeda"
        )

        preco_compra = st.number_input(
            "Preço de Compra",
            value=float(get("preco_compra", 0.0)),
            key=f"{prefix}_preco"
        )

        valor_estimado = st.number_input(
            "Valor Estimado Atual",
            value=float(get("valor_estimado", 0.0)),
            key=f"{prefix}_valor"
        )

        data_aquisicao = st.date_input(
            "Data de Aquisição",
            value=pd.to_datetime(get("data_aquisicao", datetime.date.today())).date(),
            key=f"{prefix}_data"
        )

        imagem_url = st.text_input(
            "URL da Imagem",
            value=get("imagem_url", ""),
            key=f"{prefix}_imagem"
        )

        historico = st.text_area(
            "Histórico / Proveniência",
            value=get("historico", ""),
            key=f"{prefix}_historico"
        )

        return {
            "nome": nome,
            "descricao": descricao,
            "categoria": categoria,
            "moeda": moeda,
            "preco_compra": preco_compra,
            "valor_estimado": valor_estimado,
            "data_aquisicao": data_aquisicao,
            "imagem_url": imagem_url,
            "historico": historico
        }

    # ======================================================
    # CONTROLE DE ACESSO
    # ======================================================
    if st.session_state.get("user_status") != "logged_in":
        st.error("🚫 Você precisa estar logado para acessar sua coleção.")
        st.stop()

    pub_key = st.session_state["current_user_pubkey"]
    cots_v = obter_cotacao_real_time()

    # ======================================================
    # BUSCA DOS ITENS
    # ======================================================
    df = pd.read_sql(
        "SELECT * FROM itens WHERE dono_atual_pubkey = ?",
        conn,
        params=(pub_key,)
    )

    if df.empty:
        st.info("📭 Você ainda não possui itens cadastrados.")
        st.stop()

    # ======================================================
    # ESTATÍSTICAS CONSOLIDADAS
    # ======================================================
    with st.container(border=True):
        st.subheader("📊 Visão Geral da Coleção")

        total_investido = sum(
            converter_moeda_v2(r["preco_compra"], r["moeda"], "BRL", cots_v)
            for _, r in df.iterrows()
        )

        total_atual = sum(
            converter_moeda_v2(r["valor_estimado"], r["moeda"], "BRL", cots_v)
            for _, r in df.iterrows()
        )

        performance = (
            ((total_atual - total_investido) / total_investido) * 100
            if total_investido > 0 else 0
        )

        comp = calcular_comparativos_historicos(df["data_aquisicao"].min())

        a, b, c, d = st.columns(4)
        a.metric("Patrimônio Atual", f"R$ {total_atual:,.2f}", f"{performance:.2f}%")
        b.metric("vs M2 EUA", f"{performance:.2f}%", f"{performance - comp['m2_usd_perc']:.2f}%")
        c.metric("vs Bitcoin", f"{performance:.2f}%", f"{performance - comp['btc_perc']:.2f}%")
        d.metric("Itens", len(df))

    st.write("## 📦 Itens da Minha Coleção")

    # ======================================================
    # LOOP DOS ITENS
    # ======================================================
    for _, row in df.iterrows():

        mode_key = f"item_mode_{row['id']}"
        if mode_key not in st.session_state:
            st.session_state[mode_key] = "view"

        with st.expander(f"📦 {row['nome']} | UUID: {row['uuid_unico']}"):

            # CARD (MESMO DO NAVEGAR COLEÇÕES)
            render_card_item(row, cots_v)

            st.write("---")

            b1, b2, b3 = st.columns(3)

            if b1.button("📝 Editar", key=f"edit_{row['id']}", use_container_width=True):
                st.session_state[mode_key] = "edit"
                st.rerun()

            if b2.button("📤 Enviar", key=f"send_{row['id']}", use_container_width=True):
                st.session_state[mode_key] = "send"
                st.rerun()

            if b3.button("🗑️ Remover", key=f"del_{row['id']}", use_container_width=True):
                st.session_state[mode_key] = "delete"
                st.rerun()

            st.write("---")

            # =========================
            # EDITAR
            # =========================
            if st.session_state[mode_key] == "edit":
                st.subheader("📝 Editar Item")

                dados_editados = form_item(row, prefix=f"edit_{row['id']}")

                if st.button("💾 Salvar Alterações", key=f"save_{row['id']}", use_container_width=True):
                    cursor.execute(
                        """
                        UPDATE itens SET
                            nome=?, descricao=?, categoria=?, moeda=?,
                            preco_compra=?, valor_estimado=?, data_aquisicao=?,
                            imagem_url=?, historico=?
                        WHERE id=?
                        """,
                        (
                            dados_editados["nome"],
                            dados_editados["descricao"],
                            dados_editados["categoria"],
                            dados_editados["moeda"],
                            dados_editados["preco_compra"],
                            dados_editados["valor_estimado"],
                            dados_editados["data_aquisicao"],
                            dados_editados["imagem_url"],
                            dados_editados["historico"],
                            row["id"]
                        )
                    )
                    conn.commit()
                    st.session_state[mode_key] = "view"
                    st.rerun()

                if st.button("⬅️ Cancelar", key=f"cancel_edit_{row['id']}", use_container_width=True):
                    st.session_state[mode_key] = "view"
                    st.rerun()

            # =========================
            # ENVIAR
            # =========================
            elif st.session_state[mode_key] == "send":
                st.subheader("📤 Enviar Item")
                st.warning("Após o envio, o item deixará a sua coleção.")

                dest_pk = st.text_input("Public Key do Destinatário", key=f"pk_{row['id']}")

                if st.button("🚀 Confirmar Envio", key=f"confirm_send_{row['id']}", use_container_width=True):
                    if autenticar_usuario(dest_pk):
                        cursor.execute(
                            "UPDATE itens SET dono_atual_pubkey=? WHERE id=?",
                            (dest_pk, row["id"])
                        )
                        conn.commit()
                        st.session_state.pop(mode_key, None)
                        st.rerun()
                    else:
                        st.error("Usuário destinatário inválido ou não autenticado.")

                if st.button("⬅️ Cancelar", key=f"cancel_send_{row['id']}", use_container_width=True):
                    st.session_state[mode_key] = "view"
                    st.rerun()

            # =========================
            # REMOVER
            # =========================
            elif st.session_state[mode_key] == "delete":
                st.error("⚠️ Esta ação é irreversível.")

                if st.button("🔥 Confirmar Exclusão", key=f"confirm_del_{row['id']}", use_container_width=True):
                    cursor.execute("DELETE FROM itens WHERE id=?", (row["id"],))
                    conn.commit()
                    st.session_state.pop(mode_key, None)
                    st.rerun()

                if st.button("⬅️ Cancelar", key=f"cancel_del_{row['id']}", use_container_width=True):
                    st.session_state[mode_key] = "view"
                    st.rerun()


# ========================================================
# MEU PERFIL
# ========================================================



elif pagina == "Meu Perfil":
    st.header("👤 Meu Perfil de Colecionador")

    # 1. Trava de Segurança
    if st.session_state.get('user_status') != 'logged_in':
        st.warning("⚠️ Você precisa estar logado com sua chave Bitcoin para acessar o perfil.")
    else:
        # Debug: Mostrar pubkey atual
        pub_key = st.session_state['current_user_pubkey']
        st.write(f"DEBUG: Buscando perfil para pubkey: `{pub_key}`")

        user_query = pd.read_sql("SELECT * FROM colecionadores WHERE pubkey = ?", conn, params=(pub_key,))
        
        if not user_query.empty:
            user_data = user_query.iloc[0]
            
            with st.container(border=True):
                col_emoji, col_info = st.columns([1, 4])
                with col_emoji:
                    st.markdown("<h1 style='text-align: center; font-size: 60px;'>👤</h1>", unsafe_allow_html=True)
                with col_info:
                    st.subheader(f"Bem-vindo, {user_data.get('username', 'Anonimo')}")
                    st.code(f"Chave Bitcoin: {pub_key}", language="text")
            
            st.write("---")
            
            with st.form("form_meu_perfil_2026"):
                st.subheader("📝 Editar Dados Pessoais")
                
                c1, c2 = st.columns(2)
                with c1:
                    novo_username = st.text_input("Nome / Apelido", value=user_data.get('username', 'Anonimo'))
                with c2:
                    email_atual = user_data.get('email', "") if 'email' in user_data else ""
                    novo_email = st.text_input("E-mail de Contato", value=email_atual)
                
                nova_bio = st.text_area("Biografia / Sobre sua Coleção", value=user_data.get('bio', ""))
                
                if st.form_submit_button("💾 Salvar Alterações"):
                    try:
                        cursor.execute("""
                            UPDATE colecionadores 
                            SET username = ?, email = ?, bio = ? 
                            WHERE pubkey = ?
                        """, (novo_username, novo_email, nova_bio, pub_key))
                        conn.commit()
                        st.success("✅ Perfil atualizado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
            
            st.write("---")
            st.subheader("📊 Estatísticas da Minha Coleção")
            
            itens_user = pd.read_sql("SELECT valor_estimado, moeda FROM itens WHERE dono_atual_pubkey = ?", conn, params=(pub_key,))
            
            m1, m2 = st.columns(2)
            m1.metric("Meus Itens Cadastrados", len(itens_user))
            
            if not itens_user.empty:
                cots = obter_cotacao_real_time()
                total_brl = sum([converter_moeda_v2(r['valor_estimado'], r['moeda'], 'BRL', cots) for _, r in itens_user.iterrows()])
                m2.metric("Meu Patrimônio Estimado", f"R$ {total_brl:,.2f}")
            else:
                m2.metric("Meu Patrimônio Estimado", "R$ 0,00")
        else:
            st.error("Erro: Cadastro não localizado para esta chave pública.")
            # Debug: Mostrar toda a tabela
            df_debug = pd.read_sql("SELECT * FROM colecionadores", conn)
            st.write("DEBUG: Conteúdo atual da tabela colecionadores:")
            st.dataframe(df_debug)




# ========================================================
# Navegar Coleções
# ========================================================
elif pagina == "Navegar Coleções":
    st.header("🌐 Galeria Global de Colecionadores")
    
    if st.session_state.get('user_status') != 'logged_in':
        st.error("🚫 Acesso restrito. Por favor, faça login para navegar pelas coleções.")
    else:
        cots_n = obter_cotacao_real_time()
        
        # 1. BUSCA TOTAL DE ITENS E NOMES DOS DONOS
        query_n = """
            SELECT i.*, c.username, c.pubkey 
            FROM itens i 
            JOIN colecionadores c ON i.colecionador_id = c.id
        """
        df_n = pd.read_sql(query_n, conn)
        
        if df_n.empty:
            st.info("Ainda não há ativos cadastrados na rede.")
        else:
            # --- ÁREA DE PESQUISA E FILTROS ---
            col_search, col_filter = st.columns(2)
            
            with col_search:
                busca_uuid = st.text_input("🔍 Pesquisar por UUID Único", placeholder="Ex: A1B2C3D4").upper().strip()
            
            with col_filter:
                usuarios_unicos = ["Todos"] + list(df_n['username'].unique())
                filtro_user = st.selectbox("Filtrar por Colecionador", usuarios_unicos)

            # 2. LÓGICA DE FILTRAGEM
            df_exib = df_n
            if busca_uuid:
                df_exib = df_exib[df_exib['uuid_unico'] == busca_uuid]
            if filtro_user != "Todos":
                df_exib = df_exib[df_exib['username'] == filtro_user]

            if df_exib.empty:
                st.warning(f"Nenhum item encontrado para os critérios selecionados.")
            else:
                st.write(f"Exibindo **{len(df_exib)}** ativos da comunidade.")

                for index, row in df_exib.iterrows():
                    with st.expander(f"📦 {row['nome']} | UUID: {row['uuid_unico']} | Dono: {row['username']}"):
                        # CORREÇÃO DE NOMES DE COLUNAS (c1, c2, c3)
                        c1, c2, c3 = st.columns([1, 1.5, 1])
                        
                        with c1:
                            if row['imagem_url']:
                                st.image(row['imagem_url'], use_container_width=True)
                            st.write(f"**Dono:** {row['username']}")
                            st.caption(f"Chave: `{row['pubkey'][:15]}...`")

                        with c2: # PERFORMANCE INDIVIDUAL
                            st.markdown("**📈 Análise Financeira**")
                            c_ind = calcular_comparativos_historicos(row['data_aquisicao'])
                            v_at_brl = converter_moeda_v2(row['valor_estimado'], row['moeda'], 'BRL', cots_n)
                            v_pg_brl = converter_moeda_v2(row['preco_compra'], row['moeda'], 'BRL', cots_n)
                            
                            if v_pg_brl > 0:
                                val = ((v_at_brl - v_pg_brl) / v_pg_brl) * 100
                                st.write(f"Valorização: **{val:.2f}%**")
                                if val > c_ind['m2_usd_perc']: st.success("🏆 Venceu M2 EUA")
                                if val > c_ind['btc_perc']: st.success("🚀 Venceu o Bitcoin")

                        with c3: # MÉTRICAS EM 3 MOEDAS (Real, Dólar e Bitcoin)
                            st.markdown("**💰 Avaliação Atual**")
                            v_usd = converter_moeda_v2(row['valor_estimado'], row['moeda'], 'USD', cots_n)
                            v_btc = converter_moeda_v2(row['valor_estimado'], row['moeda'], 'BTC', cots_n)
                            
                            st.metric("Real", f"R$ {v_at_brl:,.2f}")
                            st.metric("Dólar", f"$ {v_usd:,.2f}") # <-- Dólar Restaurado
                            st.metric("Bitcoin", f"₿ {v_btc:.8f}")

                        # --- HISTÓRICO DE PROPRIETÁRIOS ---
                        st.write("---")
                        st.markdown("📜 **Histórico de Proveniência**")
                        df_h = pd.read_sql("SELECT * FROM historico_transferencias WHERE item_id = ? ORDER BY id ASC", conn, params=(row['id'],))
                        if df_h.empty:
                            st.caption("Proprietário Original (Gênese)")
                        else:
                            for _, hr in df_h.iterrows():
                                st.markdown(f"<div style='font-size: 0.8rem; border-left: 2px solid #ddd; padding-left: 8px; margin-bottom: 5px;'><b>{hr['data_transferencia']}</b>: {hr['antigo_dono_pubkey'][:10]}... → {hr['novo_dono_pubkey'][:10]}...</div>", unsafe_allow_html=True)

# ========================================================
# Painel do Administrador
# ========================================================


elif pagina == "Painel Administrativo":
    if st.session_state.get('current_user_pubkey') != ADMIN_PUBKEY:
        st.error("🚫 Acesso Negado.")
    else:
        st.title("⚙️ Painel de Controle Master")

        # Usar Radio em vez de Tabs evita que o Streamlit perca o estado do clique
        secao = st.radio("Selecione a área de gestão:", ["Usuários", "Itens", "Reset Total"], horizontal=True)

        if secao == "Usuários":
            st.subheader("👥 Gerenciar Usuários")
            # Usar conn global para evitar conflitos
            try:
                usuarios = pd.read_sql("SELECT * FROM colecionadores", conn)
                st.dataframe(usuarios, use_container_width=True)

                if not usuarios.empty:
                    # Verifica se a coluna 'pubkey' existe e tem valores
                    if 'pubkey' in usuarios.columns:
                        pubkeys = usuarios['pubkey'].dropna().tolist()  # Remove None e converte para lista
                        if not pubkeys:
                            st.warning("Nenhuma public key válida encontrada no banco de dados. Pode haver registros legados sem pubkey.")
                            if st.button("🧹 Limpar Registros Inválidos (sem pubkey)", use_container_width=True):
                                cursor.execute("DELETE FROM colecionadores WHERE pubkey IS NULL")
                                conn.commit()
                                st.success("Registros inválidos removidos!")
                                st.rerun()
                        else:
                            user_sel = st.selectbox("Selecione o usuário para remover:", pubkeys, key="user_to_del")
                            
                            if st.button("🗑️ EXCLUIR USUÁRIO AGORA", type="primary", use_container_width=True):
                                cursor.execute("DELETE FROM colecionadores WHERE pubkey = ?", (user_sel,))
                                conn.commit()
                                st.success(f"Usuário removido!")
                                st.rerun()
                    else:
                        st.error("Coluna 'pubkey' não encontrada na tabela. Verifique o esquema do banco.")
                else:
                    st.info("Nenhum usuário cadastrado no banco de dados.")
            except Exception as e:
                st.error(f"Erro ao gerenciar usuários: {str(e)}")

        elif secao == "Itens":
            st.subheader("📦 Gerenciar Itens")
            try:
                itens = pd.read_sql("SELECT * FROM itens", conn)
                st.dataframe(itens, use_container_width=True)

                if not itens.empty:
                    item_id = st.number_input("ID do Item para excluir:", min_value=1, step=1)
                    if st.button("🗑️ EXCLUIR ITEM AGORA", use_container_width=True):
                        cursor.execute("DELETE FROM itens WHERE id = ?", (item_id,))
                        conn.commit()
                        st.success("Item removido!")
                        st.rerun()
            except Exception as e:
                st.error(f"Erro ao gerenciar itens: {str(e)}")

        elif secao == "Reset Total":
            st.subheader("🚨 Zona de Perigo")
            confirmar = st.text_input("Digite 'CONFIRMAR' para limpar o banco:")
            if st.button("🔥 RESETAR TODO O SISTEMA", use_container_width=True):
                if confirmar == "CONFIRMAR":
                    cursor.execute("DELETE FROM colecionadores")
                    cursor.execute("DELETE FROM itens")
                    cursor.execute("DELETE FROM historico_transferencias")
                    conn.commit()
                    st.success("Banco resetado!")
                    st.rerun()
                else:
                    st.error("Palavra incorreta.")



















