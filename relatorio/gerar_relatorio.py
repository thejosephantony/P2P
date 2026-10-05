#!/usr/bin/env python3
"""Gera o PDF a partir das medicoes reais do benchmark. Python opcional."""
from pathlib import Path
from collections import defaultdict
import argparse, csv, statistics, math, platform
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, Flowable, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

parser=argparse.ArgumentParser()
parser.add_argument('--dados',default=str(Path(__file__).resolve().parents[1]/'resultados-referencia'))
parser.add_argument('--saida',default=str(Path(__file__).resolve().parent/'Relatorio_P2P.pdf'))
parser.add_argument('--autor',default='Joseph')
parser.add_argument('--matricula',default='')
parser.add_argument('--grupo',default='')
a=parser.parse_args()
data=Path(a.dados); output=Path(a.saida); output.parent.mkdir(parents=True,exist_ok=True)
raw=list(csv.DictReader((data/'tempos.csv').open(encoding='utf-8')))
if not raw or any(r['crc_ok']!='true' for r in raw): raise ValueError('Medicoes ausentes ou integridade invalida')
modes=['sequencial','paralelo','pool','p2p']
labels={'sequencial':'Sequencial','paralelo':'Paralelo','pool':'Pool (N=2)','p2p':'P2P'}
palette={'sequencial':'#c16b24','paralelo':'#2463a8','pool':'#7555a3','p2p':'#008a80'}
grouped=defaultdict(list); runs=defaultdict(list)
for row in raw:
    mode,mb,n,rep=row['modo'],int(row['tamanho_mb']),int(row['clientes']),int(row['repeticao'])
    if int(row['bytes'])!=mb*1_000_000: raise ValueError('Numero de bytes divergente')
    grouped[(mode,mb,n)].append(float(row['tempo_s']))
    runs[(mode,mb,n,rep)].append(float(row['tempo_s']))
sizes=sorted({k[1] for k in grouped}); nodes=sorted({k[2] for k in grouped})
repeats=sorted({k[3] for k in runs})
if sizes!=[5,50,500] or nodes!=[2,4,8] or repeats!=[1,2,3]:
    raise ValueError('Este modelo de relatorio exige --sizes 5,50,500 --clients 2,4,8 --repeats 3 --pool 2')
for mode in modes:
    for mb in sizes:
        for n in nodes:
            if len(grouped[(mode,mb,n)])!=n*len(repeats): raise ValueError('Matriz incompleta')
env={}
for line in (data/'ambiente.txt').read_text(encoding='utf-8').splitlines():
    if '=' in line:
        key,value=line.split('=',1);env[key]=value
if env.get('pool')!='2': raise ValueError('Relatorio exige pool N=2')
for line in (data/'hardware.txt').read_text(encoding='utf-8').splitlines() if (data/'hardware.txt').exists() else []:
    if '=' in line:
        key,value=line.split('=',1);env[key]=value
with (data/'execucoes.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.writer(f);writer.writerow(['modo','tamanho_mb','clientes','repeticao','amostras','min_s','media_s','max_s'])
    for mb in sizes:
        for n in nodes:
            for rep in repeats:
                for mode in modes:
                    ts=runs[(mode,mb,n,rep)]
                    writer.writerow([mode,mb,n,rep,len(ts),f'{min(ts):.9f}',f'{statistics.mean(ts):.9f}',f'{max(ts):.9f}'])

font_paths=[Path('/usr/share/fonts/truetype/dejavu'),Path('C:/Windows/Fonts')]
for folder in font_paths:
    choices=[('DejaVuSans.ttf','DejaVuSans-Bold.ttf'),('arial.ttf','arialbd.ttf')]
    found=False
    for normal,bold in choices:
        if (folder/normal).exists() and (folder/bold).exists():
            pdfmetrics.registerFont(TTFont('Body',str(folder/normal)))
            pdfmetrics.registerFont(TTFont('BodyBold',str(folder/bold)));found=True;break
    if found: break
else:
    pdfmetrics.registerFontFamily('Helvetica',normal='Helvetica',bold='Helvetica-Bold')
body='Body' if found else 'Helvetica'; bold='BodyBold' if found else 'Helvetica-Bold'
pdfmetrics.registerFontFamily(body,normal=body,bold=bold,italic=body,boldItalic=bold)
navy=colors.HexColor('#152c46');teal=colors.HexColor('#007e78');gray=colors.HexColor('#536172');light=colors.HexColor('#edf3f8')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleP',fontName=bold,fontSize=27,leading=32,textColor=navy,spaceAfter=12))
styles.add(ParagraphStyle(name='SubP',fontName=body,fontSize=14,leading=19,textColor=teal,spaceAfter=10))
styles.add(ParagraphStyle(name='HeadingP',fontName=bold,fontSize=17,leading=22,textColor=navy,spaceAfter=11))
styles.add(ParagraphStyle(name='SmallH',fontName=bold,fontSize=11,leading=15,textColor=teal,spaceBefore=8,spaceAfter=5))
styles.add(ParagraphStyle(name='BodyP',fontName=body,fontSize=9.5,leading=14,textColor=navy,spaceAfter=8))
styles.add(ParagraphStyle(name='SmallP',fontName=body,fontSize=8,leading=11,textColor=gray,spaceAfter=5))
styles.add(ParagraphStyle(name='Cell',fontName=body,fontSize=8.3,leading=11,textColor=navy))
styles.add(ParagraphStyle(name='CellH',fontName=bold,fontSize=8.3,leading=11,textColor=colors.white))
styles.add(ParagraphStyle(name='Metric',fontName=bold,fontSize=19,leading=25,textColor=teal,alignment=TA_CENTER))
styles.add(ParagraphStyle(name='MetricLabel',fontName=body,fontSize=8,leading=11,textColor=navy,alignment=TA_CENTER))
styles.add(ParagraphStyle(name='CodeP',fontName='Courier',fontSize=7.7,leading=11,textColor=navy,spaceAfter=8))
def p(text,style='BodyP'):return Paragraph(text,styles[style])
def s(n=5):return Spacer(1,n)
def table(rows,widths,small=False):
    converted=[[p(str(value),'CellH' if i==0 else 'Cell') for value in row] for i,row in enumerate(rows)]
    t=Table(converted,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,light]),('LEFTPADDING',(0,0),(-1,-1),8),
        ('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),3 if small else 6),
        ('BOTTOMPADDING',(0,0),(-1,-1),3 if small else 6),('LINEBELOW',(0,0),(-1,0),1,teal)]))
    return t
def fmt(v):return f'{v:.6f}'.replace('.',',')

class Identity(Flowable):
    def __init__(self):super().__init__();self.width=17.8*cm;self.height=78
    def draw(self):
        c=self.canv;c.setFont(body,8);c.setFillColor(gray)
        c.drawString(0,65,'AUTOR');c.drawString(10.1*cm,65,'MATRÍCULA');c.drawString(0,29,'DEMAIS INTEGRANTES, SE HOUVER')
        fields=[('autor',a.autor,0,41,9.6*cm),('matricula',a.matricula,10.1*cm,41,7.7*cm),('grupo',a.grupo,0,5,17.8*cm)]
        for name,value,x,y,w in fields:
            ax,ay=c.absolutePosition(x,y)
            c.acroForm.textfield(name=name,tooltip=name.title(),value=value,x=ax,y=ay,width=w,height=20,
                fontName='Helvetica',fontSize=10,borderStyle='solid',borderWidth=.5,borderColor=colors.HexColor('#bacbd9'),
                fillColor=colors.HexColor('#f6f9fc'),textColor=navy,forceBorder=True)

class Tree(Flowable):
    def __init__(self):super().__init__();self.width=17.8*cm;self.height=132
    def draw(self):
        c=self.canv;positions={0:(253,110),1:(130,73),2:(376,73),3:(68,35),4:(190,35),5:(315,35),6:(438,35)}
        c.setStrokeColor(colors.HexColor('#92a9ba'));c.setLineWidth(1.1)
        for parent,child in [(0,1),(0,2),(1,3),(1,4),(2,5),(2,6)]:
            x,y=positions[parent];xx,yy=positions[child];c.line(x,y-10,xx,yy+10)
        for node,(x,y) in positions.items():
            c.setFillColor(teal if node==0 else navy);c.roundRect(x-32,y-10,64,20,5,fill=1,stroke=0)
            c.setFillColor(colors.white);c.setFont(bold,8);c.drawCentredString(x,y-3,'Origem' if node==0 else f'Peer {node}')
        c.setFillColor(gray);c.setFont(body,8);c.drawString(0,5,'Exemplo: origem + 6 receptores. A mesma regra de árvore é usada com 2, 4 e 8.')

def footer(c,doc):
    c.saveState();c.setStrokeColor(colors.HexColor('#d5e1eb'));c.line(1.6*cm,1.25*cm,19.4*cm,1.25*cm)
    c.setFont(body,8);c.setFillColor(gray);c.drawString(1.6*cm,.8*cm,'UFS | Sistemas Distribuídos | Atividade 01 - Unidade 2')
    c.drawRightString(19.4*cm,.8*cm,str(doc.page));c.restoreState()

story=[]
story += [p('UNIVERSIDADE FEDERAL DE SERGIPE','SmallH'),s(10),p('Avaliação de desempenho<br/>na transferência de arquivos','TitleP'),
          p('Cliente-servidor e P2P | Java + TCP','SubP'),Identity(),s(8)]
metric=Table([[p('4','Metric'),p(str(len(grouped)),'Metric'),p(str(len(runs)),'Metric'),p(str(len(raw)),'Metric')],
              [p('modos','MetricLabel'),p('combinações','MetricLabel'),p('execuções','MetricLabel'),p('downloads','MetricLabel')]],colWidths=[4.45*cm]*4)
metric.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),light),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
story += [metric,s(10),p('Objetivo e síntese','SmallH'),p('Comparar quatro formas de distribuir o mesmo conteúdo a vários clientes: atendimento sequencial, atendimento paralelo, pool limitado a N=2 e compartilhamento P2P em árvore. Foram variados os tamanhos de 5, 50 e 500 MB e as quantidades de 2, 4 e 8 receptores, com três repetições por combinação.'),
          p('Os resultados são medições reais de transferências TCP. Todos os 504 downloads tiveram tamanho e CRC32 corretos. Foram recebidos 93,24 GB de conteúdo no conjunto das execuções. O relatório apresenta mínimo, média e máximo por combinação e por repetição.'),
          p('Ambiente da medição','SmallH')]
environment_rows=[['Item','Configuração'],['Execução',env.get('os','')+' / '+env.get('arquitetura','')],['Java',env.get('java','')+'; processos JVM independentes'],['CPU disponível',env.get('processadores_logicos','')+' processadores lógicos; '+env.get('cpu_modelo','modelo não registrado')],['Memória / rede',env.get('memoria_limite','limite não registrado')+'; TCP IPv4 loopback 127.0.0.1'],['Data registrada (UTC)',env.get('data_utc','')]]
story += [table(environment_rows,[4*cm,13.8*cm],True),s(7),p('<b>Escopo:</b> os nós medidos são processos separados no mesmo host Linux. Eles compartilham CPU, memória e rede local. Os números não foram obtidos no Windows do autor nem em computadores físicos distintos. A implementação também permite execução em rede local real.','SmallP'),PageBreak()]

story += [p('Implementação e método','HeadingP'),p('Quatro modos de atendimento','SmallH')]
mode_rows=[['Modo','Comportamento implementado'],['Sequencial','Uma conexão é atendida por completo antes do próximo download. Os demais clientes aguardam.'],['Paralelo','Pool com uma thread disponível por cliente: todos os downloads podem ser atendidos simultaneamente.'],['Pool (N=2)','Duas threads de envio. Conexões adicionais são aceitas e aguardam na fila de tarefas.'],['P2P','Árvore binária TCP. A origem envia para até dois peers; peers internos recebem e encaminham blocos aos filhos.']]
story += [table(mode_rows,[3.4*cm,14.4*cm],True),s(8),p('Conteúdo, início e integridade','SmallH'),
          p('O conteúdo é sintético e determinístico: um bloco pseudoaleatório de 64 KiB, com semente 2026, é repetido até completar o tamanho solicitado. 1 MB corresponde a 1.000.000 bytes. O protocolo envia o tamanho (8 bytes), o CRC32 esperado (8 bytes) e todos os bytes do conteúdo. O receptor descarta os dados após contá-los e atualizar o CRC32.'),
          p('Antes de cada rodada, a origem e todos os receptores são criados e anunciam READY. O coordenador libera os receptores com GO. Cada receptor mede o intervalo com System.nanoTime, desde seu GO até receber e validar o conteúdo. Conexão, espera em fila e CRC32 entram na medição; criação da JVM e cálculo prévio do CRC esperado ficam fora. Os sinais GO são enviados em sequência, sem sincronização atômica.'),
          p('No P2P, o encaminhamento acontece durante a recepção. Para peers internos, o tempo inclui também o envio dos blocos aos filhos. A duração da origem é excluída das estatísticas. Cada peer receptor conta como um cliente.'),
          p('Estatísticas e repetição','SmallH'),p('Para uma combinação de modo, tamanho e quantidade de clientes, foram reunidos os tempos das três repetições: n = 3 × clientes (6, 12 ou 24 amostras). Mínimo = menor tempo; média = soma dos tempos / n; máximo = maior tempo. O anexo informa essas mesmas estatísticas separadamente por rodada. A ordem dos quatro modos foi embaralhada com semente fixa para reduzir o efeito de uma ordem fixa.'),
          Tree(),p('A topologia P2P é fixa e não oferece descoberta automática, entrada dinâmica, recuperação de falhas ou troca de partes como BitTorrent. CRC32 é uma conferência de erros acidentais, não uma proteção criptográfica.','SmallP'),PageBreak()]

notes={5:'Com arquivos de 5 MB, as durações são curtas. Escalonamento, conexão, sinal GO e inicialização dos métodos da JVM têm peso relativo elevado; pequenas diferenças de tempo não sustentam uma conclusão geral de superioridade.',
       50:'Com 50 MB, o aumento do conteúdo evidencia mais o custo de transferir e aguardar. Para oito clientes, o paralelo apresenta a menor média; o P2P se aproxima, mas continua sujeito ao custo de encaminhar na mesma máquina.',
       500:'Com 500 MB e oito clientes, o paralelo tem a menor média, seguido do pool, do P2P e do sequencial. O crescimento do máximo sequencial mostra o efeito da espera enquanto downloads anteriores são atendidos.'}
for mb in sizes:
    story += [p(f'Resultados | arquivo de {mb} MB','HeadingP'),p('Tempos em segundos; estatísticas agregadas das três repetições. Em cada linha, a amostra contém 3 × clientes tempos individuais.','SmallP')]
    rows=[['Clientes','Modo','Amostras','Mínimo (s)','Média (s)','Máximo (s)']]
    for n in nodes:
        for mode in modes:
            ts=grouped[(mode,mb,n)];rows.append([n,labels[mode],len(ts),fmt(min(ts)),fmt(statistics.mean(ts)),fmt(max(ts))])
    story += [table(rows,[2.2*cm,3.2*cm,2.2*cm,3.4*cm,3.4*cm,3.4*cm]),s(10)]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,ax=plt.subplots(figsize=(8.6,3.25));fig.patch.set_facecolor('white')
    for mode in modes:
        ax.plot(nodes,[statistics.mean(grouped[(mode,mb,n)]) for n in nodes],marker='o',linewidth=2,label=labels[mode],color=palette[mode])
    ax.set_xticks(nodes);ax.set_xlabel('Quantidade de clientes / peers receptores');ax.set_ylabel('Tempo médio (s)');ax.set_ylim(bottom=0)
    ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False);ax.legend(ncol=4,loc='upper center',bbox_to_anchor=(.5,1.16),frameon=False,fontsize=9)
    fig.tight_layout();figpath=output.parent/f'media_{mb}MB.png';fig.savefig(figpath,dpi=180,bbox_inches='tight');plt.close(fig)
    story += [Image(str(figpath),width=17.8*cm,height=6.7*cm),s(8),p(notes[mb]),p('Fonte: tempos individuais registrados em tempos.csv; valores recalculados diretamente dos dados.','SmallP'),PageBreak()]

seq=statistics.mean(grouped[('sequencial',500,8)]);par=statistics.mean(grouped[('paralelo',500,8)]);pool=statistics.mean(grouped[('pool',500,8)]);p2p=statistics.mean(grouped[('p2p',500,8)])
story += [p('Discussão, conclusão e reprodução','HeadingP'),
          p(f'Para 500 MB e oito clientes, as médias foram: sequencial {fmt(seq)} s, paralelo {fmt(par)} s, pool {fmt(pool)} s e P2P {fmt(p2p)} s. A média sequencial foi {seq/par:.2f} vezes a média paralela. O P2P reduziu a média em {(1-p2p/seq)*100:.1f}% em relação ao sequencial, mas teve média {p2p/par:.2f} vezes a do paralelo.'),
          p('Essas diferenças são compatíveis com a organização do atendimento: o sequencial acumula espera, enquanto o paralelo pode explorar os recursos disponíveis. O pool N=2 limita a concorrência e produz espera intermediária. Com dois clientes, pool e paralelo têm a mesma capacidade de atendimento; diferenças observadas entre eles refletem variação de execução, não uma diferença de limite.'),
          p('O P2P reduz o conteúdo enviado pela origem: com oito receptores, ela envia apenas duas cópias do arquivo, em vez de oito. A árvore inteira ainda transmite oito cópias ao todo, uma por aresta de recepção. Neste ambiente, peers compartilham o mesmo host e o encaminhamento adiciona trabalho local; o benefício de distribuir upload entre máquinas com enlaces independentes não foi medido.'),
          p('Limitações e interpretação','SmallH'),p('Há três repetições, sem uma fase dedicada de aquecimento da JVM e sem intervalos de confiança. O ambiente virtual compartilhado pode variar durante a execução. Não foram aplicados limites de banda ou latência artificial. O estudo não mede RTT externo, perdas, discos, upload assimétrico, falhas ou churn. O comando manual P2P começa a medir antes da chegada da origem e serve à demonstração da topologia; seus tempos não são comparáveis à matriz com GO.'),
          p('Conclusão: o modo paralelo apresentou a menor média no cenário de maior conteúdo e mais clientes deste ensaio. O pool limitou recursos com uma penalidade de espera. O P2P realizou encaminhamento distribuído de fato, porém os dados locais não provam uma vantagem ou desvantagem universal. Uma extensão adequada seria repetir a matriz em máquinas físicas separadas, com partida sincronizada, mais repetições e controle da rede.'),
          p('Como reproduzir','SmallH'),Preformatted('java -jar dist/p2p.jar selftest\njava -jar dist/p2p.jar benchmark --sizes 5,50,500 --clients 2,4,8\n    --repeats 3 --pool 2 --out resultados-windows',styles['CodeP']),
          p('O comando benchmark acima deve ser escrito em uma única linha no terminal. O README contém comandos completos para Windows, Docker e máquinas distintas. O projeto inclui código-fonte, JAR, dados brutos, resumo e estatísticas por execução.'),
          p('Referências','SmallH'),p('UFS. Atividade 01 - Unidade 2, Sistemas Distribuídos, COMP0470. Enunciado fornecido para esta atividade.','SmallP'),
          p('Oracle. Java SE 17 API: Socket; Executors; System.nanoTime. Documentação oficial, consultada em 04/10/2026 (America/Fortaleza).','SmallP'),
          p('<link href="https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/net/Socket.html">docs.oracle.com - Socket</link> | <link href="https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/Executors.html">Executors</link> | <link href="https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/System.html#nanoTime()">System.nanoTime</link>','SmallP'),PageBreak()]

for i,mb in enumerate(sizes):
    story += [p(f'Anexo | estatísticas por rodada - {mb} MB','HeadingP'),p('Cada linha resume somente os clientes de uma repetição. Tempos em segundos. São 36 rodadas por tamanho: três quantidades de clientes × três repetições × quatro modos.','SmallP')]
    rows=[['Clientes','Rodada','Modo','Mínimo (s)','Média (s)','Máximo (s)']]
    for n in nodes:
        for rep in repeats:
            for mode in modes:
                ts=runs[(mode,mb,n,rep)];rows.append([n,rep,labels[mode],fmt(min(ts)),fmt(statistics.mean(ts)),fmt(max(ts))])
    story += [table(rows,[1.95*cm,1.9*cm,3.15*cm,3.6*cm,3.6*cm,3.6*cm],True),s(8),p('Os valores podem ser auditados em execucoes.csv e tempos.csv. Nenhum resultado foi estimado ou substituído por números teóricos.','SmallP')]
    if i < len(sizes)-1:story.append(PageBreak())

doc=SimpleDocTemplate(str(output),pagesize=A4,rightMargin=1.6*cm,leftMargin=1.6*cm,topMargin=1.5*cm,bottomMargin=1.6*cm,
    title='Avaliação de desempenho na transferência de arquivos - Cliente-servidor e P2P',author=a.autor,subject='UFS Sistemas Distribuídos, Atividade 01 - Unidade 2')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(f'PDF gerado: {output.resolve()}')
