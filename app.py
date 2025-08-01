
"""Sistema de Ponto FGV (modo offline / fake Snowflake)
Execute local:
    pip install -r requirements.txt
    streamlit run app.py
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, time
import io

# ---------- "Conexão" fake com Snowflake ----------
class FakeSnowflakeConnection:
    def __init__(self):
        st.session_state.setdefault('pontos', [])  # lista de dicionários

    def insert_ponto(self, registro: dict):
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

menu = st.sidebar.radio('Menu', ['Marcar Ponto', 'Relatório Diário', 'Exportar Excel'])

# Marcação de ponto
if menu == 'Marcar Ponto':
    st.subheader('Registrar Ponto')
    nome = st.text_input('Nome do colaborador')
    cargo = st.text_input('Cargo')
    data = st.date_input('Data', value=date.today())
    col1, col2 = st.columns(2)
    with col1:
        entrada = st.time_input('Entrada', value=time(8, 0))
    with col2:
        saida = st.time_input('Saída', value=time(17, 0))

    if st.button('Salvar'):
        if nome.strip():
            horas = (datetime.combine(date.today(), saida) - datetime.combine(date.today(), entrada)).total_seconds()/3600
            registro = dict(nome=nome, cargo=cargo, data=str(data), entrada=str(entrada), saida=str(saida), horas=round(horas,2))
            conn.insert_ponto(registro)
            st.success('Ponto registrado!')
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
