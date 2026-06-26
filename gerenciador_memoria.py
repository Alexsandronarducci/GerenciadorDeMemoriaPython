# Gerenciador de memória
# feito por Alexsandro Narducci e Lucas Cândido Belletti

import ctypes
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px


# Constantes usadas na WinAPI
TH32CS_SNAPPROCESS = 0x00000002
MAX_PATH = 260
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

LIMITE_HISTORICO = 30
LIMITE_HISTORICO_APLICATIVOS = 10


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ProcessID", ctypes.c_ulong),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", ctypes.c_ulong),
        ("cntThreads", ctypes.c_ulong),
        ("th32ParentProcessID", ctypes.c_ulong),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
        ("szExeFile", ctypes.c_wchar * MAX_PATH),
    ]


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
kernel32.GlobalMemoryStatusEx.restype = ctypes.c_int

kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p

kernel32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32)]
kernel32.Process32FirstW.restype = ctypes.c_int

kernel32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32)]
kernel32.Process32NextW.restype = ctypes.c_int

kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
kernel32.OpenProcess.restype = ctypes.c_void_p

kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.CloseHandle.restype = ctypes.c_int

psapi.GetProcessMemoryInfo.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
    ctypes.c_ulong
]
psapi.GetProcessMemoryInfo.restype = ctypes.c_int


def configurar_pagina():
    st.set_page_config(
        page_title="Gerenciador de Memória",
        page_icon="💻",
        layout="wide"
    )


def inicializar_estado_interface():
    if "historico_memoria" not in st.session_state:
        st.session_state.historico_memoria = []

    if "historico_processos" not in st.session_state:
        st.session_state.historico_processos = []

    if "limite_grafico_aplicativos" not in st.session_state:
        st.session_state.limite_grafico_aplicativos = 5

    if "visualizacao_tabela" not in st.session_state:
        st.session_state.visualizacao_tabela = "Aplicativos agrupados"

    if "quantidade_tabela" not in st.session_state:
        st.session_state.quantidade_tabela = 10

    if "filtro_tipo_tabela" not in st.session_state:
        st.session_state.filtro_tipo_tabela = "Todos"

    if "ordenacao_tabela" not in st.session_state:
        st.session_state.ordenacao_tabela = "Maior uso de memória"

    if "ultima_medicao_horario" not in st.session_state:
        st.session_state.ultima_medicao_horario = ""


def aplicar_estilo_visual():
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
            }

            .titulo-principal {
                font-size: 34px;
                font-weight: 700;
                margin-bottom: 0;
            }

            .subtitulo-principal {
                color: #666;
                font-size: 15px;
                margin-top: 4px;
                margin-bottom: 20px;
            }

            .cartao-metrica {
                background-color: #f8f9fb;
                border: 1px solid #e1e4e8;
                border-radius: 10px;
                padding: 18px;
                min-height: 115px;
            }

            .cartao-titulo {
                color: #555;
                font-size: 14px;
                margin-bottom: 8px;
            }

            .cartao-valor {
                color: #111;
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 4px;
            }

            .cartao-detalhe {
                color: #777;
                font-size: 13px;
            }

            .secao {
                margin-top: 28px;
                padding-top: 10px;
                border-top: 1px solid #e6e6e6;
            }

            .texto-ajuda {
                color: #666;
                font-size: 14px;
                margin-bottom: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )


def obter_horario_atualizacao():
    return datetime.now().strftime("%H:%M:%S")


def deve_registrar_medicao(horario_atualizacao):
    return st.session_state.ultima_medicao_horario != horario_atualizacao


def marcar_medicao_registrada(horario_atualizacao):
    st.session_state.ultima_medicao_horario = horario_atualizacao


def bytes_para_gb(valor_bytes):
    return round(valor_bytes / (1024 ** 3), 2)


def bytes_para_mb(valor_bytes):
    return round(valor_bytes / (1024 ** 2), 2)


def coletar_memoria_geral():
    try:
        estado_memoria = MEMORYSTATUSEX()
        estado_memoria.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

        resultado = kernel32.GlobalMemoryStatusEx(ctypes.byref(estado_memoria))

        if not resultado:
            erro = ctypes.get_last_error()
            return {
                "erro": "Não foi possível coletar os dados da memória. Código do erro: " + str(erro)
            }

        memoria_total = estado_memoria.ullTotalPhys
        memoria_disponivel = estado_memoria.ullAvailPhys
        memoria_usada = memoria_total - memoria_disponivel
        percentual_uso = estado_memoria.dwMemoryLoad

        return {
            "memoria_total_gb": bytes_para_gb(memoria_total),
            "memoria_disponivel_gb": bytes_para_gb(memoria_disponivel),
            "memoria_usada_gb": bytes_para_gb(memoria_usada),
            "percentual_uso": percentual_uso
        }

    except Exception as erro:
        return {
            "erro": "Erro inesperado ao coletar memória: " + str(erro)
        }


def obter_memoria_processo(pid):
    acesso = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    handle_processo = None

    try:
        handle_processo = kernel32.OpenProcess(acesso, False, pid)

        if not handle_processo:
            return 0

        contadores_memoria = PROCESS_MEMORY_COUNTERS()
        contadores_memoria.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)

        resultado = psapi.GetProcessMemoryInfo(
            handle_processo,
            ctypes.byref(contadores_memoria),
            contadores_memoria.cb
        )

        if not resultado:
            return 0

        return bytes_para_mb(contadores_memoria.WorkingSetSize)

    except Exception:
        return 0

    finally:
        # Fecha o processo quando ele foi aberto
        if handle_processo:
            kernel32.CloseHandle(handle_processo)


def coletar_processos():
    processos = []
    snapshot = None

    try:
        snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)

        if snapshot == INVALID_HANDLE_VALUE or not snapshot:
            return processos

        entrada_processo = PROCESSENTRY32()
        entrada_processo.dwSize = ctypes.sizeof(PROCESSENTRY32)

        sucesso = kernel32.Process32FirstW(snapshot, ctypes.byref(entrada_processo))

        while sucesso:
            pid = entrada_processo.th32ProcessID
            nome = entrada_processo.szExeFile
            memoria_mb = obter_memoria_processo(pid)

            processos.append({
                "pid": pid,
                "nome": nome,
                "memoria_mb": memoria_mb
            })

            sucesso = kernel32.Process32NextW(snapshot, ctypes.byref(entrada_processo))

        processos = sorted(
            processos,
            key=lambda processo: processo["memoria_mb"],
            reverse=True
        )

        return processos

    except Exception:
        return processos

    finally:
        # Fecha o snapshot da lista de processos
        if snapshot and snapshot != INVALID_HANDLE_VALUE:
            kernel32.CloseHandle(snapshot)


def classificar_processo(nome_processo, pid):
    processos_sistema = [
        "system",
        "registry",
        "smss.exe",
        "csrss.exe",
        "wininit.exe",
        "services.exe",
        "lsass.exe",
        "svchost.exe",
        "winlogon.exe",
        "dwm.exe"
    ]

    nome_formatado = nome_processo.lower()

    if pid == 0 or pid == 4:
        return "Sistema"

    if nome_formatado in processos_sistema:
        return "Sistema"

    return "Usuário"


def obter_chave_agrupamento(nome_processo):
    # Usa o executável exato como chave técnica, para agrupar os prcessos com esse executável repetido
    return str(nome_processo).strip().lower()


def normalizar_nome_aplicativo(nome_processo):
    nomes_conhecidos = {
        "msedge.exe": "Microsoft Edge",
        "msedgewebview2.exe": "Microsoft Edge WebView2",
        "chrome.exe": "Google Chrome",
        "firefox.exe": "Mozilla Firefox",
        "code.exe": "Visual Studio Code",
        "teams.exe": "Microsoft Teams",
        "ms-teams.exe": "Microsoft Teams"
    }

    chave = obter_chave_agrupamento(nome_processo)

    if chave in nomes_conhecidos:
        return nomes_conhecidos[chave]

    return str(nome_processo).strip()


def preparar_tabela_processos(processos):
    if len(processos) == 0:
        return pd.DataFrame(columns=["PID", "Processo", "Tipo", "Memória (MB)"])

    tabela = pd.DataFrame(processos)

    tabela["Tipo"] = tabela.apply(
        lambda linha: classificar_processo(linha["nome"], linha["pid"]),
        axis=1
    )

    tabela = tabela.rename(columns={
        "pid": "PID",
        "nome": "Processo",
        "memoria_mb": "Memória (MB)"
    })

    tabela = tabela[["PID", "Processo", "Tipo", "Memória (MB)"]]

    tabela["Memória (MB)"] = pd.to_numeric(tabela["Memória (MB)"], errors="coerce")
    tabela["Memória (MB)"] = tabela["Memória (MB)"].fillna(0)

    tabela = tabela.sort_values(by="Memória (MB)", ascending=False)
    tabela = tabela.reset_index(drop=True)

    return tabela


def agrupar_processos_por_aplicativo(tabela_processos):
    if len(tabela_processos) == 0:
        return pd.DataFrame(
            columns=[
                "Aplicativo",
                "Executável",
                "Tipo",
                "Quantidade de processos",
                "Memória (MB)",
                "PIDs"
            ]
        )

    tabela = tabela_processos.copy()

    tabela["Executável"] = tabela["Processo"].apply(obter_chave_agrupamento)
    tabela["Aplicativo"] = tabela["Processo"].apply(normalizar_nome_aplicativo)

    tabela_agrupada = tabela.groupby(
        ["Executável", "Aplicativo"],
        as_index=False
    ).agg({
        "Tipo": lambda valores: "Sistema" if all(valor == "Sistema" for valor in valores) else "Usuário",
        "PID": lambda valores: ", ".join(str(valor) for valor in valores),
        "Processo": "count",
        "Memória (MB)": "sum"
    })

    tabela_agrupada = tabela_agrupada.rename(columns={
        "PID": "PIDs",
        "Processo": "Quantidade de processos"
    })

    tabela_agrupada["Memória (MB)"] = tabela_agrupada["Memória (MB)"].round(2)

    tabela_agrupada = tabela_agrupada[
        [
            "Aplicativo",
            "Executável",
            "Tipo",
            "Quantidade de processos",
            "Memória (MB)",
            "PIDs"
        ]
    ]

    tabela_agrupada = tabela_agrupada.sort_values(
        by="Memória (MB)",
        ascending=False
    )

    tabela_agrupada = tabela_agrupada.reset_index(drop=True)

    return tabela_agrupada


def criar_nome_grafico_aplicativo(aplicativo, executavel):
    return str(aplicativo) + " (" + str(executavel) + ")"


def atualizar_historico_memoria(dados_memoria, horario):
    st.session_state.historico_memoria.append({
        "Horário": horario,
        "Uso da RAM (%)": dados_memoria["percentual_uso"]
    })

    # Mantém só as últimas medições, pare evitar que fique muito pesado
    st.session_state.historico_memoria = st.session_state.historico_memoria[-LIMITE_HISTORICO:]


def atualizar_historico_processos(tabela_aplicativos, horario):
    # Salva sempre o top 10 para o gráfico não ficar incompleto
    principais_aplicativos = tabela_aplicativos.head(LIMITE_HISTORICO_APLICATIVOS)

    aplicativos_medicao = []

    for indice, aplicativo in principais_aplicativos.iterrows():
        nome_grafico = criar_nome_grafico_aplicativo(
            aplicativo["Aplicativo"],
            aplicativo["Executável"]
        )

        aplicativos_medicao.append({
            "Aplicativo": nome_grafico,
            "Memória (MB)": aplicativo["Memória (MB)"]
        })

    st.session_state.historico_processos.append({
        "Horário": horario,
        "Aplicativos": aplicativos_medicao
    })

    # Mantém só as últimas medições, igual no caso da memória, seguindo a mesma constante
    st.session_state.historico_processos = st.session_state.historico_processos[-LIMITE_HISTORICO:]


def preparar_tabela_exibicao(tabela_base, filtro_tipo, ordenacao, quantidade):
    tabela = tabela_base.copy()

    if filtro_tipo != "Todos" and "Tipo" in tabela.columns:
        tabela = tabela[tabela["Tipo"] == filtro_tipo]

    if ordenacao == "Maior uso de memória":
        tabela = tabela.sort_values(by="Memória (MB)", ascending=False)

    elif ordenacao == "Menor uso de memória":
        tabela = tabela.sort_values(by="Memória (MB)", ascending=True)

    elif ordenacao == "Tipo e maior uso de memória":
        ordem_tipo = {
            "Sistema": 0,
            "Usuário": 1
        }

        tabela["_ordem_tipo"] = tabela["Tipo"].map(ordem_tipo).fillna(2)

        tabela = tabela.sort_values(
            by=["_ordem_tipo", "Memória (MB)"],
            ascending=[True, False]
        )

        tabela = tabela.drop(columns=["_ordem_tipo"])

    elif ordenacao == "Nome":
        if "Aplicativo" in tabela.columns:
            tabela = tabela.sort_values(by="Aplicativo", ascending=True)
        elif "Processo" in tabela.columns:
            tabela = tabela.sort_values(by="Processo", ascending=True)

    if quantidade != "Todos":
        tabela = tabela.head(quantidade)

    tabela = tabela.reset_index(drop=True)

    return tabela


def ajustar_indice_tabela(tabela):
    tabela = tabela.copy()
    tabela = tabela.reset_index(drop=True)
    tabela.index = tabela.index + 1
    tabela.index.name = "Nº"

    return tabela


def exibir_grafico_historico_memoria():
    if len(st.session_state.historico_memoria) == 0:
        return

    tabela_historico = pd.DataFrame(st.session_state.historico_memoria)

    grafico = px.line(
        tabela_historico,
        x="Horário",
        y="Uso da RAM (%)",
        title="Histórico de uso da memória RAM",
        markers=True
    )

    grafico.update_traces(
        hovertemplate="Horário: %{x}<br>Uso da RAM: %{y:.0f}%<extra></extra>"
    )

    grafico.update_yaxes(range=[0, 100])

    grafico.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=55, b=20),
        title_font_size=18,
        hovermode="x unified",
        xaxis_title="Horário",
        yaxis_title="Uso da RAM (%)"
    )

    st.plotly_chart(grafico, use_container_width=True)


def exibir_grafico_uso_atual_aplicativos(tabela_aplicativos, limite_aplicativos):
    if len(tabela_aplicativos) == 0:
        return

    tabela_grafico = tabela_aplicativos.head(limite_aplicativos).copy()

    tabela_grafico["Nome gráfico"] = tabela_grafico.apply(
        lambda linha: criar_nome_grafico_aplicativo(
            linha["Aplicativo"],
            linha["Executável"]
        ),
        axis=1
    )

    tabela_grafico = tabela_grafico.sort_values(
        by="Memória (MB)",
        ascending=True
    )

    grafico = px.bar(
        tabela_grafico,
        x="Memória (MB)",
        y="Nome gráfico",
        orientation="h",
        title="Aplicativos com maior uso de memória agora",
        custom_data=["Aplicativo", "Executável", "Memória (MB)"]
    )

    grafico.update_traces(
        hovertemplate=(
            "Aplicativo: %{customdata[0]}"
            "<br>Executável: %{customdata[1]}"
            "<br>Memória: %{customdata[2]:.2f} MB"
            "<extra></extra>"
        )
    )

    grafico.update_layout(
        height=380,
        margin=dict(l=20, r=20, t=55, b=20),
        title_font_size=18,
        xaxis_title="Memória (MB)",
        yaxis_title="Aplicativo",
        hovermode="closest",
        showlegend=False
    )

    st.plotly_chart(grafico, use_container_width=True)


def exibir_grafico_historico_processos(limite_processos):
    if len(st.session_state.historico_processos) == 0:
        return

    dados_grafico = []

    for medicao in st.session_state.historico_processos:
        horario = medicao["Horário"]
        aplicativos = medicao.get("Aplicativos", [])

        for aplicativo in aplicativos[:limite_processos]:
            dados_grafico.append({
                "Horário": horario,
                "Aplicativo": aplicativo["Aplicativo"],
                "Memória (MB)": aplicativo["Memória (MB)"]
            })

    if len(dados_grafico) == 0:
        return

    tabela_historico = pd.DataFrame(dados_grafico)

    grafico = px.line(
        tabela_historico,
        x="Horário",
        y="Memória (MB)",
        color="Aplicativo",
        title="Histórico dos aplicativos com maior uso de memória",
        markers=True,
        custom_data=["Aplicativo"]
    )

    grafico.update_traces(
        hovertemplate=(
            "Aplicativo: %{customdata[0]}"
            "<br>Horário: %{x}"
            "<br>Memória: %{y:.2f} MB"
            "<extra></extra>"
        )
    )

    grafico.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=55, b=20),
        title_font_size=18,
        hovermode="closest",
        legend_title_text="Aplicativo",
        xaxis_title="Horário",
        yaxis_title="Memória (MB)"
    )

    st.plotly_chart(grafico, use_container_width=True)


def exibir_cartao_metrica(titulo, valor, detalhe):
    st.markdown(
        """
        <div class="cartao-metrica">
            <div class="cartao-titulo">""" + titulo + """</div>
            <div class="cartao-valor">""" + valor + """</div>
            <div class="cartao-detalhe">""" + detalhe + """</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def exibir_memoria_terminal(dados_memoria):
    if "erro" in dados_memoria:
        print(dados_memoria["erro"])
        return

    print("=== Memória geral do sistema ===")
    print("Memória total:", dados_memoria["memoria_total_gb"], "GB")
    print("Memória disponível:", dados_memoria["memoria_disponivel_gb"], "GB")
    print("Memória usada:", dados_memoria["memoria_usada_gb"], "GB")
    print("Uso de memória:", str(dados_memoria["percentual_uso"]) + "%")


def exibir_cabecalho():
    st.markdown(
        """
        <div class="titulo-principal">Gerenciador de Memória</div>
        <div class="subtitulo-principal">
            Monitoramento automático da memória RAM com Python.<br>
            Feito por Alexsandro Narducci e Lucas Cândido Belletti.
        </div>
        """,
        unsafe_allow_html=True
    )


def exibir_status_atualizacao(horario_atualizacao):
    st.caption(
        "Atualização automática a cada 2 segundos | Última atualização: "
        + horario_atualizacao
    )


def exibir_aba_resumo(dados_memoria, tabela_aplicativos, horario_atualizacao):
    exibir_status_atualizacao(horario_atualizacao)

    st.markdown('<div class="secao"></div>', unsafe_allow_html=True)
    st.subheader("Visão geral da memória")

    coluna1, coluna2, coluna3, coluna4 = st.columns(4)

    with coluna1:
        exibir_cartao_metrica(
            "Memória total",
            str(dados_memoria["memoria_total_gb"]) + " GB",
            "Capacidade física detectada"
        )

    with coluna2:
        exibir_cartao_metrica(
            "Memória usada",
            str(dados_memoria["memoria_usada_gb"]) + " GB",
            "RAM ocupada no momento"
        )

    with coluna3:
        exibir_cartao_metrica(
            "Memória disponível",
            str(dados_memoria["memoria_disponivel_gb"]) + " GB",
            "RAM livre para uso"
        )

    with coluna4:
        exibir_cartao_metrica(
            "Uso da memória",
            str(dados_memoria["percentual_uso"]) + "%",
            "Percentual geral de uso"
        )

    st.markdown("#### Uso atual da RAM")

    percentual_barra = dados_memoria["percentual_uso"] / 100
    st.progress(percentual_barra)

    st.markdown(
        '<div class="texto-ajuda">A barra mostra o percentual atual de uso da memória física do sistema.</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="secao"></div>', unsafe_allow_html=True)
    st.subheader("Top 5 aplicativos no momento")

    if len(tabela_aplicativos) == 0:
        st.warning("Não foi possível listar os aplicativos.")
        return

    resumo_aplicativos = tabela_aplicativos.head(5)[
        [
            "Aplicativo",
            "Executável",
            "Tipo",
            "Quantidade de processos",
            "Memória (MB)"
        ]
    ]

    resumo_aplicativos = ajustar_indice_tabela(resumo_aplicativos)

    st.dataframe(
        resumo_aplicativos,
        use_container_width=True,
        height=230,
        column_config={
            "Memória (MB)": st.column_config.NumberColumn(
                "Memória (MB)",
                format="%.2f MB"
            )
        }
    )


def exibir_aba_graficos(tabela_aplicativos, horario_atualizacao):
    exibir_status_atualizacao(horario_atualizacao)

    st.subheader("Gráficos de uso de memória")

    st.markdown(
        """
        <div class="texto-ajuda">
            Esta aba mostra o histórico de uso da RAM e os aplicativos que mais usam memória.
            O histórico é mantido apenas durante a sessão atual do Streamlit.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("#### Histórico da memória RAM")
    exibir_grafico_historico_memoria()

    st.markdown('<div class="secao"></div>', unsafe_allow_html=True)
    st.markdown("#### Aplicativos")

    coluna_grafico1, coluna_grafico2 = st.columns([1, 3])

    with coluna_grafico1:
        limite_grafico_processos = st.selectbox(
            "Aplicativos no gráfico:",
            [5, 10],
            key="limite_grafico_aplicativos"
        )

    with coluna_grafico2:
        st.markdown(
            """
            <div class="texto-ajuda">
                O gráfico de barras mostra o uso atual.
                O gráfico de linha mostra a evolução histórica dos aplicativos com maior uso de memória.
            </div>
            """,
            unsafe_allow_html=True
        )

    if len(tabela_aplicativos) > 0:
        exibir_grafico_uso_atual_aplicativos(
            tabela_aplicativos,
            limite_grafico_processos
        )

        exibir_grafico_historico_processos(limite_grafico_processos)
    else:
        st.warning("Não foi possível montar os gráficos dos aplicativos.")


def exibir_aba_tabela(tabela_aplicativos, tabela_processos, horario_atualizacao):
    exibir_status_atualizacao(horario_atualizacao)

    st.subheader("Aplicativos e processos")

    st.markdown(
        """
        <div class="texto-ajuda">
            A tabela pode mostrar os aplicativos agrupados por executável ou os processos individuais.
            Os controles abaixo ajudam a filtrar e ordenar sem depender do clique no cabeçalho da tabela.
        </div>
        """,
        unsafe_allow_html=True
    )

    if len(tabela_processos) == 0:
        st.warning("Nenhum processo foi encontrado ou não foi possível coletar os dados.")
        return

    coluna1, coluna2, coluna3, coluna4 = st.columns(4)

    with coluna1:
        visualizacao = st.selectbox(
            "Visualização:",
            ["Aplicativos agrupados", "Processos individuais"],
            key="visualizacao_tabela"
        )

    with coluna2:
        filtro_tipo = st.selectbox(
            "Tipo:",
            ["Todos", "Sistema", "Usuário"],
            key="filtro_tipo_tabela"
        )

    with coluna3:
        ordenacao = st.selectbox(
            "Ordenação:",
            [
                "Maior uso de memória",
                "Menor uso de memória",
                "Tipo e maior uso de memória",
                "Nome"
            ],
            key="ordenacao_tabela"
        )

    with coluna4:
        quantidade = st.selectbox(
            "Quantidade:",
            [10, 20, 50, "Todos"],
            key="quantidade_tabela"
        )

    if visualizacao == "Aplicativos agrupados":
        tabela_base = tabela_aplicativos
    else:
        tabela_base = tabela_processos

    tabela_exibida = preparar_tabela_exibicao(
        tabela_base,
        filtro_tipo,
        ordenacao,
        quantidade
    )

    if len(tabela_exibida) == 0:
        st.warning("Nenhum item encontrado com os filtros selecionados.")
        return

    tabela_exibida = ajustar_indice_tabela(tabela_exibida)

    column_config = {
        "Memória (MB)": st.column_config.NumberColumn(
            "Memória (MB)",
            format="%.2f MB"
        ),
        "PIDs": st.column_config.TextColumn(
            "PIDs",
            help="Lista de PIDs agrupados"
        )
    }

    st.dataframe(
        tabela_exibida,
        use_container_width=True,
        height=500,
        column_config=column_config
    )

    st.markdown(
        """
        <div class="texto-ajuda">
            Observação: alguns processos protegidos do Windows podem aparecer com 0 MB porque o sistema bloqueia a leitura da memória desses processos.
        </div>
        """,
        unsafe_allow_html=True
    )


def exibir_aba_sobre(horario_atualizacao):
    exibir_status_atualizacao(horario_atualizacao)

    st.subheader("Sobre o projeto")

    st.write(
        "Este projeto é um Gerenciador de Memória acadêmico feito em Python, desenvolvido para o trabalho final da disciplina de Sistemas Operacionais do professor Danton Cavalcanti Franco Junior. "
        "Ele funciona como um dashboard simples inspirado no Gerenciador de Tarefas do Windows com foco no uso de memória RAM."
    )

    st.markdown("#### Tecnologias utilizadas")

    st.write(
        "- Python 3.12\n"
        "- ctypes / WinAPI\n"
        "- Streamlit\n"
        "- pandas\n"
        "- Plotly"
    )

    st.markdown("#### Coleta dos dados")

    st.write(
        "A coleta dos dados do sistema é feita com ctypes acessando diretamente funções da WinAPI, a API do Windows que tem acesso ao sistema através de chamadas nativas / System Calls. "
    )

    st.markdown("#### Atualização automática")

    st.write(
        "O dashboard usa atualização automática fixa a cada 2 segundos com o st.fragment. "
    )

    st.markdown("#### Funcionalidades principais")

    st.write(
        "- Exibição da memória total, usada, disponível e percentual de uso.\n"
        "- Listagem de processos com PID, nome e uso de memória.\n"
        "- Agrupamento de processos por executável.\n"
        "- Classificação simples/aproximada entre Sistema e Usuário.\n"
        "- Gráficos históricos de uso da RAM e dos aplicativos.\n"
        "- Tabela com filtros, ordenação e escolha de quantidade."
    )

    st.markdown("#### Observações")

    st.write(
        "O projeto foi pensado para Windows 11."
        "Também é normal que alguns processos protegidos do Windows apareçam com 0 MB, pois o sistema pode bloquear o acesso a eles."
    )


@st.fragment(run_every="2s")
def exibir_monitoramento_automatico():
    horario_atualizacao = obter_horario_atualizacao()

    dados_memoria = coletar_memoria_geral()

    if "erro" in dados_memoria:
        st.error(dados_memoria["erro"])
        return

    processos = coletar_processos()
    tabela_processos = preparar_tabela_processos(processos)
    tabela_aplicativos = agrupar_processos_por_aplicativo(tabela_processos)

    if deve_registrar_medicao(horario_atualizacao):
        atualizar_historico_memoria(dados_memoria, horario_atualizacao)

        if len(tabela_aplicativos) > 0:
            atualizar_historico_processos(tabela_aplicativos, horario_atualizacao)

        marcar_medicao_registrada(horario_atualizacao)

    aba_resumo, aba_graficos, aba_tabela, aba_sobre = st.tabs(
        [
            "Resumo",
            "Gráficos",
            "Aplicativos e processos",
            "Sobre"
        ]
    )

    with aba_resumo:
        exibir_aba_resumo(dados_memoria, tabela_aplicativos, horario_atualizacao)

    with aba_graficos:
        exibir_aba_graficos(tabela_aplicativos, horario_atualizacao)

    with aba_tabela:
        exibir_aba_tabela(tabela_aplicativos, tabela_processos, horario_atualizacao)

    with aba_sobre:
        exibir_aba_sobre(horario_atualizacao)


def exibir_dashboard():
    inicializar_estado_interface()
    aplicar_estilo_visual()
    exibir_cabecalho()
    exibir_monitoramento_automatico()


def main():
    configurar_pagina()
    exibir_dashboard()


if __name__ == "__main__":
    main()