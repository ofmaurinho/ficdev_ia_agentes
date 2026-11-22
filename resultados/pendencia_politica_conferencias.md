# Pendencia formal: politica de conferencias humanas

**Status:** bloqueio para uso com dados reais.
**Registro afetado:** `resultados/conferencias.jsonl`, separado do SQLite do agente.
**Decisao necessaria:** aprovacao institucional da area responsavel.

A politica ainda nao foi fornecida nem aprovada. Portanto, este registro nao define prazo, autorizacao, titular custodiante, perfis de acesso ou rotina de descarte; nao executar exclusao no arquivo real. Ate a decisao formal, usar somente dados hipoteticos.

A area institucional deve preencher e aprovar: finalidade e classificacao do registro; unidade e custodiante responsaveis; perfis autorizados para leitura, exportacao e exclusao; prazo e evento inicial da contagem; destino de arquivo; condicoes de descarte; autorizacao exigida; tratamento de backups; evidencia de execucao.

O arquivo permanece local e sujeito as permissoes do sistema operacional. O Streamlit nao implementa autenticacao nem perfis; `.gitignore` nao restringe acesso local ou backups. A limpeza de memoria SQLite nao afeta esse JSONL. A verificacao existente usa registros sinteticos e comprova apenas a separacao dos escopos, nao a eliminacao do arquivo real.

**Evidencia de controle:** aviso na interface, secao de retencao em `LEIA-ME.md` e teste `test_eliminacao_sqlite_nao_altera_registro_jsonl_separado`.
