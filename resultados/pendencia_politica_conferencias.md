# Pendência formal: política de conferências humanas

**Status:** auditoria técnica e revisão documental concluídas; governança institucional pendente; uso com dados reais condicionado à aprovação.
**Registro auditado:** `resultados/conferencias.jsonl`, separado do SQLite do agente.
**Decisão necessária:** aprovação institucional da área responsável.

## Resultado da auditoria do arquivo atual

Auditoria somente de leitura realizada em 22/11/2026. O arquivo existe no caminho esperado e contém **14 linhas JSON válidas**, referentes a **12 pedidos distintos**. Não foram encontradas linhas integralmente duplicadas. Há duas linhas para cada um dos pedidos DIA-2026-0111 e DIA-2026-0112, e uma linha para cada um dos outros dez pedidos.

Os 14 registros têm identificador do pedido, recomendação do agente, encaminhamento humano, indicação booleana de concordância/divergência, campo de justificativa, minuta final e horário UTC válido. As 14 minutas estão preenchidas. Todas as linhas estão marcadas `concordancia=true` e, ao comparar as recomendações com os encaminhamentos correspondentes, as 14 estão alinhadas: 7 `apto_para_autorizacao` / `prosseguir_ao_ordenador`, 5 `nao_recomendado` / `nao_recomendar` e 2 `diligencia` / `devolver_em_diligencia`. Não há divergências declaradas (0) e, portanto, não há justificativas de divergência exigíveis ausentes. **Os 14 registros estão completos quanto aos campos auditados; nenhum incompleto ou inválido foi encontrado.**

Os pedidos 0111 e 0112 têm, cada um, um registro de diligência (`diligencia` / `devolver_em_diligencia`) e outro de prosseguimento (`apto_para_autorizacao` / `prosseguir_ao_ordenador`). O acervo de complementações contém uma entrada para cada um desses mesmos identificadores. Essa correspondência de pedido e sequência de decisão é evidência consistente das etapas original e posterior à complementação. Ainda assim, o JSONL não possui campo explícito de etapa ou identificador de sessão; a preservação da mesma sessão e a atribuição inequívoca de cada linha a uma tela/etapa não podem ser verificadas pelo arquivo isoladamente. No caso 0112, a matrícula digitada originalmente diverge da corrigida na complementação; a matrícula corrigida corresponde a um registro de servidor no acervo. O JSONL não registra a matrícula usada na conferência, portanto essa associação é corroborada pelo acervo e pelo fluxo, não pelos próprios campos da conferência. Não foi usado o gabarito para completar registros.

Não há snapshot ou hash anterior disponível para comprovar a continuidade dos registros em relação a versões passadas. A auditoria confirma o conteúdo presente; não conclui se registros anteriores foram sobrescritos ou recuperados. Nenhum registro foi criado, corrigido ou removido durante esta auditoria.

As linhas documentam eventos de conferência humana, conforme o uso informado pelo responsável e as decisões, minutas e horários persistidos. Como a aplicação não autentica usuários, o arquivo não comprova por si só a identidade de quem realizou cada ação.

## Controles técnicos implementados e comprovados

- A aplicação grava conferências no JSONL, em arquivo separado do banco SQLite de memória do agente.
- A auditoria atual encontrou os 14 registros completos descritos acima, sem duplicatas integrais e com recomendações alinhadas aos encaminhamentos.
- O arquivo é coberto por regra do `.gitignore`, o que evita sua inclusão acidental no Git, mas não restringe leitura local nem protege cópias de segurança.
- O teste `test_registro_persiste_minuta_editada_com_pii_mascarada` valida gravação em JSONL temporário e mascaramento. O teste `test_eliminacao_sqlite_nao_altera_registro_jsonl_separado` verifica a separação de escopos com arquivo sintético; nenhum deles prova retenção ou descarte do arquivo real.
- O arquivo real foi lido e auditado sem alteração.
- Nesta revisão, `python -m unittest discover -s testes -v` passou nos 44 testes. Uma comparação de hashes dos arquivos JSON, JSONL, CSV e SQLite antes/depois confirmou que permaneceram inalterados.

## Limitações técnicas ainda existentes

- O Streamlit não implementa autenticação nem perfis de acesso para leitura, exportação ou exclusão.
- O `.gitignore` não restringe acesso local nem protege backups.
- A exclusão da memória SQLite não elimina os registros JSONL.
- Não existe rotina institucionalmente aprovada de retenção e descarte para o JSONL.
- O tratamento de cópias de segurança depende de definição institucional.
- O JSONL não registra etapa nem identificador de sessão e não permite comparar o conteúdo atual com uma versão histórica anterior.

## Política institucional pendente

A área institucional deve definir e aprovar, sem presumir responsáveis ou prazos:

- finalidade e classificação do registro;
- unidade responsável e custodiante;
- perfis autorizados;
- prazo de guarda e evento inicial da contagem;
- destino de arquivamento;
- condições e autorização para descarte;
- tratamento de backups;
- evidências necessárias;
- aprovação institucional formal.

Esta validação técnica não representa aprovação institucional. A ausência de autenticação e perfis continua sendo uma limitação; nenhuma dessas funcionalidades foi implementada.

## Situação de uso

- **Execução acadêmica com acervo hipotético:** realizada.
- **Conferências humanas:** realizadas conforme informado pelo responsável e documentadas nos 14 registros atuais; a autoria não é autenticada pela aplicação.
- **Persistência e integridade:** o arquivo atual é legível, tem 14 linhas válidas para 12 pedidos, sem duplicatas, campos auditados completos e decisões alinhadas.
- **Diligências e complementações:** há evidência para os dois pedidos (0111 e 0112), com uma decisão de diligência e outra de prosseguimento para cada, além das complementações correspondentes no acervo. O JSONL não identifica explicitamente a sessão ou etapa.
- **Histórico de preservação:** não verificável sem snapshot ou hash anterior; não há base para afirmar perda definitiva ou recuperação de uma cópia.
- **Governança institucional:** pendente de aprovação.
- **Uso com dados reais:** condicionado à aprovação institucional e à definição dos controles necessários.
