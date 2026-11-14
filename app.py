from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Cantonamento Ferroviário", layout="wide")

CSV_PATH = Path(__file__).parent / "cantonamento_ferroviario_pt_leve.csv"

COLUNAS_PARA_REMOVER = [
    "id_trecho",
    "nome_linha_fr",
    "modo_cantonamento_fr",
    "pk_inicial_orig",
    "pk_final_orig",
    "coord_geo_inicio",
    "coord_geo_fim",
    "geo_ponto_central",
]


@st.cache_data
def carregar_dados():
    dataframe = pd.read_csv(CSV_PATH, sep=";")
    dataframe = dataframe.drop(
        columns=[coluna for coluna in COLUNAS_PARA_REMOVER if coluna in dataframe.columns]
    )
    dataframe["nivel_automacao_rotulo"] = (
        dataframe["nivel_automacao_rotulo"].fillna("Não classificado").astype(str)
    )
    dataframe["lat_meio"] = (
        dataframe["latitude_inicio"] + dataframe["latitude_fim"]
    ) / 2
    dataframe["lon_meio"] = (
        dataframe["longitude_inicio"] + dataframe["longitude_fim"]
    ) / 2
    return dataframe


df = carregar_dados()

st.sidebar.header("Filtros")

familias_disponiveis = sorted(df["familia_tecnologica"].dropna().unique())
familias = st.sidebar.multiselect(
    "Família tecnológica",
    familias_disponiveis,
    default=familias_disponiveis,
)

vias_disponiveis = sorted(df["tipo_via"].dropna().unique())
vias = st.sidebar.multiselect(
    "Tipo de via",
    vias_disponiveis,
    default=vias_disponiveis,
)

niveis_disponiveis = sorted(df["nivel_automacao_rotulo"].unique())
niveis = st.sidebar.multiselect(
    "Nível de automação",
    niveis_disponiveis,
    default=niveis_disponiveis,
)

f = df[
    df["familia_tecnologica"].isin(familias)
    & df["tipo_via"].isin(vias)
    & df["nivel_automacao_rotulo"].isin(niveis)
]

st.title("Cantonamento Ferroviário")

km_total = f["extensao_km"].sum()
km_auto = f.loc[f["nivel_automacao"] >= 3, "extensao_km"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Trechos", f"{len(f):,}".replace(",", "."))
c2.metric("Linhas", f"{f['codigo_linha'].nunique():,}".replace(",", "."))
c3.metric("Extensão total (km)", f"{km_total:,.0f}".replace(",", "."))
c4.metric("% km automático (nível ≥ 3)", f"{(km_auto / km_total * 100) if km_total else 0:.1f}%")

col1, col2 = st.columns(2)

por_familia = (
    f.groupby("familia_tecnologica", as_index=False)["extensao_km"]
    .sum()
    .sort_values("extensao_km")
)
col1.plotly_chart(
    px.bar(
        por_familia,
        x="extensao_km",
        y="familia_tecnologica",
        orientation="h",
        title="Extensão (km) por família tecnológica",
        labels={"extensao_km": "km", "familia_tecnologica": ""},
    ),
    use_container_width=True,
)

por_modo = (
    f.groupby("modo_cantonamento", as_index=False)["extensao_km"]
    .sum()
    .nlargest(10, "extensao_km")
    .sort_values("extensao_km")
)
col2.plotly_chart(
    px.bar(
        por_modo,
        x="extensao_km",
        y="modo_cantonamento",
        orientation="h",
        title="Top 10 modos de cantonamento (km)",
        labels={"extensao_km": "km", "modo_cantonamento": ""},
    ),
    use_container_width=True,
)

col3, col4 = st.columns(2)

via_fam = f.groupby(
    ["tipo_via", "familia_tecnologica"], as_index=False
)["extensao_km"].sum()
col3.plotly_chart(
    px.bar(
        via_fam,
        x="tipo_via",
        y="extensao_km",
        color="familia_tecnologica",
        title="Tipo de via × família tecnológica (km)",
        labels={"extensao_km": "km", "tipo_via": ""},
    ),
    use_container_width=True,
)

col4.plotly_chart(
    px.histogram(
        f.dropna(subset=["extensao_km"]),
        x="extensao_km",
        nbins=60,
        log_x=True,
        title="Distribuição da extensão dos trechos (km, escala log)",
    ),
    use_container_width=True,
)

top_linhas = (
    f.groupby("nome_linha", as_index=False)["extensao_km"]
    .sum()
    .nlargest(15, "extensao_km")
    .sort_values("extensao_km")
)
st.plotly_chart(
    px.bar(
        top_linhas,
        x="extensao_km",
        y="nome_linha",
        orientation="h",
        title="15 maiores linhas por extensão (km)",
        labels={"extensao_km": "km", "nome_linha": ""},
        height=550,
    ),
    use_container_width=True,
)

st.subheader("Mapa dos trechos")
st.plotly_chart(
    px.scatter_map(
        f,
        lat="lat_meio",
        lon="lon_meio",
        color="familia_tecnologica",
        hover_name="nome_linha",
        hover_data={
            "modo_cantonamento": True,
            "extensao_km": ":.1f",
            "lat_meio": False,
            "lon_meio": False,
        },
        zoom=4.5,
        height=600,
        map_style="carto-positron",
    ),
    use_container_width=True,
)

with st.expander("Ver dados filtrados"):
    st.dataframe(f)
