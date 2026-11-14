import streamlit as st
import pandas as pd
import plotly.express as px


# Carregar o arquivo com o separador ponto e vírgula
df = pd.read_csv('cantonamento_ferroviario_pt_leve.csv', sep=';')

# Array com colunas para serem removidas
colunas_para_remover = [
    'id_trecho',
    'nome_linha_fr',
    'modo_cantonamento_fr',
    'pk_inicial_orig',
    'pk_final_orig',
    'coord_geo_inicio',
    'coord_geo_fim',
    'geo_ponto_central'
]

# Removendo as colunas
df_formatado = df.drop(columns=[col for col in colunas_para_remover if col in df.columns])

# Exibir as primeiras linhas do DataFrame formatado
#display(df_formatado.head())


# Configurações iniciais da página do Streamlit
st.set_page_config(page_title="Cantonamento Ferroviário", layout="wide")


# Definições para o tratamento do dataframe no streamlit, com as formatações feitas anteriormente
@st.cache_data
def preparar_dados_dashboard(dataframe_base):
    df_dashboard = dataframe_base.copy()

    # Trata os valores nulos do nível de automação como "Não classificado"
    df_dashboard['nivel_automacao_rotulo'] = df_dashboard['nivel_automacao_rotulo'].fillna('Não classificado').astype(str)

    # Calcula as coordenadas médias de latitude e longitude de cada trecho para plotar no mapa
    df_dashboard['lat_meio'] = (df_dashboard['latitude_inicio'] + df_dashboard['latitude_fim']) / 2
    df_dashboard['lon_meio'] = (df_dashboard['longitude_inicio'] + df_dashboard['longitude_fim']) / 2

    return df_dashboard

# Atribuição dos dados preparados a partir do dataframe global
df = preparar_dados_dashboard(df_formatado)



#1 --- Barra Lateral (Filtros) ---
st.sidebar.header("Filtros")

# Filtro de Família Tecnológica
familias = st.sidebar.multiselect(
    "Família tecnológica",
    sorted(df['familia_tecnologica'].dropna().unique()),
    default=sorted(df['familia_tecnologica'].dropna().unique())
)


# Filtro de Tipo de Via
vias = st.sidebar.multiselect(
    "Tipo de via",
    sorted(df['tipo_via'].dropna().unique()),
    default=sorted(df['tipo_via'].dropna().unique())
)


# Filtro de Nível de Automação
niveis = st.sidebar.multiselect(
    "Nível de automação",
    sorted(df['nivel_automacao_rotulo'].unique()),
    default=sorted(df['nivel_automacao_rotulo'].unique())
)


# Aplicação dos filtros selecionados sobre o DataFrame principal
f = df[
    df['familia_tecnologica'].isin(familias) &
    df['tipo_via'].isin(vias) &
    df['nivel_automacao_rotulo'].isin(niveis)
]



#2 --- Cabeçalho e Métricas Principais ---
st.title("Cantonamento Ferroviário")

# Cálculos matemáticos de extensão geral e automática
km_total = f['extensao_km'].sum()
km_auto = f.loc[f['nivel_automacao'] >= 3, 'extensao_km'].sum()

# Exibição dos principais KPIs organizados em 4 colunas
c1, c2, c3, c4 = st.columns(4)
c1.metric("Trechos", f"{len(f):,}".replace(",", "."))
c2.metric("Linhas", f"{f['codigo_linha'].nunique():,}".replace(",", "."))
c3.metric("Extensão total (km)", f"{km_total:,.0f}".replace(",", "."))
c4.metric("% km automático (nível ≥ 3)", f"{(km_auto / km_total * 100) if km_total else 0:.1f}%")



#3 --- Primeiro Bloco de Gráficos (Família e Modo de Cantonamento) ---
col1, col2 = st.columns(2)


# Gráfico de barras horizontais: Extensão por família tecnológica
por_familia = (f.groupby('familia_tecnologica', as_index=False)['extensao_km']
                 .sum().sort_values('extensao_km'))
col1.plotly_chart(
    px.bar(por_familia, x='extensao_km', y='familia_tecnologica', orientation='h',
           title="Extensão (km) por família tecnológica",
           labels={'extensao_km': 'km', 'familia_tecnologica': ''}),
    use_container_width=True
)


# Gráfico de barras horizontais: Top 10 modos de cantonamento mais comuns
por_modo = (f.groupby('modo_cantonamento', as_index=False)['extensao_km']
              .sum().nlargest(10, 'extensao_km').sort_values('extensao_km'))
col2.plotly_chart(
    px.bar(por_modo, x='extensao_km', y='modo_cantonamento', orientation='h',
           title="Top 10 modos de cantonamento (km)",
           labels={'extensao_km': 'km', 'modo_cantonamento': ''}),
    use_container_width=True
)



#3 --- Segundo Bloco de Gráficos (Tipo de Via e Distribuição da Extensão) ---
col3, col4 = st.columns(2)


# Gráfico empilhado: Relação entre o tipo de via e as famílias tecnológicas
via_fam = (f.groupby(['tipo_via', 'familia_tecnologica'], as_index=False)['extensao_km'].sum())
col3.plotly_chart(
    px.bar(via_fam, x='tipo_via', y='extensao_km', color='familia_tecnologica',
           title="Tipo de via × família tecnológica (km)",
           labels={'extensao_km': 'km', 'tipo_via': ''}),
    use_container_width=True
)


# Histograma: Distribuição das extensões em escala logarítmica
col4.plotly_chart(
    px.histogram(f.dropna(subset=['extensao_km']), x='extensao_km', nbins=60,
                 log_x=True, title="Distribuição da extensão dos trechos (km, escala log)"),
    use_container_width=True
)


# Gráfico de barras horizontais: Maiores ferrovias/linhas por km total
top_linhas = (f.groupby('nome_linha', as_index=False)['extensao_km']
                .sum().nlargest(15, 'extensao_km').sort_values('extensao_km'))
st.plotly_chart(
    px.bar(top_linhas, x='extensao_km', y='nome_linha', orientation='h',
           title="15 maiores linhas por extensão (km)",
           labels={'extensao_km': 'km', 'nome_linha': ''}, height=550),
    use_container_width=True
)



#4 --- Mapa dos Trechos ---
st.subheader("Mapa dos trechos")
st.plotly_chart(
    px.scatter_map(f, lat='lat_meio', lon='lon_meio', color='familia_tecnologica',
                   hover_name='nome_linha',
                   hover_data={'modo_cantonamento': True, 'extensao_km': ':.1f',
                               'lat_meio': False, 'lon_meio': False},
                   zoom=4.5, height=600, map_style='carto-positron'),
    use_container_width=True
)



#5 --- Tabela de Dados Expandível ---
with st.expander("Ver dados filtrados"):
    st.dataframe(f)
