# Acoes humanas pendentes para fechar o desafio

## 1. Confirmar a contextualização histórica, se necessária

O arquivo `resultados/conferencias.jsonl` está presente. A auditoria de 22/11/2026 encontrou 14 linhas JSON válidas e completas para 12 pedidos, sem duplicatas integrais. As 14 recomendações estão alinhadas aos encaminhamentos e marcadas concordantes. Os pedidos 0111 e 0112 têm, cada um, uma decisão de diligência e outra de prosseguimento, e há complementações para esses mesmos pedidos no acervo.

O JSONL não contém identificador explícito de etapa ou sessão, embora a sequência por pedido seja consistente com a análise original e posterior à complementação. Se a instituição ou avaliação exigir comprovação explícita da mesma sessão ou da etapa de cada registro, a pessoa responsável/custodiante deve verificar se existe evidência independente e rastreável. A auditoria também não dispõe de snapshot anterior para confirmar continuidade histórica. Não há base para afirmar que o arquivo atual precise ser recuperado em backup ou que tenha sido perdido definitivamente. Não alterar os registros nem inferir dados sem evidência e autorização documentadas.

## 2. Aprovar politica para conferencias humanas antes de dados reais

A pendencia esta detalhada em `resultados/pendencia_politica_conferencias.md`. A unidade responsavel deve preencher e aprovar:

- finalidade, classificacao e custodiante do registro;
- perfis com acesso para leitura, exportacao e exclusao;
- prazo de guarda e evento que inicia a contagem;
- destino de arquivo, procedimento/autorizacao de descarte e evidencias;
- tratamento de copias de seguranca.

Depois da aprovacao, implemente e teste autenticacao/perfis e as rotinas de guarda e descarte correspondentes. Hoje o Streamlit nao implementa autenticacao, e a aba de eliminacao do agente atua somente sobre o SQLite. Ate completar essa etapa, use somente o acervo hipotetico.

## 3. Registrar a limitacao da estimativa pre-codigo

`desenho.md` declara que nao existe evidencia datada de que a estimativa inicial de custo foi feita antes da implementacao. Essa cronologia nao pode ser criada retroativamente. Mantenha a declaracao transparente e, se a rubrica exigir prova contemporanea, solicite ao avaliador que considere a calibracao posterior como evidencia parcial, sem apresenta-la como estimativa pre-codigo.

## 4. Revisao visual final (recomendavel)

Os testes automatizados de interface passaram e o servidor local respondeu HTTP 200, mas nao houve captura nem verificacao visual em navegador. Para uma revisao visual com dados hipoteticos:

1. Instale as dependencias conforme `LEIA-ME.md` e execute `streamlit run app.py`.
2. Analise um pedido; confira progresso, recomendacao, fundamentos, alertas e minuta editavel.
3. Edite a minuta, registre uma decisao humana e confira que a divergencia exige justificativa.
4. Teste a complementacao e a aba de eliminacao apenas com o acervo hipotetico.
5. Encerre o servidor e confira/remova os bancos temporarios criados para a revisao. Nao use dados reais enquanto a politica acima estiver pendente.

## Estado de chaves e execucao

O `.env` local foi criado pelo responsavel e permanece ignorado pelo Git; nao o apague nem inclua em pacote/versionamento. O benchmark live final e o experimento de memoria foram executados com a chave configurada e sem expor seu valor.
