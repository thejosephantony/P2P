# P2P - Avaliação de desempenho na transferência de arquivos

Atividade 01 da Unidade 2 de Sistemas Distribuídos, UFS, COMP0470.
Professor: Rafael Oliveira Vasconcelos. Autor: Joseph.

Implementação Java 17+ com TCP e quatro modos: cliente-servidor sequencial,
cliente-servidor paralelo, cliente-servidor com pool limitado e P2P em árvore
binária. Os peers intermediários recebem e retransmitem blocos; a origem
envia somente aos dois primeiros peers. Não é um protocolo BitTorrent.

## Executar agora no Windows

```powershell
java -jar .\dist\p2p.jar --help
java -jar .\dist\p2p.jar selftest
```

O teste rápido deve terminar com `SUCESSO: quatro modos verificados`.
Depois execute a matriz completa:

```powershell
java -jar .\dist\p2p.jar benchmark --sizes 5,50,500 --clients 2,4,8 --repeats 3 --pool 2 --out resultados-windows
```

São 36 combinações, 108 execuções e 504 downloads. O tempo depende da máquina.
Cada cliente é um processo JVM separado e usa uma conexão TCP real. Neste comando
todos os processos estão no mesmo computador, via `127.0.0.1`.
Essa execução emula nós independentes e não representa uma rede de computadores
físicos separados. O relatório entregue identifica essa limitação.

## Compilar novamente

Com o JDK instalado, sem Maven:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Alternativa com Maven/NetBeans: abra este projeto pelo `pom.xml` e execute
Clean and Build. No terminal, `mvn clean package` produz `target/p2p.jar`.
O código usa somente a biblioteca padrão do Java.

## Docker

```powershell
docker compose build
docker compose run --rm benchmark
```

Os CSVs ficam em `resultados-windows`. O benchmark em Docker também cria processos
separados no mesmo container; não distribui a medição automaticamente por hosts.
A imagem é compilada dentro do Docker, sem depender do JDK ou Maven do Windows.

Para demonstrar o P2P com cinco containers e uma rede Docker:

```powershell
docker compose -f compose-p2p.yaml build origem
docker compose -f compose-p2p.yaml up --force-recreate
```

Os serviços `origem`, `peer1`, `peer2`, `peer3` e `peer4` devem terminar com código 0.
Cada peer deve imprimir `RESULT`, 50.000.000 bytes e `true`. A origem envia a
peer1/peer2; peer1 encaminha a peer3/peer4. Ao terminar:

```powershell
docker compose -f compose-p2p.yaml down
```

A configuração Docker foi conferida estruturalmente, mas Docker não estava
disponível no ambiente em que os números do relatório foram medidos.
Os números do relatório vêm exclusivamente da execução Java documentada.

## Executar em computadores diferentes

Use IPs acessíveis na rede local e permita as portas TCP escolhidas no firewall.
Não use `127.0.0.1` para conectar computadores diferentes.

Servidor para quatro clientes e arquivo de 50 MB:

```powershell
java -jar .\dist\p2p.jar servidor sequencial 9000 4 2 50
```

Em quatro terminais, em uma ou mais outras máquinas:

```powershell
java -jar .\dist\p2p.jar cliente IP_DO_SERVIDOR 9000
```

Troque `sequencial` por `paralelo` ou `pool` e reinicie o servidor a cada rodada.
O servidor termina depois de atender a quantidade de clientes informada.

P2P com origem + quatro peers: inicie folhas 3/4/2 primeiro, depois peer1 e,
por último, origem. Cada linha abaixo pertence a uma máquina/terminal diferente.
Substitua `IP_PEERx` pelos IPs reais:

```powershell
java -jar .\dist\p2p.jar peer 3 9000 50
java -jar .\dist\p2p.jar peer 4 9000 50
java -jar .\dist\p2p.jar peer 2 9000 50
java -jar .\dist\p2p.jar peer 1 9000 50 IP_PEER3:9000 IP_PEER4:9000
java -jar .\dist\p2p.jar peer 0 9000 50 IP_PEER1:9000 IP_PEER2:9000
```

O modo manual P2P inclui a espera pela origem no seu cronômetro; ele serve para
demonstrar a topologia. Os tempos comparáveis do relatório usam o benchmark com
sinal de partida. Não misture tempos manuais com essa matriz experimental.

## Metodologia e dados

- Tamanhos: 5, 50 e 500 MB. **1 MB = 1.000.000 bytes**.
- Clientes/peers receptores: 2, 4 e 8, além do nó de origem.
- Modos: `sequencial`, `paralelo`, `pool` (N=2) e `p2p`.
- Repetições: 3 por combinação; ordem dos modos embaralhada com semente 2026.
- Conteúdo sintético determinístico, gerado em blocos de 64 KiB; todos os bytes
  atravessam sockets TCP. Não há compressão e não se grava o download em disco.
- Cronômetro monotônico local (`System.nanoTime`), após receber o sinal GO e até
  receber/verificar todos os bytes. Inclui conexão, espera na fila e CRC32.
- Cada processo fica pronto antes do GO. A inicialização das JVMs e a geração
  prévia do CRC esperado ficam fora da medição. O envio dos sinais não é atômico.
- P2P usa encaminhamento durante a recepção, sem esperar um arquivo completo.
  Peers internos incluem o encaminhamento dos blocos no tempo medido.
- Todos os downloads verificam tamanho e CRC32. CRC32 detecta erros acidentais;
  não é uma verificação criptográfica contra alteração maliciosa.
- O sequencial verifica máximo 1 envio ativo; o pool verifica no máximo N.

Resultados medidos no ambiente Linux de referência:

| Arquivo | Conteúdo |
| --- | --- |
| `resultados-referencia/tempos.csv` | 504 tempos individuais, bytes e integridade |
| `resultados-referencia/resumo.csv` | 36 combinações com mínimo, média e máximo |
| `resultados-referencia/execucoes.csv` | 108 rodadas com mínimo, média e máximo |
| `resultados-referencia/ambiente.txt` | SO, Java, CPU disponível e parâmetros |
| `relatorio/Relatorio_P2P.pdf` | Relatório, gráficos, análise e anexos |
| `relatorio/gerar_relatorio.py` | Script que regenera o PDF a partir dos CSVs |

Mínimo/média/máximo no resumo são calculados sobre os clientes de todas as três
repetições da mesma combinação: 6, 12 ou 24 amostras. O máximo indica o maior
tempo individual observado, não a média dos últimos clientes de cada rodada.
O anexo apresenta também as estatísticas por rodada, para eliminar ambiguidade.

Exemplo: 500 MB / 8 clientes, médias medidas: sequencial 0,934717 s;
paralelo 0,371160 s; pool 0,556137 s; P2P 0,641021 s.
São resultados de loopback e processos compartilhando CPU/memória, e não tempos
da máquina Windows do autor nem uma previsão de desempenho pela Internet.

Para regenerar o relatório com novas medições, Python é opcional:

```powershell
python -m pip install reportlab matplotlib
python .\relatorio\gerar_relatorio.py --dados .\resultados-windows --saida .\relatorio\Relatorio_Windows.pdf --autor "Joseph" --matricula "SUA_MATRICULA"
```
## Limitações

O experimento mede uma emulação local: rede loopback, recursos compartilhados e
nenhum limite artificial de banda. Não mede roteadores, RTT de rede externa,
perdas, assimetria de upload, entrada/saída dinâmica de peers ou recuperação de
falhas. Há três repetições, sem fase dedicada de aquecimento da JVM ou intervalos
de confiança. A duração pequena de arquivos menores amplifica ruído de
escalonamento e sincronização. Portanto, o resultado local não prova uma
superioridade geral de uma arquitetura. A implementação permite repetir a
transferência em máquinas distintas para ampliar o estudo.
