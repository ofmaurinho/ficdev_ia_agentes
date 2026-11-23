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

Em 22/11/2026, a execucao final mediu 84 casos: 12 pedidos e duas complementacoes, tres rodadas em cada modo. Seis pedidos com identidade divergente foram bloqueados antes do modelo. As 78 propostas restantes passaram pelas barreiras e acertaram integralmente o gabarito (39/39 por modo), sem erros de execucao nem divergencia nos argumentos das ferramentas.

Paralelismo desligado: mediana de cinco chamadas ao modelo, 15.581 tokens totais, US$ 0,0036072 e 6,69 s. Ligado: quatro chamadas, 12.585 tokens, US$ 0,0030266 e 5,81 s. Os dois modos usaram quatro ferramentas por caso completo. A diferenca e observacional, sem inferencia causal. Custos usam precos de referencia do exercicio, nao sao valores de fatura. Metricas por caso estao em resultados/benchmark_live.json e .csv; veja relatorio.md.

A reexecucao limpa, os criterios conferidos e as acoes humanas pendentes estao documentados em resultados/reexecucao_limpa_20261122.md e resultados/ACAO_HUMANA_PENDENTE.md.

## Memória, retenção e privacidade

O banco de trabalho `memoria_diarias.sqlite` é o `SqliteDb` do Agno. Ele pode persistir o histórico da sessão (entradas, saídas, mensagens de ferramenta e resultados associados) e, somente quando `update_memory_on_run=True` for habilitado, memórias do usuário. O agente também precisa conservar no contexto operacional o identificador do pedido, a matrícula confirmada e fatos cadastrais/de cálculo; justificativas e minutas são minimizadas antes do modelo, mas os registros do Agno ainda podem conter dados funcionais e do processo. CPF, e-mail e dados bancários são mascarados antes do envio ao modelo.

O `session_id` é o número do pedido e o `user_id` é a matrícula confirmada. A aplicação limita o histórico de contexto a quatro execuções (`num_history_runs=4`); esse limite de contexto não substitui a retenção dos registros armazenados.

A retenção da cópia de trabalho é de **30 dias por padrão**, configurável pela variável `RETENCAO_MEMORIA_DIAS` no `.env`. Se ausente, `configuracao.py` usa 30. O expurgo considera sessões sem atualização dentro do prazo e memórias de usuário antigas; a aplicação o executa ao inicializar os recursos SQLite na primeira carga do processo. A rotina verifica diretamente as tabelas e não declara sucesso se houver erro ou resíduo vencido. O titular deve solicitar a eliminação pelo canal administrativo que a instituição vier a definir; esse canal e a autorização do operador ainda não são implementados pelo exercício. O operador autorizado pode então informar o número do pedido na aba **Eliminar memória**. A rotina remove todas as sessões e memórias vinculadas à matrícula confirmada do titular; no caso 0112, limita a matrícula inicialmente digitada aos dados do pedido para preservar dados não relacionados de terceiro. Verifica o banco antes de confirmar. Esse mecanismo cobre somente o banco de trabalho do agente; não elimina nem substitui o processo oficial.

O registro de conferência humana fica em `resultados/conferencias.jsonl`, arquivo separado do SQLite. Cada linha pode conter o identificador do pedido, recomendação do agente, encaminhamento humano, concordância/divergência, justificativa da divergência, minuta final editada e horário UTC. Justificativa e minuta passam pela máscara de PII, mas continuam sendo registros administrativos relevantes. O arquivo fica no diretório local do projeto; o acesso atual é controlado somente pelas permissões do sistema de arquivos, pois o Streamlit não implementa autenticação ou perfis de acesso. `.gitignore` impede sua inclusão acidental no Git, mas não controla cópias de segurança ou acesso ao computador. **Não há prazo de guarda nem rotina de exclusão definidos para esse arquivo no projeto.** A política institucional de retenção, acesso, arquivo e eliminação é uma pendência antes de uso real; os 30 dias do SQLite não se aplicam ao JSONL. A aba de eliminação de memória não toca nesse arquivo. A unidade deverá autorizar e estabelecer o procedimento de exclusão/guarda conforme a classificação administrativa do registro; o aplicativo não implementa essa autorização nem autenticação de titular.

Auditoria somente de leitura de 22/11/2026: o arquivo está presente e contém **14 linhas JSON válidas para 12 pedidos**, sem duplicatas integrais. Os **14 registros estão completos e alinhados** entre recomendação e encaminhamento: 14 concordantes, zero divergentes; são 7 `apto_para_autorizacao` / `prosseguir_ao_ordenador`, 5 `nao_recomendado` / `nao_recomendar` e 2 `diligencia` / `devolver_em_diligencia`. Os pedidos 0111 e 0112 têm duas linhas cada, uma de diligência e outra de prosseguimento, e há uma complementação correspondente para cada pedido no acervo. O JSONL não identifica explicitamente etapa ou sessão, portanto não comprova sozinho a preservação da mesma sessão; não há snapshot anterior para confirmar continuidade histórica. No caso 0112, a matrícula corrigida na complementação corresponde ao acervo de servidores, mas a matrícula não consta do JSONL. A auditoria documental está concluída; a governança institucional continua pendente de aprovação. Detalhes estão em `resultados/pendencia_politica_conferencias.md`.

No experimento de memoria, o primeiro turno de 0112 foi bloqueado antes do modelo, com zero chamadas e custo. A correcao foi enviada junto do pedido sob identidade confirmada. No caso 0111, o historico limitado recuperou e aplicou a complementacao; sem memoria, a recuperacao nao ocorreu. O modo com memoria de usuario tambem validou as duas complementacoes, mas elevou chamadas e custo sem acrescentar recuperacao em relacao ao historico limitado. Veja resultados/memoria.json para os seis turnos e os custos.

Na reexecução documentada, foram aprovados 42 testes; `pip check` ficou limpo; 42/42 casos offline e 78/78 propostas live elegíveis foram aprovadas. Na revisão documental atual, os 44 testes da suíte passaram. Os testes controlados exercitam o loop Agno com modelo stubado, incluindo limite de ferramentas, erro de provedor, custo zero nos bloqueios pré-modelo e separação do JSONL de conferência; não simulam falha HTTP externa. A interface passou AppTest e o servidor Streamlit respondeu HTTP 200; não houve captura nem inspeção visual em navegador. O conjunto do desafio não representa produção.

# Entradas e gabarito

O acervo fornecido permanece em `exemplos/dados/`. `agente.py` e a interface não importam nem consultam `exemplos/gabarito.json`; apenas `avaliacao.py` o lê após cada execução para pontuar resultados. O gabarito é referência de avaliação, nunca contexto do agente.


### Decisao institucional pendente para conferencias

Registro formal da pendencia e campos para aprovacao: `resultados/pendencia_politica_conferencias.md`.


Antes de habilitar dados reais, a unidade responsavel deve registrar: finalidade e classificacao do registro; responsavel custodiante; perfis autorizados para leitura, exportacao e exclusao; prazo de guarda; eventos que iniciam a contagem; destino de arquivo; procedimento, autorizacao e evidencias de descarte; tratamento de copias de seguranca. Nenhum prazo foi presumido nem configurado para `resultados/conferencias.jsonl`. Ate a decisao formal, use somente o acervo hipotetico. O arquivo e local e herda as permissoes do sistema operacional; o Streamlit nao tem autenticacao/perfis, e `.gitignore` nao protege acesso local nem backups. A limpeza do SQLite nao elimina o JSONL.
