import streamlit as st
import pandas as pd
import unicodedata
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Dashboard Prodepa", layout="wide")

CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vStCsK-I9n6aQ6argn2xcQ1jIe5BCcvHrG5PNmq7xd13dd6i5iZovnR8ahCOzUQZztC8DlT4vYAZyRf/"
    "pub?gid=2120793063&single=true&output=csv"
)

# ------------------------------------------------------------------ #
# Utilidades
# ------------------------------------------------------------------ #
def strip_accents(text: str) -> str:
    """Remove acentos de uma string (NFD)."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(text))
        if unicodedata.category(c) != 'Mn'
    )

@st.cache_data(ttl=3600)
def carregar_dados():
    df = pd.read_csv(CSV_URL)

    # Padronizar cabeçalhos
    df.columns = [
        strip_accents(col).upper().strip().replace(' ', '_')
        for col in df.columns
    ]

    # Padronizar texto de algumas colunas
    for col in ['STATUS', 'SERVICO', 'GRANDEZA', 'MUNICIPIO']:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .apply(lambda x: strip_accents(x).upper().strip())
            )

    # Converter datas
    if 'DATA_INICIO' in df.columns:
        df['DATA_INICIO'] = pd.to_datetime(
            df['DATA_INICIO'],
            dayfirst=True,
            errors='coerce'
        )

    # Limpar valores monetários
    if 'VALOR_ATUAL' in df.columns:
        df['VALOR_ATUAL_LIMPO'] = (
            df['VALOR_ATUAL']
            .astype(str)
            .str.replace('R$', '', regex=False)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .str.strip()
            .astype(float)
        )

    return df

# ------------------------------------------------------------------ #
# App
# ------------------------------------------------------------------ #
def main():
    st.title("📊 Dashboard de Serviços - Prodepa")

    with st.spinner("Carregando dados..."):
        df = carregar_dados()

    # ---------------------- Filtros laterais ---------------------- #
    st.sidebar.header("🔍 Filtros")

    if 'STATUS' in df.columns:
        opts = df['STATUS'].unique().tolist()
        sel_status = st.sidebar.multiselect("Filtrar por Status", opts, default=opts)
        df = df[df['STATUS'].isin(sel_status)]

    if 'SERVICO' in df.columns:
        opts = df['SERVICO'].unique().tolist()
        sel_serv = st.sidebar.multiselect("Filtrar por Serviço", opts, default=opts)
        df = df[df['SERVICO'].isin(sel_serv)]

    # ✅ CORREÇÃO AQUI — usar o mesmo nome de coluna
    if 'SITUACAO_DO_CONTRATO' in df.columns:
        opts = df['SITUACAO_DO_CONTRATO'].unique().tolist()
        sel_situacao = st.sidebar.multiselect(
            "Filtrar por Situação do Contrato",
            opts,
            default=opts
        )
        df = df[df['SITUACAO_DO_CONTRATO'].isin(sel_situacao)]

    # ------------------------- KPIs ------------------------- #
    st.subheader("📈 KPIs Gerais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Contratos", len(df))

    # Extrair banda em MB caso não exista
    if 'BANDA_MB' not in df.columns and 'GRANDEZA' in df.columns:
        df['BANDA_MB'] = (
            df['GRANDEZA']
            .str.extract(r'(\d+)')
            .astype(float)
        )

    if 'BANDA_MB' in df.columns:
        col2.metric("Média de Banda (MB)", f"{df['BANDA_MB'].mean():.1f}")

    if 'MUNICIPIO' in df.columns:
        col3.metric("Municípios Atendidos", df['MUNICIPIO'].nunique())

    st.markdown("---")

    # --------------------- Visualizações --------------------- #
    if 'BANDA_MB' in df.columns:
        st.subheader("📊 Distribuição de Largura de Banda")
        banda_counts = df['BANDA_MB'].value_counts().sort_index()
        st.bar_chart(banda_counts)

    if 'SERVICO' in df.columns:
        st.subheader("🧮 Share de Serviços Contratados")
        serv_pct = df['SERVICO'].value_counts(normalize=True)
        fig1, ax1 = plt.subplots()
        ax1.pie(serv_pct, labels=serv_pct.index, autopct="%1.1f%%", startangle=90)
        ax1.axis('equal')
        st.pyplot(fig1)

    if {'SERVICO', 'MUNICIPIO'}.issubset(df.columns):
        st.subheader("📍 Top 10 Municípios com Link de Dados Rádio")
        radio = df[df['SERVICO'] == 'LINK DE DADOS RADIO']
        st.bar_chart(radio['MUNICIPIO'].value_counts().head(10))

        st.subheader("📍 Top 10 Municípios com Link de Dados Fibra")
        fibra = df[df['SERVICO'] == 'LINK DE DADOS FIBRA']
        st.bar_chart(fibra['MUNICIPIO'].value_counts().head(10))

    # Arrecadação por serviço
    if {'SERVICO', 'VALOR_ATUAL_LIMPO'}.issubset(df.columns):
        st.subheader("💰 Arrecadação por Serviço")
        arrec_servico = (
            df.groupby('SERVICO')['VALOR_ATUAL_LIMPO']
              .sum()
              .sort_values(ascending=False)
        )
        st.bar_chart(arrec_servico)

        total_arrec = arrec_servico.sum()
        st.metric(
            "💸 Total Arrecadado",
            f"R$ {total_arrec:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    # Top 15 municípios (maior / menor arrecadação)
    if {'MUNICIPIO', 'VALOR_ATUAL_LIMPO'}.issubset(df.columns):
        st.subheader("🏙️ Top 15 Municípios com Maior Arrecadação")
        top_municipios = (
            df.groupby('MUNICIPIO')['VALOR_ATUAL_LIMPO']
              .sum()
              .sort_values(ascending=False)
              .head(15)
        )
        st.bar_chart(top_municipios)

        st.subheader("🏙️ Top 15 Municípios com Menor Arrecadação")
        bottom_municipios = (
            df.groupby('MUNICIPIO')['VALOR_ATUAL_LIMPO']
              .sum()
              .sort_values()
              .head(15)
        )
        st.bar_chart(bottom_municipios)

    # Heatmap Serviço x Municípios
    if {'MUNICIPIO', 'SERVICO'}.issubset(df.columns):
        st.subheader("🌡️ Heatmap do Volume de Serviço x Top 15 Municípios")
        top15 = df['MUNICIPIO'].value_counts().head(15).index
        top5  = df['SERVICO'].value_counts().head(5).index
        df_sub = df[df['MUNICIPIO'].isin(top15) & df['SERVICO'].isin(top5)]
        pivot_hm = df_sub.pivot_table(
            index='MUNICIPIO',
            columns='SERVICO',
            aggfunc='size',
            fill_value=0
        )
        fig3, ax3 = plt.subplots(figsize=(8, 6))
        sns.heatmap(pivot_hm, annot=True, fmt='d', cmap='YlGnBu', ax=ax3)
        ax3.set_ylabel('Município')
        ax3.set_xlabel('Serviço')
        st.pyplot(fig3)

    # ---------------------- Dados brutos ---------------------- #
    st.subheader("📋 Dados Brutos Filtrados")
    st.dataframe(df)

# ------------------------------------------------------------------ #
if __name__ == "__main__":
    main()
