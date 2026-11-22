# Desafio 01 — instrução de pedidos de diárias

Aplicação local que prepara instrução estruturada e minuta editável para conferência humana. O agente não defere, indefere nem autoriza despesa. A decisão final cabe ao ordenador.

## Instalação e execução (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Configure OPENAI_API_KEY localmente; não compartilhe o arquivo.
python -m pip check
python -m unittest discover -s testes -v
python avaliacao.py --repeticoes 3
python avaliacao.py --live --repeticoes 3
python experimento_memoria.py --live
streamlit run app.py
```

A avaliação offline não chama o modelo. Opções `--live` exigem chave e acesso à API. Os dados de `exemplos/dados/` são preservados; o gerador não deve ser executado sobre o acervo fornecido.

## Arquitetura

- Agno 3.0.9, modelo `gpt-5.6-luna`, schema Pydantic `Instrucao`, limite de seis chamadas de ferramenta, telemetria e debug desligados.
- As quatro ferramentas são chamadas pelo agente. Guardas validam argumentos e impõem as dependências: cadastro antes de histórico e cálculo; cálculo antes do saldo.
- A aplicação compara a proposta do modelo com fatos determinísticos e só exibe a proposta original se ela passar pelas barreiras. Não usa gabarito e não substitui proposta recusada por fallback.
- CPF, e-mail e dados bancários são minimizados. Identidade divergente bloqueia envio e memória para o titular potencialmente incorreto.
- O paralelismo fica desligado por padrão devido à ordem de negócio; o benchmark final mediu os dois modos sem erros.
- A interface permite analisar, complementar diligência, editar minuta, registrar conferência humana e eliminar memória.

## Resultados finais

Em 22/11/2026 foram medidos 84 casos: 12 pedidos e duas complementações, três rodadas, dois modos. Seis divergências de identidade foram bloqueadas antes do modelo. As outras 78 propostas tiveram aceitação integral e acerto exato contra o gabarito (39/39 em cada modo).

Paralelismo desligado: mediana de cinco chamadas de modelo, 12.419 tokens, US$ 0,002992 e 7,00 s. Ligado: quatro chamadas, 10.055 tokens, US$ 0,0025352 e 5,96 s. Os dois modos invocaram quatro ferramentas por caso completo e tiveram 100% de acerto. A diferença de custo e tempo é observacional, sem inferência causal. Custos estimados usam preços de referência do exercício e não são valores de fatura. Consulte `relatorio.md` e os arquivos `resultados/`.

No ensaio de memória, histórico limitado recuperou a diligência 0111 no segundo turno e validou a complementação. Memória de usuário não acrescentou recuperação e elevou custo. O caso 0112 foi corrigido sem enviar identidade divergente ao modelo. Os bancos temporários foram verificados e removidos.

## Memória, retenção e privacidade

O banco de trabalho `memoria_diarias.sqlite` é o `SqliteDb` do Agno. Ele pode persistir o histórico da sessão (entradas, saídas, mensagens de ferramenta e resultados associados) e, somente quando `update_memory_on_run=True` for habilitado, memórias do usuário. O agente também precisa conservar no contexto operacional o identificador do pedido, a matrícula confirmada e fatos cadastrais/de cálculo; justificativas e minutas são minimizadas antes do modelo, mas os registros do Agno ainda podem conter dados funcionais e do processo. CPF, e-mail e dados bancários são mascarados antes do envio ao modelo.

O `session_id` é o número do pedido e o `user_id` é a matrícula confirmada. A aplicação limita o histórico de contexto a quatro execuções (`num_history_runs=4`); esse limite de contexto não substitui a retenção dos registros armazenados.

A retenção da cópia de trabalho é de **30 dias por padrão**, configurável pela variável `RETENCAO_MEMORIA_DIAS` no `.env`. Se ausente, `configuracao.py` usa 30. O expurgo considera sessões sem atualização dentro do prazo e memórias de usuário antigas; a aplicação o executa ao inicializar os recursos SQLite na primeira carga do processo. A rotina verifica diretamente as tabelas e não declara sucesso se houver erro ou resíduo vencido. O titular deve solicitar a eliminação pelo canal administrativo que a instituição vier a definir; esse canal e a autorização do operador ainda não são implementados pelo exercício. O operador autorizado pode então informar o número do pedido na aba **Eliminar memória**. A rotina remove todas as sessões e memórias vinculadas à matrícula confirmada do titular; no caso 0112, limita a matrícula inicialmente digitada aos dados do pedido para preservar dados não relacionados de terceiro. Verifica o banco antes de confirmar. Esse mecanismo cobre somente o banco de trabalho do agente; não elimina nem substitui o processo oficial.

O registro de conferência humana fica em `resultados/conferencias.jsonl`, arquivo separado do SQLite. Cada linha pode conter o identificador do pedido, recomendação do agente, encaminhamento humano, concordância/divergência, justificativa da divergência, minuta final editada e horário UTC. Justificativa e minuta passam pela máscara de PII, mas continuam sendo registros administrativos relevantes. O arquivo fica no diretório local do projeto; o acesso atual é controlado somente pelas permissões do sistema de arquivos, pois o Streamlit não implementa autenticação ou perfis de acesso. `.gitignore` impede sua inclusão acidental no Git, mas não controla cópias de segurança ou acesso ao computador. **Não há prazo de guarda nem rotina de exclusão definidos para esse arquivo no projeto.** A política institucional de retenção, acesso, arquivo e eliminação é uma pendência antes de uso real; os 30 dias do SQLite não se aplicam ao JSONL. A aba de eliminação de memória não toca nesse arquivo. A unidade deverá autorizar e estabelecer o procedimento de exclusão/guarda conforme a classificação administrativa do registro; o aplicativo não implementa essa autorização nem autenticação de titular.

No experimento de memória, o primeiro turno do caso 0112 aparece como `bloqueado_antes_do_modelo`: chamadas, tokens e custo do modelo são zero. O pedido não foi executado sob a matrícula divergente. O turno seguinte confirmou a matrícula corrigida e aplicou a complementação; esse envio conjunto não conta como recuperação do histórico.

São 40 testes aprovados; `pip check` limpo; 42/42 casos offline. Os testes controlados exercitam o loop real do Agno com modelo stubado, incluindo a apresentação explícita de custo zero nos bloqueios pré-modelo e a separação do JSONL de conferência, mas não simulam falha HTTP real. A interface passou AppTest; não houve captura de navegador. O conjunto do desafio não representa produção.

## Entradas e gabarito

O acervo fornecido permanece em `exemplos/dados/`. `agente.py` e a interface não importam nem consultam `exemplos/gabarito.json`; apenas `avaliacao.py` o lê após cada execução para pontuar resultados. O gabarito é referência de avaliação, nunca contexto do agente.


### Decisao institucional pendente para conferencias

Registro formal da pendencia e campos para aprovacao: `resultados/pendencia_politica_conferencias.md`.


Antes de habilitar dados reais, a unidade responsavel deve registrar: finalidade e classificacao do registro; responsavel custodiante; perfis autorizados para leitura, exportacao e exclusao; prazo de guarda; eventos que iniciam a contagem; destino de arquivo; procedimento, autorizacao e evidencias de descarte; tratamento de copias de seguranca. Nenhum prazo foi presumido nem configurado para `resultados/conferencias.jsonl`. Ate a decisao formal, use somente o acervo hipotetico. O arquivo e local e herda as permissoes do sistema operacional; o Streamlit nao tem autenticacao/perfis, e `.gitignore` nao protege acesso local nem backups. A limpeza do SQLite nao elimina o JSONL.
