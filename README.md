# Gerenciador de Memória do Windows em Python.
# Feito por Alexsandro Narducci e Lucas Cândido Belletti

Projeto acadêmico em Python para o trabalho final da disciplina de Sistemas Operacionais, com o professor [Danton Cavalcanti Franco Junior](https://github.com/dantonjr).
Consiste em um dashboard inspirado no Gerenciador de Tarefas do Windows, com foco no monitoramento do uso de memória RAM da máquina.

O sistema mostra informações gerais da memória, lista processos em execução com a quantidade de memória usada, agrupa por aplicativo/executável e exibe essas informações em tabelas e gráficos.

## Descrição geral

O projeto é uma versão simplificada do Gerenciador de Tarefas, mas com foco específico na memória do sistema.
As informações do sistema são coletadas com a biblioteca embutida do Python `ctypes`, que utiliza funções da winAPI em C para obter os dados da memória.
O foco maior foi entender essa coleta de informações da memória RAM e processos no Windows sem depender de bibliotecas de alto nível como o `psutil`, que simplificaria muito o projeto.

O dashboard é um painel feito com `Streamlit`, as tabelas utilizam a biblioteca `pandas` e os gráficos foram feitos através de `plotly`

## Objetivos do projeto
* demonstrar o uso de chamadas do sistema operacional com `ctypes` e WinAPI.
* monitorar a memória geral do sistema;
* mostrar os processos e aplicativos que mais usam memória;
* organizar os dados em tabelas;
* apresentar gráficos de uso atual e histórico;

## REQUISITOS PARA EXECUTAR 

Ambiente recomendado é Windows 11 e Python 3.12

As bibliotecas necessárias:
* streamlit
* pandas
* plotly

## INSTALAÇÃO

Para instalar todas de uma vez, use:

```bash
pip install streamlit pandas plotly
```

## COMO EXECUTAR O PROJETO

No terminal, dentro da pasta onde está o arquivo, execute:

```bash
streamlit run gerenciador_memoria.py
```
Depois disso, o Streamlit deve abrir o dashboard automaticamente no navegador.

Dependendo de como foi instalado o Streamlit, pode dar um conflito no PATH, se o comando acima não rodar o projeto, tente este:

```bash
python -m streamlit run gerenciador_memoria.py
```
## Coleta de dados do sistema operacional

Como dito anteriormente, os dados são acessados diretamente pela WinAPI usando `ctypes`.
O `ctypes` é uma biblioteca do Python que permite carregar DLLs do Windows e chamar funções nativas do sistema operacional. Neste projeto, são usadas principalmente funções das bibliotecas `kernel32` e `psapi`.

### Coleta de informações gerais da memória do sistema

Para coletar informações gerais da memória RAM, o projeto usa a estrutura `MEMORYSTATUSEX`.
Essa estrutura representa o formato esperado pela função `GlobalMemoryStatusEx`, que é uma função da WinAPI usada para obter dados de memória do sistema.
Com essa função, o projeto obtém a memória fisica total, a disponível e o percentual de uso.

A memória usada é calculada no próprio código, usando a diferença entre memória total e memória disponível.
Depois disso, os valores são convertidos de bytes para gigabites, para ficarem mais fáceis de entender no dashboard.

### Coleta dos processos pela WinAPI

Primeiro o projeto usa `CreateToolhelp32Snapshot` para criar uma captura dos processos em execução no momento. Essa captura funciona como uma lista temporária que pode ser percorrida pelo programa.
Depois são usadas as funções `Process32FirstW` e `Process32NextW` que percorrem os processos encontrados no snapshot.

As informações básicas de cada processo ficam na estrutura `PROCESSENTRY32`, que permite acessar dados como o PID, nome do executável e informações gerais do processo.

Depois de encontrar um processo, o projeto tenta acessá-lo com `OpenProcess`.
Quando o acesso é permitido, o projeto usa `GetProcessMemoryInfo` para consultar o uso de memória do processo. Essa função preenche a estrutura `PROCESS_MEMORY_COUNTERS`.
Dentro dessa estrutura, o campo mais importante usado no projeto é o `WorkingSetSize`.

O `WorkingSetSize` representa a quantidade de memória física atualmente associada ao processo. No dashboard, esse valor é convertido de bytes para megabytes.

### Fechamento de handles

Sempre que o projeto abre um processo com `OpenProcess` ou cria um snapshot com `CreateToolhelp32Snapshot`, ele precisa liberar esse recurso depois, por isso o código usa o `CloseHandle`.
Como os handles são recursos controlados pelo SO, se eles não forem fechados corretamente, o programa pode desperdiçar recursos do sistema.

### Limitações da coleta

Alguns processos do Windows são protegidos e não permitem leitura direta de informações por programas comuns.
Quando isso acontece, o erro é tratado e o uso de memória fica como `0 MB`.

Outra limitação é que a classificação entre `Sistema` e `Usuário` é simples e aproximada. Ela usa alguns nomes conhecidos de processos do Windows, mas não tenta fazer uma análise completa.
Comparamos lado a lado com o Gerenciador de tarefas do Windows e o número de próximos do Sistema/Usuario está bem próximo.

O agrupamento por aplicativo também é uma aproximação. Ele é feito pelo nome do executável, então vários processos `chrome.exe`, por exemplo, podem ser somados em um grupo chamado Google Chrome. Esse agrupamento não é exatamente igual ao funcionamento interno do Gerenciador de Tarefas do Windows, que é mais completo, mas já ajuda bastante na leitura dos dados.

## Funcionalidades

O projeto possui as seguintes funcionalidades:

* atualização automática fixa a cada 2 segundos;
* visão geral da memória RAM;
* exibição de memória total, usada, disponível e percentual de uso;
* listagem de processos em execução;
* visualização de aplicativos agrupados por executável;
* opção de visualizar processos individuais;
* classificação simples entre Sistema e Usuário;
* filtros por tipo;
* ordenação por memória, tipo ou nome;
* seleção de quantidade de itens exibidos;
* gráfico histórico do uso de RAM;
* gráfico de barras dos aplicativos com maior uso de memória no momento;
* gráfico histórico dos aplicativos com maior uso de memória;
* interface dividida em abas.

## Tecnologias utilizadas

* Python 3.12
* ctypes/WinAPI
* Streamlit
* pandas
* Plotly
* datetime

## Estrutura do código

O projeto foi mantido em um único arquivo Python, estruturado da seguinte maneira:

* constantes usadas para acessar a WinAPI;
* estruturas `MEMORYSTATUSEX`, `PROCESSENTRY32` e `PROCESS_MEMORY_COUNTERS`;
* configuração das funções nativas do Windows com `ctypes`;
* funções de conversão de bytes para GB e MB;
* função de coleta da memória geral;
* função de coleta dos processos;
* função para obter a memória usada por cada processo;
* função de classificação entre Sistema e Usuário;
* função de agrupamento por executável;
* funções para preparar tabelas com pandas;
* funções para atualizar históricos;
* funções para criar gráficos com Plotly;
* funções da interface com Streamlit;
* fragmento de atualização automática a cada 2 segundos.

## Observações e limitações

O projeto foi feito para Windows. Como ele usa WinAPI, não deve funcionar corretamente em Linux ou macOS.

Alguns processos podem aparecer com `0 MB` porque o Windows bloqueia o acesso a eles. Isso depende das permissões do usuário e das proteções do próprio sistema operacional.

O agrupamento é feito pelo nome do executável. Então processos com o mesmo executável são somados, mas processos com nomes de executáveis diferentes não são agrupados, o que pode deixar a listagem um pouco menos precisa, se comparado ao Gerenciador do Windows, que consegue agrupar bem todos os processos do mesmo programa. No nosso projeto, o mesmo programa pode ser repetir 2 vezes na listagem por ter processos com executáveis diferentes, como é o caso do Microsoft Edege por exemplo.

