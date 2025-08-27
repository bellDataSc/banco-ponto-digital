import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional
import hashlib
import io

# ==================== CONFIGURAÇÕES ====================
st.set_page_config(
    page_title="Sistema de Ponto FGV",
    page_icon="⏰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para visual FGV (Azul e Branco)
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
    }
    .main-header {
        background: linear-gradient(90deg, #003366, #0066cc);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
    }
    .metric-card {
        background: #f8f9fa;
        border: 2px solid #0066cc;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .success-msg {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 10px;
        color: #155724;
    }
    .sidebar .sidebar-content {
        background: #f8f9fa;
    }
    .stButton > button {
        background: #0066cc;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 20px;
    }
    .stButton > button:hover {
        background: #003366;
    }
</style>
""", unsafe_allow_html=True)

# ==================== CLASSES E FUNÇÕES ====================

class UsuarioManager:
    """Gerenciamento de usuários e autenticação"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.md5(password.encode()).hexdigest()
    
    @staticmethod
    def init_usuarios():
        """Inicializa usuários padrão"""
        if 'usuarios' not in st.session_state:
            st.session_state.usuarios = {
                'maria': {
                    'senha': UsuarioManager.hash_password('123'),
                    'nome': 'Maria Silva',
                    'cargo': 'Analista',
                    'contratos': {'Contrato A': 70, 'Contrato B': 30}
                },
                'joao': {
                    'senha': UsuarioManager.hash_password('456'),
                    'nome': 'João Santos',
                    'cargo': 'Coordenador',
                    'contratos': {'Contrato A': 50, 'Contrato C': 50}
                },
                'admin': {
                    'senha': UsuarioManager.hash_password('admin'),
                    'nome': 'Administrador',
                    'cargo': 'Admin',
                    'contratos': {'Gestão': 100}
                }
            }
    
    @staticmethod
    def autenticar(usuario: str, senha: str) -> bool:
        usuarios = st.session_state.get('usuarios', {})
        return (usuario in usuarios and 
                usuarios[usuario]['senha'] == UsuarioManager.hash_password(senha))
    
    @staticmethod
    def get_usuario_info(usuario: str) -> Dict:
        return st.session_state.usuarios.get(usuario, {})

class PontoManager:
    """Gerenciamento de batidas de ponto"""
    
    @staticmethod
    def init_pontos():
        if 'pontos' not in st.session_state:
            st.session_state.pontos = []
    
    @staticmethod
    def registrar_batida(usuario: str, tipo: str) -> Dict:
        now = datetime.now()
        batida = {
            'id': len(st.session_state.pontos) + 1,
            'usuario': usuario,
            'tipo': tipo,
            'data': now.strftime('%Y-%m-%d'),
            'horario': now.strftime('%H:%M:%S'),
            'timestamp': now
        }
        st.session_state.pontos.append(batida)
        return batida
    
    @staticmethod
    def get_batidas_usuario(usuario: str, data_filtro: Optional[str] = None) -> List[Dict]:
        batidas = st.session_state.pontos
        resultado = [b for b in batidas if b['usuario'] == usuario]
        
        if data_filtro:
            resultado = [b for b in resultado if b['data'] == data_filtro]
        
        return resultado
    
    @staticmethod
    def calcular_horas_dia(usuario: str, data: str) -> Dict:
        batidas = PontoManager.get_batidas_usuario(usuario, data)
        
        horas_info = {
            'entrada': None,
            'saida': None,
            'almoco_saida': None,
            'almoco_retorno': None,
            'extras': [],
            'total_horas': 0,
            'horas_almoco': 0
        }
        
        for batida in batidas:
            if batida['tipo'] == 'entrada':
                horas_info['entrada'] = batida['horario']
            elif batida['tipo'] == 'saida':
                horas_info['saida'] = batida['horario']
            elif batida['tipo'] == 'almoco_saida':
                horas_info['almoco_saida'] = batida['horario']
            elif batida['tipo'] == 'almoco_retorno':
                horas_info['almoco_retorno'] = batida['horario']
            elif batida['tipo'].startswith('extra'):
                horas_info['extras'].append({
                    'tipo': batida['tipo'],
                    'horario': batida['horario']
                })
        
        # Calcular total de horas
        if horas_info['entrada'] and horas_info['saida']:
            entrada_dt = datetime.strptime(f"{data} {horas_info['entrada']}", '%Y-%m-%d %H:%M:%S')
            saida_dt = datetime.strptime(f"{data} {horas_info['saida']}", '%Y-%m-%d %H:%M:%S')
            horas_info['total_horas'] = (saida_dt - entrada_dt).total_seconds() / 3600
            
            # Descontar almoço se houver
            if horas_info['almoco_saida'] and horas_info['almoco_retorno']:
                almoco_saida_dt = datetime.strptime(f"{data} {horas_info['almoco_saida']}", '%Y-%m-%d %H:%M:%S')
                almoco_retorno_dt = datetime.strptime(f"{data} {horas_info['almoco_retorno']}", '%Y-%m-%d %H:%M:%S')
                horas_info['horas_almoco'] = (almoco_retorno_dt - almoco_saida_dt).total_seconds() / 3600
                horas_info['total_horas'] -= horas_info['horas_almoco']
        
        return horas_info

class RelatorioManager:
    """Geração de relatórios e estatísticas"""
    
    @staticmethod
    def calcular_porcentagem_contratos(usuario: str, mes: int, ano: int) -> Dict:
        # Filtrar batidas do mês
        inicio_mes = f"{ano:04d}-{mes:02d}-01"
        if mes == 12:
            fim_mes = f"{ano+1:04d}-01-01"
        else:
            fim_mes = f"{ano:04d}-{mes+1:02d}-01"
        
        batidas = st.session_state.pontos
        batidas_mes = [
            b for b in batidas 
            if (b['usuario'] == usuario and 
                inicio_mes <= b['data'] < fim_mes)
        ]
        
        # Agrupar por dia e calcular horas
        dias_trabalhados = {}
        for batida in batidas_mes:
            data = batida['data']
            if data not in dias_trabalhados:
                dias_trabalhados[data] = []
            dias_trabalhados[data].append(batida)
        
        total_horas_mes = 0
        for data in dias_trabalhados:
            horas_dia = PontoManager.calcular_horas_dia(usuario, data)
            total_horas_mes += horas_dia['total_horas']
        
        # Aplicar porcentagem por contrato
        usuario_info = UsuarioManager.get_usuario_info(usuario)
        contratos = usuario_info.get('contratos', {})
        
        resultado = {}
        for contrato, porcentagem in contratos.items():
            horas_contrato = (total_horas_mes * porcentagem) / 100
            resultado[contrato] = {
                'porcentagem': porcentagem,
                'horas': round(horas_contrato, 2)
            }
        
        return resultado, total_horas_mes

# ==================== INICIALIZAÇÃO ====================

def init_app():
    """Inicializa aplicação"""
    UsuarioManager.init_usuarios()
    PontoManager.init_pontos()
    
    if 'logged_user' not in st.session_state:
        st.session_state.logged_user = None
    if 'entrada_automatica' not in st.session_state:
        st.session_state.entrada_automatica = {}

init_app()

# ==================== INTERFACE PRINCIPAL ====================

# Header
st.markdown("""
<div class="main-header">
    <h1>⏰ Sistema de Ponto FGV</h1>
    <p>Avenida Paulista - Controle de Frequência</p>
</div>
""", unsafe_allow_html=True)

# ==================== LOGIN ====================

def tela_login():
    """Tela de login"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("Login")
        
        with st.form("login_form"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar", use_container_width=True)
            
            if submit:
                if UsuarioManager.autenticar(usuario, senha):
                    st.session_state.logged_user = usuario
                    # Registrar entrada automática
                    if usuario not in st.session_state.entrada_automatica:
                        PontoManager.registrar_batida(usuario, 'entrada')
                        st.session_state.entrada_automatica[usuario] = datetime.now().strftime('%Y-%m-%d')
                        st.success("Login realizado! Entrada registrada automaticamente.")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos!")
        
        # Informações de teste
        st.info("""
        **Usuários de teste:**
        - maria / 123
        - joao / 456  
        - admin / admin
        """)

# ==================== DASHBOARD PRINCIPAL ====================

def dashboard_principal():
    """Dashboard principal após login"""
    usuario = st.session_state.logged_user
    usuario_info = UsuarioManager.get_usuario_info(usuario)
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80/003366/FFFFFF?text=FGV", caption="Fundação Getulio Vargas")
        st.write(f"**Usuário:** {usuario_info.get('nome', usuario)}")
        st.write(f"**Cargo:** {usuario_info.get('cargo', 'N/A')}")
        
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_user = None
            st.rerun()
    
    # Menu principal
    menu = st.selectbox(
        "Selecione uma opção:",
        ["Batidas de Ponto", "Relatórios", "Dashboard", "Histórico", "Exportar Dados"]
    )
    
    if menu == "Batidas de Ponto":
        tela_batidas()
    elif menu == "Relatórios":
        tela_relatorios()
    elif menu == "Dashboard":
        tela_dashboard()
    elif menu == "Histórico":
        tela_historico()
    elif menu == "Exportar Dados":
        tela_exportar()

# ==================== TELAS FUNCIONAIS ====================

def tela_batidas():
    """Tela de registro de batidas"""
    st.subheader("Registro de Batidas de Ponto")
    
    usuario = st.session_state.logged_user
    hoje = datetime.now().strftime('%Y-%m-%d')
    horas_hoje = PontoManager.calcular_horas_dia(usuario, hoje)
    
    # Status do dia
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_entrada = "✅" if horas_hoje['entrada'] else "❌"
        st.metric("Entrada", horas_hoje['entrada'] or "Não registrada", delta=status_entrada)
    
    with col2:
        status_saida = "✅" if horas_hoje['saida'] else "❌"
        st.metric("Saída", horas_hoje['saida'] or "Não registrada", delta=status_saida)
    
    with col3:
        st.metric("Almoço", 
                 f"{horas_hoje['almoco_saida'] or '--'} / {horas_hoje['almoco_retorno'] or '--'}")
    
    with col4:
        st.metric("Horas Trabalhadas", f"{horas_hoje['total_horas']:.2f}h")
    
    # Botões de batida
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("Registrar Saída", use_container_width=True):
            PontoManager.registrar_batida(usuario, 'saida')
            st.success("Saída registrada!")
            st.rerun()
    
    with col2:
        if st.button("Saída Almoço", use_container_width=True):
            PontoManager.registrar_batida(usuario, 'almoco_saida')
            st.success("Saída para almoço registrada!")
            st.rerun()
    
    with col3:
        if st.button("Retorno Almoço", use_container_width=True):
            PontoManager.registrar_batida(usuario, 'almoco_retorno')
            st.success("Retorno do almoço registrado!")
            st.rerun()
    
    with col4:
        if st.button("Extra 1", use_container_width=True):
            PontoManager.registrar_batida(usuario, 'extra1')
            st.success("Batida extra 1 registrada!")
            st.rerun()
    
    with col5:
        if st.button("Extra 2", use_container_width=True):
            PontoManager.registrar_batida(usuario, 'extra2')
            st.success("Batida extra 2 registrada!")
            st.rerun()

def tela_relatorios():
    """Tela de relatórios"""
    st.subheader("Relatórios por Contrato")
    
    usuario = st.session_state.logged_user
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        mes = st.selectbox("Mês", range(1, 13), index=datetime.now().month-1)
    with col2:
        ano = st.selectbox("Ano", range(2023, 2026), index=1)  # 2024 como padrão
    
    # Calcular relatório
    contratos_info, total_horas = RelatorioManager.calcular_porcentagem_contratos(usuario, mes, ano)
    
    if total_horas > 0:
        st.metric("Total de Horas no Mês", f"{total_horas:.2f}h")
        
        # Gráfico de pizza
        labels = list(contratos_info.keys())
        values = [info['horas'] for info in contratos_info.values()]
        
        fig = px.pie(values=values, names=labels, 
                    title=f"Distribuição de Horas por Contrato - {mes:02d}/{ano}")
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela detalhada
        st.subheader("Detalhamento por Contrato")
        df_contratos = pd.DataFrame([
            {
                'Contrato': contrato,
                'Porcentagem (%)': info['porcentagem'],
                'Horas': info['horas']
            }
            for contrato, info in contratos_info.items()
        ])
        st.dataframe(df_contratos, use_container_width=True)
    else:
        st.info("Nenhuma hora registrada para este período.")

def tela_dashboard():
    """Dashboard com métricas gerais"""
    st.subheader("Dashboard Geral")
    
    usuario = st.session_state.logged_user
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    # Métricas da semana
    inicio_semana = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')
    batidas_semana = [
        b for b in st.session_state.pontos
        if b['usuario'] == usuario and b['data'] >= inicio_semana
    ]
    
    # Calcular horas da semana
    dias_semana = {}
    for batida in batidas_semana:
        data = batida['data']
        if data not in dias_semana:
            dias_semana[data] = PontoManager.calcular_horas_dia(usuario, data)
    
    total_semana = sum(dia['total_horas'] for dia in dias_semana.values())
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        horas_hoje = PontoManager.calcular_horas_dia(usuario, hoje)
        st.metric("Horas Hoje", f"{horas_hoje['total_horas']:.2f}h")
    
    with col2:
        st.metric("Horas esta Semana", f"{total_semana:.2f}h")
    
    with col3:
        meta_semanal = 40  # 40h por semana
        progresso = (total_semana / meta_semanal) * 100
        st.metric("Progresso Semanal", f"{progresso:.1f}%")
    
    with col4:
        dias_trabalhados = len(dias_semana)
        st.metric("Dias Trabalhados", f"{dias_trabalhados}")
    
    # Gráfico de horas diárias da semana
    if dias_semana:
        df_semana = pd.DataFrame([
            {'Data': data, 'Horas': info['total_horas']}
            for data, info in dias_semana.items()
        ])
        
        fig = px.bar(df_semana, x='Data', y='Horas', 
                    title="Horas Trabalhadas por Dia (Esta Semana)")
        fig.update_layout(yaxis_title="Horas")
        st.plotly_chart(fig, use_container_width=True)

def tela_historico():
    """Histórico completo de batidas"""
    st.subheader("Histórico de Batidas")
    
    usuario = st.session_state.logged_user
    batidas = PontoManager.get_batidas_usuario(usuario)
    
    if batidas:
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data Início", 
                                      value=datetime.now() - timedelta(days=30))
        with col2:
            data_fim = st.date_input("Data Fim", value=datetime.now())
        
        # Filtrar batidas
        batidas_filtradas = [
            b for b in batidas
            if data_inicio.strftime('%Y-%m-%d') <= b['data'] <= data_fim.strftime('%Y-%m-%d')
        ]
        
        # Criar DataFrame
        df = pd.DataFrame(batidas_filtradas)
        df = df[['data', 'tipo', 'horario']]
        df.columns = ['Data', 'Tipo', 'Horário']
        
        # Traduzir tipos
        tipo_map = {
            'entrada': 'Entrada',
            'saida': 'Saída',
            'almoco_saida': 'Saída Almoço',
            'almoco_retorno': 'Retorno Almoço',
            'extra1': 'Extra 1',
            'extra2': 'Extra 2'
        }
        df['Tipo'] = df['Tipo'].map(tipo_map)
        
        st.dataframe(df, use_container_width=True)
        
        # Estatísticas do período
        st.subheader("Estatísticas do Período")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Batidas", len(batidas_filtradas))
        
        with col2:
            dias_unicos = len(set(b['data'] for b in batidas_filtradas))
            st.metric("Dias com Batidas", dias_unicos)
        
        with col3:
            entradas = len([b for b in batidas_filtradas if b['tipo'] == 'entrada'])
            st.metric("Total de Entradas", entradas)
    else:
        st.info("Nenhuma batida registrada ainda.")

def tela_exportar():
    """Exportação de dados"""
    st.subheader("Exportar Dados")
    
    usuario = st.session_state.logged_user
    batidas = PontoManager.get_batidas_usuario(usuario)
    
    if batidas:
        # Criar DataFrame completo
        df = pd.DataFrame(batidas)
        df = df[['data', 'tipo', 'horario']]
        
        # Excel
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Exportar Excel")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Batidas', index=False)
                
                # Criar sheet com resumo
                resumo_data = []
                datas_unicas = sorted(set(b['data'] for b in batidas))
                
                for data in datas_unicas:
                    horas_dia = PontoManager.calcular_horas_dia(usuario, data)
                    resumo_data.append({
                        'Data': data,
                        'Entrada': horas_dia['entrada'],
                        'Saída': horas_dia['saida'],
                        'Horas Trabalhadas': horas_dia['total_horas']
                    })
                
                df_resumo = pd.DataFrame(resumo_data)
                df_resumo.to_excel(writer, sheet_name='Resumo Diário', index=False)
            
            st.download_button(
                "Baixar Excel",
                buffer.getvalue(),
                file_name=f"ponto_{usuario}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            st.subheader("Exportar CSV")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Baixar CSV",
                csv,
                file_name=f"ponto_{usuario}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    else:
        st.info("Nenhum dado para exportar.")

# ==================== EXECUÇÃO PRINCIPAL ====================

if st.session_state.logged_user is None:
    tela_login()
else:
    dashboard_principal()
