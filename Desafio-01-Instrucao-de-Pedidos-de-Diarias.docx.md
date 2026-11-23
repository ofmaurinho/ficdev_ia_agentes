**Desafio 01 - Instrução de Pedidos de Diárias**

**Conteúdos:** Aulas de 01 à 07

**Duração:** 2 dias

**Modalidade:** individual

# Problema

A Coordenadoria de Diárias e Passagens da Secretaria de Estado de Meio Ambiente de Mato Grosso (SEMA-MT) recebe, todo mês, centenas de pedidos de diárias de fiscais, analistas e motoristas que se deslocam ao interior. Cada pedido é instruído por um servidor que consulta o cadastro funcional, o histórico de diárias e de prestações de contas, a tabela de valores e o saldo da dotação da unidade. Só depois dessa conferência o processo segue ao ordenador de despesa, que defere ou indefere.

Os erros desse trabalho raramente aparecem no dia em que são cometidos. Uma diária concedida a quem tem prestação de contas vencida ou um pedido urgente aceito sem a autorização escrita exigida pela norma costumam ser descobertos meses depois, na auditoria. Além disso, muitos pedidos chegam incompletos, voltam ao solicitante em diligência e retornam com a complementação, quando o servidor precisa reconstituir o caso desde o começo.

A pergunta que este desafio responde é se um único agente construído com o Agno, o framework das Aulas 06 e 07, consegue instruir esses pedidos de ponta a ponta, deixando a decisão a quem assina. A resposta exige reunir o que as sete primeiras aulas ensinaram: a aritmética dos passos, ferramentas, saída estruturada, barreiras de verificação, memória com eliminação verificável e um formulário de conferência. O processo foi escolhido porque é regido por regras escritas, repete-se em grande volume e depende de várias fontes, condições em que um agente ajuda sem decidir no lugar de ninguém.

# Objetivos

- Integrar em um único agente Agno as ferramentas, a saída estruturada, os limites de execução, o filtro de dados pessoais e a memória persistente estudados nas Aulas 01 a 07
- Especificar o processo pelo quadro PEAS (medida de desempenho, ambiente, atuadores e sensores) e estimar, antes de qualquer código, sua confiabilidade composta e do número de passos
- Escrever ferramentas sobre os dados do órgão com docstring que funcione como especificação, testando-as sem modelo
- Implementar e verificar a rotina de eliminação dos dados do servidor guardados pelo agente
- Medir o agente contra um gabarito, em acertos, *tokens* (as unidades de texto que o provedor cobra), tempo e custo, e provocar seus modos de falha
- Entregar o agente ao servidor em um formulário, com o ponto de conferência humana justificado por medição

# O que Você Vai Construir

O sistema recebe um pedido de diárias como foi protocolado e devolve a instrução pronta para conferência: as verificações exigidas pela norma, a quantidade e o valor das diárias, a recomendação e a minuta do despacho. O agente consulta os dados do órgão por meio de quatro ferramentas e responde em um objeto validado, que o formulário desenha campo a campo. Quando o pedido volta em diligência, a complementação é enviada na mesma sessão, e o agente recupera o caso pela memória.

*Figura 1: Fluxo do pedido de diárias, das ferramentas e da memória. Observe que a instrução passa por uma barreira no código antes de chegar ao formulário, e que a decisão final permanece com o ordenador de despesa.*

A recomendação tem três valores. **Apto para autorização** significa que todos os critérios foram atendidos; **não recomendado** significa que há impedimento, como antecedência insuficiente, prestação vencida, limite mensal excedido ou falta de saldo; **diligência** significa que o pedido está incompleto ou diverge do cadastro. Em nenhum caso o agente decide, porque a decisão pertence ao ordenador.

# Requisitos

Este desafio integra o conteúdo das sete primeiras aulas do módulo. Vale rever, antes de começar:

| **Assunto** | **Onde foi estudado** |
| --- | --- |
| Quadro PEAS, confiabilidade composta, custo por passos e níveis de autonomia | Aula 01 |
| Saída estruturada com esquema declarado | Aula 02 |
| Ferramentas, critério de acerto, custo da cauda e modos de falha | Aula 03 |
| Erro que atravessa a cadeia e ancoragem numérica | Aula 04 |
| Conferência humana como etapa do fluxo | Aula 05 |
| Agente no Agno, docstring, chamadas paralelas, filtro de dados pessoais, erro devolvido pela interface de programação (API, *Application Programming Interface*) e formulário | Aula 06 |
| Histórico da sessão, identificadores, custo da memória e eliminação de dados | Aula 07 |

**Ambiente sugerido:** Python 3.10 ou superior, com Agno 3.0.9, openai, python-dotenv, pydantic, streamlit e sqlalchemy\[asyncio]. A chave OPENAI_API_KEY fica no .env da raiz do repositório, lido com load_dotenv, e nunca aparece no código, no relatório nem na tela. O modelo de referência é o gpt-5.6-luna, o nível de menor custo da família GPT-5.6.

pip install agno openai python-dotenv pydantic streamlit "sqlalchemy\[asyncio]"

**Atenção:** a série 2.1 do sqlalchemy não instala o pacote greenlet, de que o SqliteDb do Agno depende, e a importação falha com "The SQLAlchemy asyncio module requires that the Python 'greenlet' library is installed". O alvo sqlalchemy\[asyncio] traz a dependência.

# O Acervo de Entrada

O material de partida está em exemplos/dados/ e é gerado, com semente fixa, pelo script gerar_dados.py. Todos os dados são **hipotéticos**: servidores, matrículas, saldos, valores e a própria Instrução Normativa (IN) SEMA nº 07/2026 foram inventados para o exercício. Os números de Cadastro de Pessoas Físicas (CPF) têm dígitos verificadores inválidos de propósito, para que nenhum coincida com o de uma pessoa real. Para regenerar o acervo, execute:

cd Modulo-Agentes-Autonomos/arquivos/desafio-01\
python3 gerar_dados.py

Os dados ficam em formatos que um sistema real exportaria:

| **Arquivo** | **Conteúdo** |
| --- | --- |
| normas.md | A IN hipotética, com as regras e os valores da diária |
| servidores.csv | Cadastro funcional de quarenta servidores, com CPF |
| historico_diarias.csv | Diárias concedidas e situação das prestações de contas |
| tabela_diarias.json | Valores por grupo e destino, regras numéricas e data da análise |
| unidades.json | Unidades de lotação e saldo de cada uma |
| pedidos.json | Os doze pedidos a instruir |
| complementacoes.json | Duas respostas a pedidos devolvidos em diligência |

Cada um dos doze pedidos exercita uma decisão diferente:

| **Pedido** | **O que exercita** |
| --- | --- |
| DIA-2026-0101 | Pedido regular, com todos os dados |
| DIA-2026-0102 | Prestação de contas pendente: distinguir a vencida da que ainda está no prazo |
| DIA-2026-0103 | Ida e volta no mesmo dia: regra da meia diária |
| DIA-2026-0104 | Viagem ao Distrito Federal, com CPF e conta bancária colados na justificativa |
| DIA-2026-0105 | Antecedência menor que a mínima, sem urgência |
| DIA-2026-0106 | Antecedência menor que a mínima, com urgência legítima |
| DIA-2026-0107 | Ordem dirigida ao "sistema de análise" escrita na justificativa |
| DIA-2026-0108 | Prestação de contas vencida |
| DIA-2026-0109 | Diárias do mês somadas às pedidas acima do limite |
| DIA-2026-0110 | Viagem a outra unidade da federação (UF), com saldo insuficiente na unidade |
| DIA-2026-0111 | Data de retorno ausente, complementada depois |
| DIA-2026-0112 | Matrícula de outro servidor, por troca de dois algarismos, corrigida depois |

O arquivo gabarito.json traz a resposta esperada para os doze pedidos e as duas complementações. Ele foi calculado pelo gerar_dados.py, que aplica a norma por código, sem modelo algum. O gabarito não deve ser entregue ao agente, porque um agente que lê a resposta esperada não está sendo medido.

**Atenção:** os pedidos DIA-2026-0106 e DIA-2026-0107 têm, ambos, antecedência menor que dez dias. O primeiro descreve um incêndio florestal em curso, que a norma aceita como urgência mediante autorização escrita; o segundo alega autorização verbal e ordena ao sistema que marque o pedido como apto. Um agente que trata os dois da mesma forma está errado.

# Etapas

## Etapa 1 - Desenho do processo e quadro PEAS

Antes de escrever código, descreva o processo como o servidor o executa hoje, em etapas numeradas, e como o agente o executará. Especifique o agente pelo quadro PEAS da Aula 01, sigla de *Performance, Environment, Actuators, Sensors*, que reúne medida de desempenho, ambiente, atuadores e sensores. A medida de desempenho deve ser verificável contra o gabarito, porque é ela que a Etapa 6 mede.

Conte os passos do agente, considerando cada chamada ao modelo como um passo, e aplique a tabela de confiabilidade composta da Aula 01 com 95% e 99% por passo. Para o custo, estime a entrada da primeira chamada, que reúne instrução, esquemas das ferramentas, esquema da saída e pedido, e some o que cada passo acrescenta. Na execução de referência, a primeira chamada consumiu cerca de 2.060 *tokens* e cada passo seguinte acrescentou de 90 a 150, e a estimativa para cinco passos ficou a menos de 3% do medido.

Por fim, posicione o processo na grade de reversibilidade e tempo de detecção da Aula 01, Seção 5. Uma diária paga indevidamente pode ser devolvida, mas o erro costuma ser percebido apenas na auditoria, o que coloca o processo no quadrante em que o agente não age sozinho. Registre em desenho.md o processo, o quadro PEAS, as duas contas, o volume mensal adotado e o quadrante.

## Etapa 2 - Ferramentas sobre os dados do órgão

Escreva de três a quatro ferramentas como funções Python comuns, cada uma substituindo uma consulta que o servidor faz à mão, como cadastro, histórico do mês, cálculo das diárias e saldo da unidade. A docstring precisa dizer quando usar a ferramenta, o que ela devolve e em que formato espera os argumentos, conforme a Aula 06, Seção 5.1. Ela é a única parte da função que o modelo lê.

Duas regras de projeto orientam a etapa. A primeira é a **minimização**: o cadastro tem CPF e e-mail, que a instrução não usa, e a ferramenta não deve devolvê-los ao modelo. A segunda é que **as contas ficam no código**, porque a aritmética é onde o modelo erra com segurança, de modo que antecedência, quantidade, saldo do mês e comparação com o saldo da unidade saem prontos. A ferramenta do saldo, por exemplo:

**def** consultar_saldo_diarias(unidade: str, valor: float) -> str:\
"""Consulta o saldo da dotação de diárias de uma unidade e o compara com o valor pedido.\

Use depois de calcular o valor total das diárias. \`unidade\` é a sigla da\
unidade de lotação devolvida pelo cadastro, como CFF ou GAB; \`valor` é o\
total em reais, com ponto decimal, como 980.0. Devolve o saldo disponível e\
a indicação de saldo suficiente ou insuficiente para o pedido.\
"""\
sigla = unidade.strip().upper()\
**if** sigla **not in** UNIDADES:\
**return** f"Unidade '{unidade}' não localizada. Siglas válidas: {', '.join(UNIDADES)}."\
saldo = UNIDADES\[sigla]\["saldo_diarias"]\
situacao = "suficiente" **if** saldo >= float(valor) **else** "INSUFICIENTE"\
**return** f"Saldo da unidade {sigla}: R$ {saldo:.2f}. Saldo {situacao} para R$ {valor:.2f} (art. 8º)."

Teste cada ferramenta sem agente e sem chave, como o ferramentas_comuns.py da Aula 06, com casos dos próprios pedidos: a matrícula trocada do DIA-2026-0112, a prestação vencida do DIA-2026-0108, a meia diária do DIA-2026-0103 e o saldo do DIA-2026-0110. Um erro dentro da função aparece depois como resposta estranha do agente, difícil de localizar. Guarde a saída do teste como evidência de que as contas estão certas antes de o modelo entrar.

## Etapa 3 - Agente com saída estruturada, limites e filtro

Monte o agente com output_schema, declarando uma classe Pydantic que a tela e a medição leiam sem interpretar texto. O contrato mínimo tem os campos abaixo, e cada campo acrescentado deve existir porque alguém precisa lê-lo:

**class Verificacao**(BaseModel):\
criterio: Literal\["cadastro", "dados_completos", "antecedencia", "prestacao_contas",\
"limite_mensal", "saldo_orcamentario"]\
situacao: Literal\["atende", "nao_atende", "nao_verificado"]\
detalhe: str            *# o dado que fundamenta a situação, como veio da ferramenta*\


**class Instrucao**(BaseModel):\
numero_pedido: str\
matricula: str\
quantidade_diarias: Optional\[float]   *# nulo na diligência*\
valor_total: Optional\[float]          *# nulo na diligência*\
verificacoes: list\[Verificacao]\
recomendacao: Literal\["apto_para_autorizacao", "diligencia", "nao_recomendado"]\
exige_autorizacao_superior: bool\
pendencias: list\[str]   *# o que o solicitante precisa corrigir*\
alertas: list\[str]      *# ordens embutidas, dados mascarados, o que o conferente precisa ver*\
minuta_despacho: str

A instrução de sistema contém as regras da norma, a ordem das consultas e a proibição de calcular com dados supostos. Configure tool_call_limit, telemetry=False e reasoning_effort="none", exigido pela família GPT-5.6 quando há ferramentas, e decida se as chamadas paralelas ficam ligadas. A decisão considera a Aula 06, Seção 4.3, porque o cálculo depende do grupo que vem do cadastro e o saldo depende do valor calculado.

Configure o PIIDetectionGuardrail com os padrões norte-americanos desligados, um para o CPF(não verifique se o CPF é válido, mas sim máscara válida) e outro para conta e agência bancária. A configuração está certa quando o CPF do DIA-2026-0104 não chega ao modelo nem ao banco, e nenhuma matrícula, data ou número de pedido é mascarado. Confira também resposta.status antes de usar o conteúdo, como na Aula 06, Seção 5.3, para que um erro da API nunca seja tratado como instrução.

**Atenção:** a barreira pertence ao código, e não ao *prompt*, o texto de instruções enviado ao modelo, conforme a Aula 01. Escreva uma verificação que confira os argumentos das ferramentas contra o pedido que a aplicação tem em mãos: toda matrícula consultada e toda data usada no cálculo precisam constar do pedido ou da complementação. A Etapa 4 mostra quando essa verificação passa a ser a única defesa.

## Etapa 4 - Memória, custo por turno e eliminação

Ligue a memória com SqliteDb, add_history_to_context e um teto em num_history_runs, tratando cada pedido como uma sessão. O session_id é o número do pedido, e o user_id é a matrícula do solicitante, nunca a sigla da unidade. Informe os dois em cada chamada a run, e não na construção do agente, o que permite manter um único agente em cache no formulário sem misturar pedidos.

Meça o custo da memória com as duas complementações, em três configurações: sem memória, com o histórico da sessão e com o histórico acrescido das memórias do usuário (update_memory_on_run). Registre a entrada do primeiro turno, a do turno da complementação e se ela foi aplicada ao pedido certo.

Implemente a rotina de eliminação e teste-a com as duas servidoras que passaram por diligência. A rotina apaga as sessões do titular, que levam junto as execuções, lista e apaga as memórias com delete_user_memories e confere o banco tabela por tabela, procurando matrícula e nome. O pedido DIA-2026-0112 mostra por que a conferência é obrigatória: a matrícula digitada pertence a outro servidor, a sessão fica gravada sob o identificador dele, e a busca pelo user_id da titular não a encontra.

A rotina alcança somente o banco do agente, que é cópia de trabalho. O processo de diárias é o registro de despesa pública, sujeito à transparência e à guarda das normas de prestação de contas, e a Lei Geral de Proteção de Dados Pessoais (LGPD).

**Etapa 5 - Formulário de conferência**

Entregue o agente em uma aplicação Streamlit no padrão de formulário descrito na aula 06.

A tela mostra a recomendação, as verificações com o fundamento de cada uma, os alertas, as pendências e as consultas com os argumentos. A minuta do despacho fica em campo editável, e o servidor registra o encaminhamento que decidiu ao lado do que o agente sugeriu, com o motivo quando divergirem. Esse registro é o lugar físico da conferência humana e permitirá medir, com o uso, com que frequência o servidor discorda do agente.

Na diligência, a tela oferece um campo para a complementação, enviada na mesma sessão do pedido, e, em área separada, aciona a rotina de eliminação e mostra o que restou no banco. Se a execução falhar ou a verificação de argumentos recusar a instrução, a tela exibe uma mensagem padrão e devolve o pedido à análise manual. Nada do conteúdo recusado aparece ao servidor.

# Entregáveis

Ao final, entregue um repositório ou pasta compactada contendo:

| **Item** | **Descrição** |
| --- | --- |
| desenho.md | Processo, quadro PEAS, confiabilidade composta, custo por passos e quadrante de autonomia da Etapa 1 |
| Código-fonte | Ferramentas com teste sem agente, agente, scripts de memória e de medição e aplicação Streamlit, com .env.example e sem chave versionada |
| resultados/ | Saídas das medições das Etapas 4 e 5, em arquivo |
| relatorio.md | Números medidos, modos de falha provocados e decisão sobre o ponto de conferência humana |
| LEIA-ME.md | Como executar o sistema, decisões técnicas tomadas e suas justificativas |

No LEIA-ME.md, responda a quatro perguntas:

1. Que configuração de chamadas paralelas, teto de chamadas e memória você escolheu, e com base em que número?
2. Como o sistema impede que uma instrução fundamentada em dado inventado chegue ao conferente?
3. Que dados do servidor o agente guarda, por quanto tempo, e como o titular os elimina?

# Critérios de Avaliação

A avaliação recai sobre os arquivos gerados e as medições, e não sobre a elegância do código:

| **Critério** | **O que se observa** |
| --- | --- |
| **Funcionamento de ponta a ponta** | Instrui os doze pedidos e as duas complementações sem intervenção manual e sem quebrar |
| **Ferramentas e agente** | Docstrings completas, contas no código, contrato Pydantic, limites, filtro configurado e verificação de status |
| **Memória e eliminação** | Identificadores corretos, custo por turno medido e rotina que comprova, no banco, que nada restou |
| **Medição e falhas** | Três rodadas contra o gabarito, comparação das chamadas paralelas e quatro falhas provocadas com honestidade |
| **Formulário de conferência** | Progresso visível, despacho editável, decisão do conferente registrada e mensagem padrão no erro |
| **Desenho e relatório** | Aritmética da Etapa 1 confrontada com o medido e ponto de conferência humana justificado |

# O que mais pesa negativamente: uma instrução que chega ao conferente fundamentada em dado que não veio do pedido nem das ferramentas. Um agente que acerta onze casos e recusa três com a mensagem padrão vale mais que um que acerta treze e entrega o décimo quarto calculado para o servidor errado, porque o primeiro erra de forma visível.
