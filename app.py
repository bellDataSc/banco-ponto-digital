"""Sistema de Ponto FGV (modo offline / fake Snowflake)
Execute local:
    pip install -r requirements.txt
    streamlit run app.py
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import io

# ---------- "Conexão" fake com Snowflake ----------
class FakeSnowflakeConnection:
    def __init__(self):
        st.session_state.setdefault('pontos', [])  # lista de dicionários
        st.session_state.setdefault('batidas', {})  # dicionário de batidas por pessoa/dia

    def insert_batida(self, nome: str, data: str, tipo_batida: str, hora: str):
        # Cria chave única para cada pessoa/dia
        chave = f"{nome}_{data}"
        
        # Inicializa o registro se não existir
        if chave not in st.session_state.batidas:
            st.session_state.batidas[chave] = {
                'nome': nome,
                'data': data,
                'entrada': None,
                'saida_almoco': None,
                'retorno_almoco': None,
                'saida': None
            }
        
        # Atualiza o tipo de batida específico
        st.session_state.batidas[chave][tipo_batida] = hora
        
        # Calcula horas trabalhadas se tiver dados suficientes
        registro = st.session_state.batidas[chave]
        self._calcular_horas(registro)
        
        # Adiciona ou atualiza na lista de pontos
        self._atualizar_pontos(registro)
    
    def _calcular_horas(self, registro):
        # Só calcula se tiver pelo menos entrada e saída
        if registro['entrada'] and registro['saida']:
            # Converte strings para objetos time
            entrada = datetime.strptime(registro['entrada'], '%H:%M:%S').time()
            saida = datetime.strptime(registro['saida'], '%H:%M:%S').time()
            
            # Calcula tempo total (sem considerar almoço inicialmente)
            total_segundos = (datetime.combine(date.today(), saida) - 
                             datetime.combine(date.today(), entrada)).total_seconds()
            
            # Se tiver registro de almoço, subtrai esse período
            if registro['saida_almoco'] and registro['retorno_almoco']:
                saida_almoco = datetime.strptime(registro['saida_almoco'], '%H:%M:%S').time()
                retorno_almoco = datetime.strptime(registro['retorno_almoco'], '%H:%M:%S').time()
                
                almoco_segundos = (datetime.combine(date.today(), retorno_almoco) - 
                                 datetime.combine(date.today(), saida_almoco)).total_seconds()
                
                total_segundos -= almoco_segundos
            
            # Converte para horas e arredonda
            registro['horas'] = round(total_segundos / 3600, 2)
    
    def _atualizar_pontos(self, registro):
        # Verifica se já existe um registro para essa pessoa/dia
        for i, ponto in enumerate(st.session_state.pontos):
            if ponto['nome'] == registro['nome'] and ponto['data'] == registro['data']:
                # Atualiza o registro existente
                st.session_state.pontos[i] = registro
                return
        
        # Se não existir, adiciona um novo
        st.session_state.pontos.append(registro)

    def fetch_pontos(self):
        return pd.DataFrame(st.session_state.pontos)

# Instância única
@st.cache_resource
def get_conn():
    return FakeSnowflakeConnection()

conn = get_conn()

# ---------- UI ----------
st.set_page_config(page_title='Ponto FGV', page_icon='⏰', layout='wide')
st.title('⏰ Sistema de Ponto FGV (Demo)')

menu = st.sidebar.radio('Menu', ['Registrar Batida', 'Relatório Diário', 'Exportar Excel'])

# Registro de batidas
if menu == 'Registrar Batida':
    st.subheader('Registro de Batida')
    nome = st.text_input('Nome do colaborador')
    data = st.date_input('Data', value=date.today())
    hora_atual = datetime.now().time()
    hora_batida = st.time_input('Horário da batida', value=hora_atual)
    
    tipo_batida = st.radio(
        "Tipo de batida",
        ["entrada", "saida_almoco", "retorno_almoco", "saida"],
        format_func=lambda x: {
            "entrada": "Entrada", 
            "saida_almoco": "Saída para almoço", 
            "retorno_almoco": "Retorno do almoço", 
            "saida": "Saída"
        }[x]
    )

    if st.button('Registrar Batida'):
        if nome.strip():
            conn.insert_batida(
                nome=nome, 
                data=str(data), 
                tipo_batida=tipo_batida, 
                hora=str(hora_batida)
            )
            st.success(f'Batida de {tipo_batida.replace("_", " ")} registrada!')
        else:
            st.error('Preencha o nome.')

# Relatório diário
if menu == 'Relatório Diário':
    st.subheader('Relatório do Dia')
    df = conn.fetch_pontos()
    if df.empty:
        st.info('Nenhum ponto registrado ainda.')
    else:
        hoje = str(date.today())
        df_today = df[df['data'] == hoje]
        st.dataframe(df_today, use_container_width=True)
        total_horas = df_today['horas'].sum()
        st.metric('Total de horas hoje', f"{total_horas:.2f}h")

# Exportar Excel
if menu == 'Exportar Excel':
    st.subheader('Exportar dados para Excel')
    df = conn.fetch_pontos()
    if df.empty:
        st.info('Sem dados para exportar.')
    else:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Pontos')
        st.download_button('📥 Baixar Excel', buffer.getvalue(), file_name='pontos_fgv.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
