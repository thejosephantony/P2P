# Roteiro curto para apresentação

1. Objetivo: comparar o tempo para distribuir o mesmo conteúdo aos clientes.
2. Descrever os quatro modos: um download por vez, todos em paralelo, limite
   N=2 e árvore P2P com retransmissão pelos peers intermediários.
3. Mostrar que P2P não faz todos os peers baixarem diretamente da origem:
   a origem conecta a 1/2, peer1 conecta a 3/4, e assim por diante.
4. Explicar matriz: 5/50/500 MB, 2/4/8 clientes, três repetições e 36 combinações.
5. Mostrar `tempos.csv`, verificação CRC32 e os mínimos/médias/máximos do PDF.
6. Discutir 500 MB e oito clientes: paralelo teve menor média nesse ambiente;
   sequencial inclui espera em fila; pool limita a pressão de concorrência.
7. Explicar que a origem P2P envia apenas duas cópias do arquivo, mas os peers
   internos também usam CPU e memória para receber/retransmitir.
8. Limitação principal: todos os processos medidos compartilham uma máquina
   e a rede loopback. Não generalizar o resultado para Internet/LAN física.
9. Demonstrar `java -jar dist/p2p.jar selftest`, ou os cinco containers P2P.

Perguntas prováveis:

- Por que usar tempo desde o GO? Para incluir a espera de clientes na fila.
- Por que há três repetições? Para observar variação, embora ainda seja uma
  amostra pequena para inferência estatística.
- O arquivo existe no disco? O conteúdo é sintético e determinístico, transmitido
  integralmente e descartado após a conferência, como permitido no enunciado.
- P2P sempre vence? Não. Topologia, banda de upload, RTT e custo de encaminhar
  alteram o desempenho. Os números medidos dependem do ambiente.
- Qual o benefício do pool? Controla quantos downloads consomem recursos ao mesmo
  tempo, mantendo os demais pedidos em espera.
- Como ampliar? Máquinas separadas, partida sincronizada, mais repetições,
  mais valores de N, controle de banda e análise de latência/perdas.
