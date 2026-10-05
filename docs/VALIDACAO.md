# Validação executada

Ambiente: Linux 6.18.44, Java 17.0.20, TCP IPv4 loopback, em 04/10/2026
(America/Fortaleza). Esta validação não foi executada na máquina Windows do autor.

- Fonte compilada para Java 17 e JAR executável gerado.
- `selftest`: quatro modos, quatro receptores, arquivo de 1 MB; sucesso.
- Matriz completa: 5/50/500 MB, 2/4/8 clientes, três repetições, quatro modos.
- 108 execuções e 504 downloads finalizados.
- Todos os downloads verificaram tamanho e CRC32.
- Os 36 resumos foram recalculados a partir dos 504 tempos individuais e
  conferidos: mínimo, média, máximo e quantidade de amostras coincidiram.
- Sequencial: máximo de um envio ativo por vez; pool: no máximo dois.
- Teste negativo: um servidor de teste enviou `xyz` com o CRC32 esperado de `abc`;
  o cliente encerrou com erro `CRC32 divergente`, como esperado.
- `selftest` repetido após a versão final do código: sucesso nos quatro modos.
- `compose.yaml` e `compose-p2p.yaml` analisados como YAML válido.
- Não foi possível executar Docker no ambiente de medição; a configuração de
  containers é fornecida para execução no Windows e não é fonte dos tempos.
- O PDF foi renderizado e revisado visualmente; contém nove páginas e campos
  editáveis para identificação.

Dados preservados em `resultados-referencia/`; a matriz não precisa ser rodada
novamente apenas para abrir ou entregar o relatório.
