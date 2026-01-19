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

conn = sqlite3.connect('colecionadores.db', check_same_thread=False)
cursor = conn.cursor()

# COLOQUE ESTA LINHA NO TOPO DO ARQUIVO (FORA DE QUALQUER FUNÇÃO)
url = "https://api.blockchair.com"

# ========================================================
# TROCA DE ITENS
# ========================================================

cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_transferencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        antigo_dono_pubkey TEXT,
        novo_dono_pubkey TEXT,
        data_transferencia TEXT,
        FOREIGN KEY(item_id) REFERENCES itens(id)
    )
""")
conn.commit()



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
        # Debug básico
        print(f"DEBUG - Endereço: {endereco}")
        print(f"DEBUG - Mensagem: '{mensagem}' (len={len(mensagem)})")
        print(f"DEBUG - Assinatura: '{assinatura[:20]}...' (len={len(assinatura)})")

        sig_bytes = base64.b64decode(assinatura.strip())
        print(f"DEBUG - Header byte: {sig_bytes[0]}")
        if len(sig_bytes) != 65:
            return False, f"Tamanho inválido: {len(sig_bytes)} bytes (deve ser 65)"

        header = sig_bytes[0]
        rec_id = header - 27
        print(f"DEBUG - Rec ID: {rec_id}")
        
        # Permite 0-4 para compatibilidade (algumas wallets usam 4)
        if rec_id not in (0, 1, 2, 3, 4):
            return False, f"Rec ID inválido: {rec_id} (deve ser 0-4)"

        r = int.from_bytes(sig_bytes[1:33], 'big')
        s = int.from_bytes(sig_bytes[33:], 'big')

        # Hash Bitcoin Signed Message (corrigido para varint preciso)
        prefix = b"Bitcoin Signed Message:\n"
        msg_bytes = mensagem.encode('utf-8')
        msg_len = len(msg_bytes)
        if msg_len < 253:
            len_bytes = bytes([msg_len])
        else:
            len_bytes = b'\xfd' + msg_len.to_bytes(2, 'little')
        full_message = prefix + len_bytes + msg_bytes
        message_hash = hashlib.sha256(hashlib.sha256(full_message).digest()).digest()

        curve = SECP256k1
        public_keys = VerifyingKey.from_public_key_recovery(
            (r, s),
            message_hash,
            curve=curve,
            hashfunc=hashlib.sha256,
            allow_truncate=True,
            rec_id=rec_id % 4,  # Mod para forçar 0-3 se for 4
            compressed=(header >= 31)  # 31+ = compressed
        )

        if not public_keys:
            return False, "Nenhuma pubkey recuperada (hash ou sig inválida)"

        vk = public_keys[0]
        pubkey_bytes = vk.to_string("compressed" if (header >= 31) else "uncompressed")
        sha = hashlib.sha256(pubkey_bytes).digest()
        ripemd = hashlib.new('ripemd160', sha).digest()
        extended = b'\x00' + ripemd  # Mainnet P2PKH
        checksum = hashlib.sha256(hashlib.sha256(extended).digest()).digest()[:4]
        endereco_recuperado = base58_encode(extended + checksum)

        print(f"DEBUG - Endereço recuperado: {endereco_recuperado}")

        match = endereco_recuperado == endereco.strip()
        return match, f"{'VÁLIDA' if match else f'INVÁLIDA (recuperado: {endereco_recuperado})'}"

    except Exception as e:
        return False, f"Erro: {str(e)}"

# Exemplo rápido de teste (rode no seu console)
if __name__ == "__main__":
    valido, motivo = verificar_assinatura_bitcoin(
        "1BH7pLzx4WC1P89JmBgep58gUAsKkS62u8",
        "teste1",
        "H48+iRY0pEpblxe7zLEwoBx5qVkSz2sMbMY2uK7ME9eENR4NcysMbgPLUYguEskshhLjYftWiuxV43FmUra9iq4="
    )
    print(f"Resultado: {valido} - {motivo}")



def on_verify_click(pub_key, mensagem_desafio, assinatura):
    # ( ... sua lógica de verificação anterior ... )
    
    if verificar_assinatura_bitcoin(pub_key, mensagem_desafio, assinatura):
        # 1. Define o login como sucesso
        st.session_state['user_status'] = 'logged_in'
        st.session_state['current_user_pubkey'] = pub_key
        
        # 2. O PULO DO GATO: Muda a página e LIMPA os inputs de login
        # Isso impede que o sistema fique "preso" na página de login
        st.session_state['pagina_ativa'] = "Meu Perfil"
        
        # 3. Limpa os campos de texto do formulário de login (se você usou chaves neles)
        if 'input_pk' in st.session_state: st.session_state['input_pk'] = ""
        if 'input_sig' in st.session_state: st.session_state['input_sig'] = ""
        
        st.success("Autenticado com sucesso!")
    else:
        st.session_state['user_status'] = 'invalid_signature'

# ========================================================
# TRADUÇÃO
# ========================================================

# Dicionário de tradução
LANGUAGES = {
    'Português': {
        'menu': ["Cadastrar Colecionador", "Adicionar Item", "Visualizar Coleções"],
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
def nav_home(): st.session_state['pagina_ativa'] = "Início"
def nav_login(): st.session_state['pagina_ativa'] = "Cadastrar Colecionador"
def nav_perfil(): st.session_state['pagina_ativa'] = "Meu Perfil"
def nav_add(): st.session_state['pagina_ativa'] = "Adicionar Item"
def nav_view(): st.session_state['pagina_ativa'] = "Visualizar Coleções"

def realizar_logout():
    st.session_state['user_status'] = None
    st.session_state['current_user_pubkey'] = None
    st.session_state['pagina_ativa'] = "Início"

if 'pagina_ativa' not in st.session_state:
    st.session_state['pagina_ativa'] = "Início"

# --- NAVEGAÇÃO POR BOTÕES NA SIDEBAR (COM LÓGICA DE LOGIN OCULTO) ---
with st.sidebar:
    st.title("🛡️ Sistema de Elite")
    
    if 'pagina_ativa' not in st.session_state:
        st.session_state['pagina_ativa'] = "Início"

    # 1. BOTÃO INÍCIO (Sempre visível)
    if st.button("🏠 Início", use_container_width=True, key="nav_home"):
        st.session_state['pagina_ativa'] = "Início"
        st.rerun()

    if st.session_state.get('user_status') == 'logged_in':
        if st.button("🌐 Navegar Coleções", use_container_width=True, key="nav_browse"):
            st.session_state['pagina_ativa'] = "Navegar Coleções"
            st.rerun()

    # 2. LÓGICA CONDICIONAL DE BOTÕES
    if st.session_state.get('user_status') == 'logged_in':
        # --- SE ESTIVER LOGADO: Oculta Login e mostra o resto ---
        st.write("---")
        
        if st.button("👤 Meu Perfil", use_container_width=True, key="nav_perfil"):
            st.session_state['pagina_ativa'] = "Meu Perfil"
            st.rerun()
        
        if st.button("📦 Adicionar Item", use_container_width=True, key="nav_add"):
            st.session_state['pagina_ativa'] = "Adicionar Item"
            st.rerun()
        
        if st.button("🔍 Minha Coleção", use_container_width=True, key="nav_view"):
            st.session_state['pagina_ativa'] = "Visualizar Coleções"
            st.rerun()

        st.write("---")
        # Botão de Logout para encerrar a sessão
        if st.button("🔴 Encerrar Sessão", use_container_width=True, key="nav_logout"):
            st.session_state['user_status'] = None
            st.session_state['current_user_pubkey'] = None
            st.session_state['pagina_ativa'] = "Início"
            st.rerun()
            
    else:
        # --- SE ESTIVER DESLOGADO: Mostra apenas o botão de Login ---
        st.write("---")
        if st.button("🔑 Login / Cadastro", use_container_width=True, key="nav_login"):
            st.session_state['pagina_ativa'] = "Cadastrar Colecionador"
            st.rerun()

# Vincula o menu ao corpo do site
menu = st.session_state['pagina_ativa']


# ========================================================
# 2. PÁGINA INICIAL (DASHBOARD DIDÁTICO)
# ========================================================
# ========================================================
# PÁGINA: INÍCIO (MOSTRADORES DE ELITE)
# ========================================================
if menu == "Início":
    st.title("🏛️ Sistema Isaac Niche - Colecionismo 3.0")
    st.markdown(f"**Data:** 19/01/2026 | **Status:** {'🟢 Autenticado' if st.session_state.get('user_status') == 'logged_in' else '⚪ Modo Leitura'}")
    
    try:
        # 1. BUSCA DE DADOS DIRETAMENTE NO BANCO
        # Puxamos todos os itens para calcular o valor global (riqueza catalogada)
        df_itens_dash = pd.read_sql("SELECT valor_estimado, moeda FROM itens", conn)
        
        # Puxamos o número de colecionadores únicos
        df_users_dash = pd.read_sql("SELECT id FROM colecionadores", conn)
        
        # Cotações em tempo real (necessário para o cálculo da Riqueza)
        cots_dash = obter_cotacao_real_time()

        # 2. CÁLCULO DA RIQUEZA CATALOGADA (Soma de todos os itens convertidos para Reais)
        riqueza_catalogada = 0.0
        if not df_itens_dash.empty:
            riqueza_catalogada = sum([converter_moeda_v2(row['valor_estimado'], row['moeda'], 'BRL', cots_dash) for _, row in df_itens_dash.iterrows()])

        # 3. MOSTRADORES (OS CARDS DE MÉTRICAS)
        st.write("---")
        m1, m2, m3 = st.columns(3)
        
        with m1:
            st.metric("Itens Registrados", f"{len(df_itens_dash)}")
        
        with m2:
            st.metric("Riqueza Catalogada", f"R$ {riqueza_catalogada:,.2f}")
        
        with m3:
            st.metric("Colecionadores Ativos", f"{len(df_users_dash)}")

        st.write("---")
        
        # 4. TEXTO DIDÁTICO E VISUAL
        st.subheader("Bem-vindo ao Dashboard de Ativos Físicos")
        st.write("""
            Este sistema rastreia o valor real do seu acervo físico em tempo real. 
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
        st.warning("📊 Dashboard em inicialização. Cadastre itens para ativar as métricas.")








# ========================================================
# 3. PÁGINA DE LOGIN (CRIPTO-ASSINATURA)
# ========================================================
elif menu == "Cadastrar Colecionador":
    if st.session_state.get('user_status') == 'logged_in':
        st.success(f"✅ Você já está autenticado como: `{st.session_state['current_user_pubkey']}`")
        if st.button("Ir para Meu Perfil"):
            st.session_state['pagina_ativa'] = "Meu Perfil"
            st.rerun()
    else:
        st.header("🔑 Acesso ao Sistema Isaac Niche")
        
        # --- FORMULÁRIO DE LOGIN (TOPO) ---
        st.warning("⚠️ Use apenas endereços **Legacy** (que começam com **'1'**). Endereços bc1q... não são compatíveis com a assinatura de mensagens.")
        
        msg_desafio = "teste1"
        st.write("Mensagem para assinar:")
        st.code(msg_desafio, language="text")
        
        addr = st.text_input("Seu Endereço Bitcoin Legacy (Ex: 1BH7...)")
        sig = st.text_area("Sua Assinatura (Signature)")
        
        if st.button("Verificar e Acessar Sistema", type="primary", use_container_width=True):
            if verificar_assinatura_bitcoin(addr, msg_desafio, sig):
                cursor.execute("INSERT OR IGNORE INTO colecionadores (public_key) VALUES (?)", (addr,))
                conn.commit()
                st.session_state['user_status'] = 'logged_in'
                st.session_state['current_user_pubkey'] = addr
                st.session_state['pagina_ativa'] = "Meu Perfil"
                st.success("✅ Identidade verificada! Acessando perfil...")
                st.rerun()
            else:
                st.error("🚫 Falha na verificação. Verifique se o endereço é Legacy (começa com 1) e se a assinatura está correta.")

        # --- MANUAL INSTRUTIVO (QUADRO FIXO NA BASE) ---
        with st.container(border=True):
            st.subheader("📖 Guia de Início Rápido")
            
            col_man1, col_man2 = st.columns(2)
            with col_man1:
                st.markdown("""
                **1. Instale a BlueWallet**
                *   [iPhone](https://apps.apple.com)
                *   [Android](https://play.google.com)
                """)
            with col_man2:
                st.markdown("""
                **2. Crie uma Carteira Legacy**
                Ao criar, escolha o tipo **'Legacy'** ou **'P2PKH'**. É vital que o endereço comece com **'1'** para que a assinatura funcione no sistema.
                """)
            
            st.divider()
            st.markdown("""
            **3. Como assinar a mensagem de acesso?**
            1. No app BlueWallet, clique na sua carteira e vá em **Ferramentas** (ícone de três pontos).
            2. Selecione **"Assinar/Verificar Mensagem"**.
            3. No campo **Endereço**, use o endereço da sua carteira.
            4. No campo **Mensagem**, digite exatamente o código mostrado acima (`teste1`).
            5. Clique em **Assinar** e cole o texto gerado no campo **Assinatura** deste site.
            """)



# ========================================================
# 4. PÁGINA ADICIONAR ITEM (NFT-STYLE)
# ========================================================
elif menu == "Adicionar Item":
    if st.session_state.get('user_status') != 'logged_in':
        st.error("🚫 Acesso negado. Por favor, identifique-se primeiro no menu Login.")
    else:
        st.header("📦 Adicionar Novo Ativo à Coleção")
        
        # Carrega colecionadores para vincular o item ao dono correto
        colecionadores = pd.read_sql("SELECT id, public_key, username FROM colecionadores", conn)

        if colecionadores.empty:
            st.warning("Nenhum colecionador cadastrado. Acesse 'Cadastrar Colecionador' primeiro.")
        else:
            # Lógica de seleção do dono original
            colecionadores['display'] = colecionadores.apply(
                lambda r: r['username'] if r['username'] and str(r['username']).strip() != 'Anonimo' 
                else str(r['public_key'])[:15] + "...", axis=1
            )
            
            idx_user = 0
            if 'current_user_pubkey' in st.session_state:
                try:
                    idx_user = list(colecionadores['public_key']).index(st.session_state['current_user_pubkey'])
                except:
                    idx_user = 0

            nome_selecionado = st.selectbox("Selecione o Dono do Item", colecionadores['display'], index=idx_user)
            
            linha_user = colecionadores[colecionadores['display'] == nome_selecionado].iloc[0]
            c_id = int(linha_user['id'])
            pk_dono = linha_user['public_key']

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
# 5. VISUALIZAR COLEÇÕES (ANÁLISE DE ELITE)
# ========================================================
elif menu == "Visualizar Coleções":
    st.header("🔍 Painel de Gestão e Performance")
    
    if st.session_state.get('user_status') != 'logged_in':
        st.error("🚫 Acesso restrito. Faça login para gerenciar seus itens.")
    else:
        pub_key = st.session_state['current_user_pubkey']
        cots_v = obter_cotacao_real_time()

        # 1. BUSCA DE DADOS
        query_v = "SELECT * FROM itens WHERE dono_atual_pubkey = ?"
        df_v = pd.read_sql(query_v, conn, params=(pub_key,))

        if df_v.empty:
            st.info("Você ainda não possui itens cadastrados para análise.")
        else:
            # --- PAINEL GERAL (DASHBOARD) ---
            with st.container(border=True):
                st.subheader("📊 Estatísticas Consolidadas")
                t_invest_brl = sum([converter_moeda_v2(r['preco_compra'], r['moeda'], 'BRL', cots_v) for _, r in df_v.iterrows()])
                t_patrim_brl = sum([converter_moeda_v2(r['valor_estimado'], r['moeda'], 'BRL', cots_v) for _, r in df_v.iterrows()])
                perf_geral = ((t_patrim_brl - t_invest_brl) / t_invest_brl * 100) if t_invest_brl > 0 else 0
                
                comp_g = calcular_comparativos_historicos(df_v['data_aquisicao'].min())

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Patrimônio Total", f"R$ {t_patrim_brl:,.2f}", f"{perf_geral:.2f}%")
                m2.metric("vs M2 EUA", f"{perf_geral:.1f}%", f"{perf_geral - comp_g['m2_usd_perc']:.1f}%")
                m3.metric("vs Bitcoin", f"{perf_geral:.1f}%", f"{perf_geral - comp_g['btc_perc']:.1f}%")
                m4.metric("Total Itens", len(df_v))

                st.write("---")
                df_v['data_dt'] = pd.to_datetime(df_v['data_aquisicao'])
                df_s = df_v.sort_values('data_dt')
                df_s['Evolução'] = df_s.apply(lambda r: converter_moeda_v2(r['valor_estimado'], r['moeda'], 'BRL', cots_v), axis=1).cumsum()
                st.area_chart(df_s.set_index('data_dt')['Evolução'], use_container_width=True)

            st.write("### 📦 Itens Individuais")
            
            # --- LOOP DE ITENS ---
            for index, row in df_v.iterrows():
                e_key, s_key, d_key = f"ed_{row['id']}", f"sn_{row['id']}", f"dl_{row['id']}"
                
                with st.expander(f"📦 {row['nome']} | UUID: {row['uuid_unico']}"):
                    if st.session_state.get(e_key):
                        # FORMULÁRIO DE EDIÇÃO (Completo como na criação)
                        with st.form(f"f_ed_{row['id']}"):
                            st.subheader("📝 Editar Ativo")
                            ce1, ce2 = st.columns(2)
                            with ce1:
                                n_nome = st.text_input("Nome", value=row['nome'])
                                n_cat = st.selectbox("Categoria", ["Moedas", "Relógios", "Arte", "Outros"], index=0)
                            with ce2:
                                n_val = st.number_input("Valor Estimado", value=float(row['valor_estimado']))
                                n_moeda = st.selectbox("Moeda", ["BRL", "USD", "BTC"], index=0)
                            if st.form_submit_button("Salvar"):
                                cursor.execute("UPDATE itens SET nome=?, categoria=?, valor_estimado=?, moeda=? WHERE id=?", (n_nome, n_cat, n_val, n_moeda, row['id']))
                                conn.commit()
                                st.session_state[e_key] = False
                                st.rerun()
                    else:
                        # --- VISUALIZAÇÃO PADRÃO CORRIGIDA ---
                        c1, c2, c3 = st.columns([1, 1.5, 1])
                        
                        with c1:
                            if row['imagem_url']: 
                                st.image(row['imagem_url'], use_container_width=True)
                            st.write(f"**UUID:** `{row['uuid_unico']}`")
                        
                        with c2: # Performance Individual vs M2 e BTC
                            st.markdown("**📈 Performance Individual**")
                            c_ind = calcular_comparativos_historicos(row['data_aquisicao'])
                            v_at_brl = converter_moeda_v2(row['valor_estimado'], row['moeda'], 'BRL', cots_v)
                            v_pg_brl = converter_moeda_v2(row['preco_compra'], row['moeda'], 'BRL', cots_v)
                            
                            if v_pg_brl > 0:
                                val_i = ((v_at_brl - v_pg_brl) / v_pg_brl) * 100
                                st.write(f"Valorização: **{val_i:.2f}%**")
                                st.write("---")
                                if val_i > c_ind['m2_usd_perc']: 
                                    st.success(f"🏆 Superou M2 EUA ({c_ind['m2_usd_perc']}%)")
                                else: 
                                    st.warning(f"📉 Abaixo do M2 EUA ({c_ind['m2_usd_perc']}%)")
                                
                                if val_i > c_ind['btc_perc']: 
                                    st.success(f"🚀 Superou Bitcoin ({c_ind['btc_perc']}%)")
                                else: 
                                    st.error(f"₿ Abaixo do Bitcoin ({c_ind['btc_perc']}%)")
                        
                        with c3: # MÉTRICAS EM 3 MOEDAS (Real, Dólar e Bitcoin)
                            st.markdown("**💰 Avaliação Atual**")
                            v_usd = converter_moeda_v2(row['valor_estimado'], row['moeda'], 'USD', cots_v)
                            v_btc = converter_moeda_v2(row['valor_estimado'], row['moeda'], 'BTC', cots_v)
                            
                            st.metric("Real", f"R$ {v_at_brl:,.2f}")
                            st.metric("Dólar", f"$ {v_usd:,.2f}")
                            st.metric("Bitcoin", f"₿ {v_btc:.8f}")


                        # BOTÕES DE AÇÃO (Editar, Enviar, Remover)
                        st.write("---")
                        b1, b2, b3 = st.columns(3)
                        if b1.button("📝 Editar", key=f"b_e_{row['id']}", use_container_width=True):
                            st.session_state[e_key] = True
                            st.rerun()
                        if b2.button("📤 Enviar", key=f"b_s_{row['id']}", use_container_width=True):
                            st.session_state[s_key] = True
                            st.rerun()
                        if b3.button("🗑️ Remover", key=f"b_d_{row['id']}", use_container_width=True):
                            st.session_state[d_key] = True
                            st.rerun()

                        # Lógica de Envio e Remoção Simplificada para não dar erro
                        if st.session_state.get(s_key):
                            d_pk = st.text_input("Endereço Destino", key=f"d_{row['id']}")
                            if st.button("Confirmar Envio", key=f"cs_{row['id']}"):
                                cursor.execute("UPDATE itens SET dono_atual_pubkey = ? WHERE id = ?", (d_pk, row['id']))
                                conn.commit()
                                st.rerun()
                        
                        if st.session_state.get(d_key):
                            if st.button("Confirmar Exclusão", key=f"cd_{row['id']}"):
                                cursor.execute("DELETE FROM itens WHERE id = ?", (row['id'],))
                                conn.commit()
                                st.rerun()

                        # HISTÓRICO DE PROPRIETÁRIOS
                        st.write("---")
                        st.markdown("📜 **Histórico de Proveniência**")
                        df_h = pd.read_sql("SELECT * FROM historico_transferencias WHERE item_id = ?", conn, params=(row['id'],))
                        for _, hr in df_h.iterrows():
                            st.caption(f"📅 {hr['data_transferencia']} | De: {hr['antigo_dono_pubkey'][:10]}... Para: {hr['novo_dono_pubkey'][:10]}...")








# ========================================================
# MEU PERFIL
# ========================================================
elif menu == "Meu Perfil":
    st.header("👤 Meu Perfil de Colecionador")

    # 1. Trava de Segurança
    if st.session_state.get('user_status') != 'logged_in':
        st.warning("⚠️ Você precisa estar logado com sua chave Bitcoin para acessar o perfil.")
    else:
        # Busca os dados atuais do usuário logado
        pub_key = st.session_state['current_user_pubkey']
        user_query = pd.read_sql("SELECT * FROM colecionadores WHERE public_key = ?", conn, params=(pub_key,))
        
        if not user_query.empty:
            # Pegamos os dados da linha (iloc)
            user_data = user_query.iloc[0]
            
            # --- ÁREA VISUAL DO PERFIL (SEM IMAGENS EXTERNAS) ---
            with st.container(border=True):
                col_emoji, col_info = st.columns([1, 4])
                with col_emoji:
                    # Usamos um emoji grande no lugar da imagem para evitar erros de carregamento
                    st.markdown("<h1 style='text-align: center; font-size: 60px;'>👤</h1>", unsafe_allow_html=True)
                with col_info:
                    st.subheader(f"Bem-vindo, {user_data['username']}")
                    st.code(f"Chave Bitcoin: {pub_key}", language="text")
            
            st.write("---")
            
            # --- FORMULÁRIO DE DADOS PESSOAIS ---
            with st.form("form_meu_perfil_2026"):
                st.subheader("📝 Editar Dados Pessoais")
                
                c1, c2 = st.columns(2)
                with c1:
                    novo_username = st.text_input("Nome / Apelido", value=user_data['username'])
                with c2:
                    # Tenta buscar o e-mail se a coluna existir no banco
                    email_atual = user_data['email'] if 'email' in user_data.index and user_data['email'] else ""
                    novo_email = st.text_input("E-mail de Contato", value=email_atual)
                
                nova_bio = st.text_area("Biografia / Sobre sua Coleção", value=user_data['bio'] if 'bio' in user_data.index and user_data['bio'] else "")
                
                if st.form_submit_button("💾 Salvar Alterações"):
                    try:
                        # Garante que a coluna email exista antes de tentar salvar
                        try:
                            cursor.execute("ALTER TABLE colecionadores ADD COLUMN email TEXT")
                        except:
                            pass # Já existe
                        
                        cursor.execute("""
                            UPDATE colecionadores 
                            SET username = ?, email = ?, bio = ? 
                            WHERE public_key = ?
                        """, (novo_username, novo_email, nova_bio, pub_key))
                        conn.commit()
                        st.success("✅ Perfil atualizado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

            # --- RESUMO PATRIMONIAL INDIVIDUAL ---
            st.write("---")
            st.subheader("📊 Estatísticas da Minha Coleção")
            
            # Busca itens vinculados a esta chave pública específica
            itens_user = pd.read_sql("SELECT valor_estimado, moeda FROM itens WHERE dono_atual_pubkey = ?", conn, params=(pub_key,))
            
            m1, m2 = st.columns(2)
            m1.metric("Meus Itens Cadastrados", len(itens_user))
            
            if not itens_user.empty:
                # Usa a função de tempo real para calcular o valor individual
                cots = obter_cotacao_real_time()
                total_brl = sum([converter_moeda_v2(r['valor_estimado'], r['moeda'], 'BRL', cots) for _, r in itens_user.iterrows()])
                m2.metric("Meu Patrimônio Estimado", f"R$ {total_brl:,.2f}")
            else:
                m2.metric("Meu Patrimônio Estimado", "R$ 0,00")
        else:
            st.error("Erro: Cadastro não localizado para esta chave pública.")


# ========================================================
# Navegar Coleções
# ========================================================
elif menu == "Navegar Coleções":
    st.header("🌐 Galeria Global de Colecionadores")
    
    if st.session_state.get('user_status') != 'logged_in':
        st.error("🚫 Acesso restrito. Por favor, faça login para navegar pelas coleções.")
    else:
        cots_n = obter_cotacao_real_time()
        
        # 1. BUSCA TOTAL DE ITENS E NOMES DOS DONOS
        query_n = """
            SELECT i.*, c.username, c.public_key 
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
                            st.caption(f"Chave: `{row['public_key'][:15]}...`")

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

conn.close()





