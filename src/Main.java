import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.zip.CRC32;

/** Experimento TCP: sequencial, paralelo, pool e P2P em arvore binaria. */
public final class Main {
    static final int BLOCK = 64 * 1024;
    static final int TIMEOUT = 120_000;
    static final byte[] CONTENT = content();
    static byte[] content() { byte[] b = new byte[BLOCK]; new Random(2026).nextBytes(b); return b; }
    static long checksum(long size) {
        CRC32 crc = new CRC32();
        for (long left = size; left > 0;) { int n = (int)Math.min(left, BLOCK); crc.update(CONTENT, 0, n); left -= n; }
        return crc.getValue();
    }
    static ServerSocket listener(int port) throws IOException {
        ServerSocket s = new ServerSocket(); s.setReuseAddress(true);
        s.bind(new InetSocketAddress("0.0.0.0", port), 128); s.setSoTimeout(TIMEOUT); return s;
    }
    static Socket connect(String host, int port) throws IOException {
        Socket s = new Socket(); s.connect(new InetSocketAddress(host, port), 10_000);
        s.setSoTimeout(TIMEOUT); s.setTcpNoDelay(true); return s;
    }
    static void ready() { System.out.println("READY"); System.out.flush(); }
    static void go() throws IOException {
        String line = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8)).readLine();
        if (!"GO".equals(line)) throw new IOException("Sinal GO ausente");
    }
    static void send(Socket socket, long size, long crc) throws IOException {
        try (socket; DataOutputStream out = new DataOutputStream(socket.getOutputStream())) {
            out.writeLong(size); out.writeLong(crc);
            for (long left = size; left > 0;) { int n = (int)Math.min(left, BLOCK); out.write(CONTENT, 0, n); left -= n; }
            out.flush();
        }
    }
    static void server(String mode, int port, int clients, int pool, long size, long crc) throws Exception {
        if (!List.of("sequencial", "paralelo", "pool").contains(mode)) throw new IllegalArgumentException("Modo do servidor invalido");
        if (clients < 1 || pool < 1 || size < 1) throw new IllegalArgumentException("Parametros devem ser positivos");
        AtomicInteger active = new AtomicInteger(), maximum = new AtomicInteger();
        Queue<Throwable> errors = new ConcurrentLinkedQueue<>();
        try (ServerSocket ss = listener(port)) {
            ready();
            if (mode.equals("sequencial")) {
                for (int i = 0; i < clients; i++) { Socket s = ss.accept(); maximum.set(1); send(s, size, crc); }
            } else {
                ExecutorService executor = Executors.newFixedThreadPool(mode.equals("pool") ? pool : clients);
                for (int i = 0; i < clients; i++) {
                    Socket s = ss.accept();
                    executor.submit(() -> { int n = active.incrementAndGet(); maximum.accumulateAndGet(n, Math::max);
                        try { send(s, size, crc); } catch (Throwable e) { errors.add(e); }
                        finally { active.decrementAndGet(); }
                    });
                }
                executor.shutdown();
                if (!executor.awaitTermination(TIMEOUT, TimeUnit.MILLISECONDS)) throw new IOException("Timeout do servidor");
            }
            if (!errors.isEmpty()) throw new IOException("Erro no envio", errors.peek());
            System.out.println("MAX_ACTIVE " + maximum.get());
        }
    }
    static void result(int node, long bytes, long begin, boolean ok) {
        System.out.printf(Locale.ROOT, "RESULT %d %d %.9f %s%n", node, bytes, (System.nanoTime()-begin)/1e9, ok);
    }
    static void client(String host, int port, int node, boolean controlled) throws Exception {
        if (controlled) { ready(); go(); }
        long begin = System.nanoTime();
        try (Socket socket = connect(host, port); DataInputStream in = new DataInputStream(socket.getInputStream())) {
            long size = in.readLong(), expected = in.readLong(), count = 0; CRC32 crc = new CRC32(); byte[] b = new byte[BLOCK];
            while (count < size) { int n = in.read(b, 0, (int)Math.min(b.length, size-count));
                if (n < 0) throw new EOFException("Download incompleto"); crc.update(b, 0, n); count += n; }
            if (crc.getValue() != expected) throw new IOException("CRC32 divergente");
            result(node, count, begin, true);
        }
    }
    // Todos os peers recebem dados; peers internos tambem os enviam aos filhos.
    // A origem envia somente aos primeiros dois peers; nao centraliza os demais downloads.
    static void peer(int index, int port, long size, long expected, List<String> children, boolean controlled) throws Exception {
        try (ServerSocket ss = listener(port)) {
            String readyFile = System.getenv("READY_FILE");
            if (readyFile != null && !readyFile.isBlank()) Files.writeString(Path.of(readyFile), "ready");
            if (controlled) { ready(); go(); }
            else { System.out.println("Peer " + index + " pronto na porta " + port); }
            long begin = System.nanoTime();
            List<Socket> outgoing = new ArrayList<>(); List<DataOutputStream> outputs = new ArrayList<>();
            try {
                for (String child : children) {
                    int colon = child.lastIndexOf(':');
                    Socket socket = connect(child.substring(0, colon), Integer.parseInt(child.substring(colon+1)));
                    outgoing.add(socket); outputs.add(new DataOutputStream(socket.getOutputStream()));
                }
                Socket incoming = index == 0 ? null : ss.accept();
                try (incoming) {
                    DataInputStream in = incoming == null ? null : new DataInputStream(incoming.getInputStream());
                    if (in != null) { size = in.readLong(); expected = in.readLong(); }
                    for (DataOutputStream out : outputs) { out.writeLong(size); out.writeLong(expected); }
                    byte[] buffer = index == 0 ? CONTENT : new byte[BLOCK]; CRC32 crc = new CRC32(); long count = 0;
                    while (count < size) {
                        int n = (int)Math.min(BLOCK, size-count);
                        if (in != null) { n = in.read(buffer, 0, n); if (n < 0) throw new EOFException("Peer recebeu arquivo incompleto"); }
                        for (DataOutputStream out : outputs) out.write(buffer, 0, n);
                        if (index != 0) crc.update(buffer, 0, n); count += n;
                    }
                    for (DataOutputStream out : outputs) out.flush();
                    if (index != 0 && crc.getValue() != expected) throw new IOException("CRC32 divergente no peer " + index);
                    result(index, count, begin, true);
                }
            } finally { for (Socket s : outgoing) s.close(); }
        }
    }
    static final class Worker {
        final Process process; final BufferedReader output; final BufferedWriter input;
        Worker(List<String> arguments, Path errors) throws Exception {
            String java = Path.of(System.getProperty("java.home"), "bin", "java").toString();
            List<String> command = new ArrayList<>(List.of(java, "-Xms16m", "-Xmx64m", "-cp", System.getProperty("java.class.path"), "Main"));
            command.addAll(arguments);
            process = new ProcessBuilder(command).redirectError(errors.toFile()).start();
            output = process.inputReader(StandardCharsets.UTF_8); input = process.outputWriter(StandardCharsets.UTF_8);
            if (!"READY".equals(output.readLine())) throw new IOException("Worker nao iniciou. Veja " + errors);
        }
        void start() throws IOException { input.write("GO\n"); input.flush(); }
        List<String> finish() throws Exception {
            List<String> lines = output.lines().toList();
            if (!process.waitFor(TIMEOUT, TimeUnit.MILLISECONDS)) { process.destroyForcibly(); throw new IOException("Worker nao terminou"); }
            if (process.exitValue() != 0) throw new IOException("Worker terminou com erro " + process.exitValue());
            return lines;
        }
        void stop() { if (process.isAlive()) process.destroyForcibly(); }
    }
    static int freePort() throws IOException { try (ServerSocket s = new ServerSocket(0)) { return s.getLocalPort(); } }
    static List<String> args(Object... values) { return Arrays.stream(values).map(Object::toString).toList(); }
    static List<String> run(String mode, int clients, int pool, long size, long crc, Path logs, String tag) throws Exception {
        List<Worker> workers = new ArrayList<>(); List<String> results = new ArrayList<>();
        try {
            if (mode.equals("p2p")) {
                int[] ports = new int[clients+1]; Set<Integer> used = new HashSet<>();
                for (int i = 0; i < ports.length; i++) { do { ports[i] = freePort(); } while (!used.add(ports[i])); }
                for (int i = 0; i <= clients; i++) {
                    List<String> command = new ArrayList<>(args("_peer", i, ports[i], size, crc));
                    for (int child = 2*i+1; child <= Math.min(2*i+2, clients); child++) command.add("127.0.0.1:" + ports[child]);
                    workers.add(new Worker(command, logs.resolve(tag+"-peer"+i+".log")));
                }
                for (int i = workers.size()-1; i >= 0; i--) workers.get(i).start();
            } else {
                int port = freePort(); workers.add(new Worker(args("_server", mode, port, clients, pool, size, crc), logs.resolve(tag+"-server.log")));
                for (int i = 1; i <= clients; i++) workers.add(new Worker(args("_client", "127.0.0.1", port, i), logs.resolve(tag+"-client"+i+".log")));
                for (int i = 1; i < workers.size(); i++) workers.get(i).start();
            }
            for (Worker w : workers) results.addAll(w.finish());
            return results;
        } finally { for (Worker w : workers) w.stop(); }
    }
    static Map<String,String> options(String[] a, int start) {
        Map<String,String> result = new HashMap<>();
        for (int i = start; i < a.length; i += 2) {
            if (!a[i].startsWith("--") || i+1 >= a.length) throw new IllegalArgumentException("Use --opcao valor");
            result.put(a[i].substring(2), a[i+1]);
        }
        return result;
    }
    static int[] ints(String text) { return Arrays.stream(text.split(",")).mapToInt(Integer::parseInt).toArray(); }
    static void benchmark(String[] a) throws Exception {
        Map<String,String> o = options(a, 1); int[] sizes = ints(o.getOrDefault("sizes", "5,50,500"));
        int[] counts = ints(o.getOrDefault("clients", "2,4,8")); int repetitions = Integer.parseInt(o.getOrDefault("repeats", "3"));
        int pool = Integer.parseInt(o.getOrDefault("pool", "2")); Path out = Path.of(o.getOrDefault("out", "resultados"));
        if (repetitions < 1 || pool < 1 || Arrays.stream(sizes).anyMatch(v -> v < 1) || Arrays.stream(counts).anyMatch(v -> v < 1)) throw new IllegalArgumentException("Parametros devem ser positivos");
        Files.createDirectories(out); Path logs = out.resolve("logs"); Files.createDirectories(logs);
        String environment = "data_utc="+Instant.now()+"\nos="+System.getProperty("os.name")+" "+System.getProperty("os.version")+
            "\narquitetura="+System.getProperty("os.arch")+"\njava="+System.getProperty("java.version")+
            "\nprocessadores_logicos="+Runtime.getRuntime().availableProcessors()+"\nrede=TCP IPv4 loopback 127.0.0.1; processos JVM separados\n"+
            "tamanhos_MB="+Arrays.toString(sizes)+"\nclientes="+Arrays.toString(counts)+"\nrepeticoes="+repetitions+"\npool="+pool+
            "\nbloco_bytes="+BLOCK+"\nMB=1000000 bytes\n";
        Files.writeString(out.resolve("ambiente.txt"), environment);
        record Key(String mode, int mb, int nodes) {}
        Map<Key,List<Double>> grouped = new LinkedHashMap<>();
        try (PrintWriter raw = new PrintWriter(Files.newBufferedWriter(out.resolve("tempos.csv")))) {
            raw.println("modo,tamanho_mb,clientes,repeticao,no,bytes,tempo_s,crc_ok,max_envios_origem");
            Random random = new Random(2026); int experiment = 0;
            for (int mb : sizes) {
                long size = mb*1_000_000L, crc = checksum(size);
                for (int nodes : counts) for (int repeat = 1; repeat <= repetitions; repeat++) {
                    List<String> modes = new ArrayList<>(List.of("sequencial", "paralelo", "pool", "p2p")); Collections.shuffle(modes, random);
                    for (String mode : modes) {
                        String tag = mode+"-"+mb+"MB-"+nodes+"n-r"+repeat;
                        List<String> lines = run(mode, nodes, pool, size, crc, logs, tag);
                        int maximum = mode.equals("p2p") ? Math.min(2, nodes) : 0, received = 0;
                        for (String line : lines) if (line.startsWith("MAX_ACTIVE ")) maximum = Integer.parseInt(line.split(" ")[1]);
                        if ((mode.equals("sequencial") && maximum != 1) || (mode.equals("pool") && maximum > pool)) throw new IOException("Limite de concorrencia violado");
                        List<Double> times = grouped.computeIfAbsent(new Key(mode, mb, nodes), k -> new ArrayList<>());
                        for (String line : lines) if (line.startsWith("RESULT ")) {
                            String[] p = line.split(" "); int node = Integer.parseInt(p[1]); if (node == 0) continue;
                            long bytes = Long.parseLong(p[2]); double seconds = Double.parseDouble(p[3]);
                            if (bytes != size || !p[4].equals("true")) throw new IOException("Validacao de integridade falhou");
                            raw.printf(Locale.ROOT, "%s,%d,%d,%d,%d,%d,%.9f,true,%d%n", mode, mb, nodes, repeat, node, bytes, seconds, maximum);
                            times.add(seconds); received++;
                        }
                        if (received != nodes) throw new IOException("Numero inesperado de downloads");
                        raw.flush();
                        System.out.printf("[%d/%d] %s: %d downloads OK%n", ++experiment, sizes.length*counts.length*repetitions*4, tag, received);
                    }
                }
            }
        }
        try (PrintWriter summary = new PrintWriter(Files.newBufferedWriter(out.resolve("resumo.csv")))) {
            summary.println("modo,tamanho_mb,clientes,amostras,min_s,media_s,max_s");
            for (int mb : sizes) for (int n : counts) for (String mode : List.of("sequencial", "paralelo", "pool", "p2p")) {
                List<Double> times = grouped.get(new Key(mode, mb, n)); DoubleSummaryStatistics s = times.stream().mapToDouble(Double::doubleValue).summaryStatistics();
                summary.printf(Locale.ROOT, "%s,%d,%d,%d,%.9f,%.9f,%.9f%n", mode, mb, n, s.getCount(), s.getMin(), s.getAverage(), s.getMax());
            }
        }
        System.out.println("SUCESSO: quatro modos verificados; CSVs e ambiente em " + out.toAbsolutePath());
    }
    public static void main(String[] a) throws Exception {
        if (a.length == 0 || a[0].equals("--help")) {
            System.out.println("P2P - Atividade U2 / Sistemas Distribuidos\n"+
                "java -jar dist/p2p.jar benchmark [--sizes 5,50,500 --clients 2,4,8 --repeats 3 --pool 2 --out resultados]\n"+
                "java -jar dist/p2p.jar selftest\n"+
                "java -jar dist/p2p.jar servidor <sequencial|paralelo|pool> <porta> <clientes> <pool> <MB>\n"+
                "java -jar dist/p2p.jar cliente <host> <porta>\n"+
                "java -jar dist/p2p.jar peer <indice> <porta> <MB> [hostFilho:porta ...]\n"+
                "Peer 0 e a origem. Inicie os demais peers antes da origem. MB = 1.000.000 bytes."); return;
        }
        switch (a[0]) {
            case "benchmark" -> benchmark(a);
            case "selftest" -> benchmark(new String[]{"benchmark", "--sizes", "1", "--clients", "4", "--repeats", "1", "--pool", "2", "--out", "teste-rapido"});
            case "_server" -> server(a[1], Integer.parseInt(a[2]), Integer.parseInt(a[3]), Integer.parseInt(a[4]), Long.parseLong(a[5]), Long.parseLong(a[6]));
            case "servidor" -> { long size = Long.parseLong(a[5])*1_000_000; server(a[1], Integer.parseInt(a[2]), Integer.parseInt(a[3]), Integer.parseInt(a[4]), size, checksum(size)); }
            case "_client" -> client(a[1], Integer.parseInt(a[2]), Integer.parseInt(a[3]), true);
            case "cliente" -> client(a[1], Integer.parseInt(a[2]), 1, false);
            case "_peer" -> peer(Integer.parseInt(a[1]), Integer.parseInt(a[2]), Long.parseLong(a[3]), Long.parseLong(a[4]), Arrays.asList(a).subList(5, a.length), true);
            case "peer" -> { long size = Long.parseLong(a[3])*1_000_000; peer(Integer.parseInt(a[1]), Integer.parseInt(a[2]), size, checksum(size), Arrays.asList(a).subList(4, a.length), false); }
            default -> throw new IllegalArgumentException("Modo desconhecido. Execute --help");
        }
    }
}
