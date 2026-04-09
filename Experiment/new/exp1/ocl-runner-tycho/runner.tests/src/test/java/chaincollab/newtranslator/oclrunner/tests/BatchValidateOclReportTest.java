package chaincollab.newtranslator.oclrunner.tests;

import java.io.File;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.eclipse.emf.common.util.Diagnostic;
import org.junit.Assert;
import org.junit.Assume;
import org.junit.Test;

import chaincollab.newtranslator.oclrunner.OclValidator;

/**
 * Batch validate all XMI models under a directory and write a JSON report.
 *
 * Inputs via system properties (passed by Tycho Surefire):
 * - ecore: path to .ecore
 * - ocl: path to .ocl (Complete OCL)
 * - xmiDir: directory to scan (required to enable this test; otherwise skipped)
 * - xmiGlob: glob-like suffix filter (optional; defaults to ".xmi")
 * - reportDir: output directory (optional; defaults to "target/ocl-report")
 * - writePerModelJson: true/false (optional; default true)
 * - failOnViolation: true/false (optional; default false)
 */
public class BatchValidateOclReportTest {
    private static final Pattern OCL_CONSTRAINT_VIOLATED = Pattern.compile("The '([^']+)' constraint is violated.*");
    private static final Pattern EMF_REQUIRED_FEATURE = Pattern.compile("The required feature '([^']+)' of '([^']+)' must be set");
    private static final Pattern OCL_CONSTRAINT_RESULT_INVALID = Pattern.compile("The '([^']+)' constraint result is invalid for '([^']+)'.*");
    private static final Pattern OCL_NULL_SOURCE = Pattern.compile(".*Null source for '([^']+)'.*");

    @Test
    public void batchValidateAndWriteJsonReport() throws Exception {
        Path cwd = Path.of("").toAbsolutePath().normalize();

        File ecore = resolveFile("ecore", cwd.resolve("MDAcheck/b2c.ecore").toFile());
        File ocl = resolveFile("ocl", cwd.resolve("MDAcheck/check.ocl").toFile());
        MeaningResolver meaningResolver = MeaningResolver.fromCompleteOclFile(ocl);

        String xmiDirProp = System.getProperty("xmiDir");
        Assume.assumeTrue("xmiDir is not set; skipping batch report test", !isUnset(xmiDirProp));
        Path xmiDir = resolveExistingDir(xmiDirProp);
        Assume.assumeTrue("xmiDir does not exist: " + xmiDir, Files.isDirectory(xmiDir));

        String xmiGlob = System.getProperty("xmiGlob");
        if (isUnset(xmiGlob)) {
            xmiGlob = ".xmi";
        }

        Path reportDir = resolvePath("reportDir", cwd.resolve("target/ocl-report"));
        boolean writePerModelJson = resolveBoolean("writePerModelJson", true);
        boolean failOnViolation = resolveBoolean("failOnViolation", false);

        Files.createDirectories(reportDir);
        Path perModelDir = reportDir.resolve("models");
        if (writePerModelJson) {
            Files.createDirectories(perModelDir);
        }

        List<Path> xmis = listXmiFiles(xmiDir, xmiGlob);
        long startedAt = System.nanoTime();

        List<ModelResult> results = new ArrayList<>(xmis.size());
        int okCount = 0;
        int violationModels = 0;
        int totalViolations = 0;

        System.out.println("=== OCL Batch Validation ===");
        System.out.println("Ecore:    " + ecore.getAbsolutePath());
        System.out.println("OCL:      " + ocl.getAbsolutePath());
        System.out.println("XMI dir:  " + xmiDir);
        System.out.println("Filter:   " + xmiGlob);
        System.out.println("Report:   " + reportDir.toAbsolutePath());
        System.out.println("Models:   " + xmis.size());

        for (int i = 0; i < xmis.size(); i++) {
            Path xmi = xmis.get(i);
            long modelStart = System.nanoTime();
            List<Diagnostic> failures;
            String error = null;
            try {
                failures = OclValidator.validate(ecore, ocl, xmi.toFile());
            } catch (RuntimeException ex) {
                failures = List.of();
                error = ex.toString();
            }
            long modelMs = (System.nanoTime() - modelStart) / 1_000_000L;

            boolean ok = (error == null) && failures.isEmpty();
            if (ok) {
                okCount++;
            } else {
                violationModels++;
            }
            totalViolations += failures.size();

            ModelResult r = new ModelResult(
                    xmiDir.relativize(xmi).toString().replace('\\', '/'),
                    xmi.toString(),
                    ok,
                    failures,
                    error,
                    modelMs,
                    meaningResolver
            );
            results.add(r);

            if (writePerModelJson) {
                String safeName = r.relativePath.replace('/', '_');
                if (!safeName.toLowerCase(Locale.ROOT).endsWith(".json")) {
                    safeName = safeName + ".json";
                }
                Path out = perModelDir.resolve(safeName);
                writeUtf8(out, toModelJson(r));
            }

            if ((i + 1) % 10 == 0 || i + 1 == xmis.size()) {
                System.out.println("Progress: " + (i + 1) + "/" + xmis.size());
            }
        }

        long durationMs = (System.nanoTime() - startedAt) / 1_000_000L;

        String reportJson = toReportJson(ecore, ocl, xmiDir, xmiGlob, results, okCount, violationModels, totalViolations, durationMs);
        Path reportFile = reportDir.resolve("report.json");
        writeUtf8(reportFile, reportJson);

        String reportMd = toReportMarkdown(xmiDir, results, okCount, violationModels, totalViolations, durationMs);
        Path reportMdFile = reportDir.resolve("report.md");
        writeUtf8(reportMdFile, reportMd);

        String summary = "Summary: total=" + results.size()
                + ", ok=" + okCount
                + ", not_ok=" + violationModels
                + ", total_violations=" + totalViolations
                + ", durationMs=" + durationMs;
        System.out.println(summary);
        System.out.println("JSON report: " + reportFile.toAbsolutePath());
        System.out.println("MD report:   " + reportMdFile.toAbsolutePath());

        if (failOnViolation && (violationModels > 0)) {
            Assert.fail("OCL violations found. " + summary);
        }
    }

    private static List<Path> listXmiFiles(Path xmiDir, String xmiGlob) {
        try (Stream<Path> s = Files.walk(xmiDir)) {
            return s.filter(Files::isRegularFile)
                    .filter(p -> matchesSuffix(p.getFileName().toString(), xmiGlob))
                    .sorted(Comparator.comparing(p -> xmiDir.relativize(p).toString()))
                    .collect(Collectors.toList());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static boolean matchesSuffix(String fileName, String suffixOrExt) {
        if (suffixOrExt == null || suffixOrExt.isBlank()) {
            return fileName.toLowerCase(Locale.ROOT).endsWith(".xmi");
        }
        String s = suffixOrExt.trim();
        if (!s.startsWith(".")) {
            s = "." + s;
        }
        return fileName.toLowerCase(Locale.ROOT).endsWith(s.toLowerCase(Locale.ROOT));
    }

    private static File resolveFile(String key, File defaultFile) {
        String value = System.getProperty(key);
        if (isUnset(value)) {
            return defaultFile;
        }
        return resolveExistingFile(value, defaultFile);
    }

    private static Path resolvePath(String key, Path defaultPath) {
        String value = System.getProperty(key);
        if (isUnset(value)) {
            return defaultPath;
        }
        return resolvePathPreferProjectRoot(value, defaultPath);
    }

    private static boolean resolveBoolean(String key, boolean defaultValue) {
        String value = System.getProperty(key);
        if (isUnset(value)) {
            return defaultValue;
        }
        return "true".equalsIgnoreCase(value.trim()) || "1".equals(value.trim()) || "yes".equalsIgnoreCase(value.trim());
    }

    private static boolean isUnset(String value) {
        return value == null || value.isBlank() || "null".equalsIgnoreCase(value.trim());
    }

    private static void writeUtf8(Path path, String content) {
        try {
            Files.createDirectories(path.getParent());
            Files.writeString(path, content, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String toReportJson(File ecore, File ocl, Path xmiDir, String xmiGlob,
                                       List<ModelResult> results,
                                       int okCount, int violationModels, int totalViolations,
                                       long durationMs) {
        StringBuilder sb = new StringBuilder(1024 + results.size() * 256);
        sb.append("{\n");
        sb.append("  \"generatedAt\": ").append(jsonString(Instant.now().toString())).append(",\n");
        sb.append("  \"ecore\": ").append(jsonString(ecore.getAbsolutePath())).append(",\n");
        sb.append("  \"ocl\": ").append(jsonString(ocl.getAbsolutePath())).append(",\n");
        sb.append("  \"xmiDir\": ").append(jsonString(xmiDir.toString())).append(",\n");
        sb.append("  \"xmiGlob\": ").append(jsonString(xmiGlob)).append(",\n");
        sb.append("  \"summary\": {\n");
        sb.append("    \"total\": ").append(results.size()).append(",\n");
        sb.append("    \"ok\": ").append(okCount).append(",\n");
        sb.append("    \"notOk\": ").append(violationModels).append(",\n");
        sb.append("    \"totalViolations\": ").append(totalViolations).append(",\n");
        sb.append("    \"durationMs\": ").append(durationMs).append("\n");
        sb.append("  },\n");
        sb.append("  \"models\": [\n");
        for (int i = 0; i < results.size(); i++) {
            sb.append(indentLines(toModelJson(results.get(i)), "    "));
            if (i + 1 < results.size()) {
                sb.append(",");
            }
            sb.append("\n");
        }
        sb.append("  ]\n");
        sb.append("}\n");
        return sb.toString();
    }

    private static String toModelJson(ModelResult r) {
        StringBuilder sb = new StringBuilder(256 + r.failures.size() * 128);
        sb.append("{\n");
        sb.append("  \"relativePath\": ").append(jsonString(r.relativePath)).append(",\n");
        sb.append("  \"absolutePath\": ").append(jsonString(r.absolutePath)).append(",\n");
        sb.append("  \"ok\": ").append(r.ok).append(",\n");
        sb.append("  \"durationMs\": ").append(r.durationMs).append(",\n");
        sb.append("  \"error\": ").append(r.error == null ? "null" : jsonString(r.error)).append(",\n");
        sb.append("  \"violationCount\": ").append(r.failures.size()).append(",\n");
        sb.append("  \"violations\": [\n");
        for (int i = 0; i < r.failures.size(); i++) {
            Diagnostic d = r.failures.get(i);
            ViolationInfo info = r.meaningResolver.resolve(d.getMessage());
            sb.append("    {\n");
            sb.append("      \"severity\": ").append(d.getSeverity()).append(",\n");
            sb.append("      \"kind\": ").append(jsonString(info.kind)).append(",\n");
            sb.append("      \"code\": ").append(info.code == null ? "null" : jsonString(info.code)).append(",\n");
            sb.append("      \"meaningZh\": ").append(info.meaningZh == null ? "null" : jsonString(info.meaningZh)).append(",\n");
            sb.append("      \"message\": ").append(jsonString(d.getMessage())).append("\n");
            sb.append("    }");
            if (i + 1 < r.failures.size()) {
                sb.append(",");
            }
            sb.append("\n");
        }
        sb.append("  ]\n");
        sb.append("}");
        return sb.toString();
    }

    private static String indentLines(String s, String indent) {
        return Stream.of(s.split("\n", -1))
                .map(line -> indent + line)
                .collect(Collectors.joining("\n"));
    }

    private static String jsonString(String s) {
        return "\"" + jsonEscape(s) + "\"";
    }

    private static String jsonEscape(String s) {
        StringBuilder sb = new StringBuilder(s.length() + 16);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '\\': sb.append("\\\\"); break;
                case '"': sb.append("\\\""); break;
                case '\b': sb.append("\\b"); break;
                case '\f': sb.append("\\f"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        return sb.toString();
    }

    private static final class ModelResult {
        final String relativePath;
        final String absolutePath;
        final boolean ok;
        final List<Diagnostic> failures;
        final String error;
        final long durationMs;
        final MeaningResolver meaningResolver;

        ModelResult(String relativePath, String absolutePath, boolean ok, List<Diagnostic> failures, String error, long durationMs, MeaningResolver meaningResolver) {
            this.relativePath = relativePath;
            this.absolutePath = absolutePath;
            this.ok = ok;
            this.failures = failures;
            this.error = error;
            this.durationMs = durationMs;
            this.meaningResolver = meaningResolver;
        }
    }

    private static final class ViolationInfo {
        final String kind;
        final String code;
        final String meaningZh;

        ViolationInfo(String kind, String code, String meaningZh) {
            this.kind = kind;
            this.code = code;
            this.meaningZh = meaningZh;
        }
    }

    /**
     * Resolves a human-friendly meaning from raw EMF/OCL diagnostic messages.
     *
     * For OCL constraint violations, the "code" is typically {@code Context::InvariantName} and the meaning
     * is derived from the closest {@code -- ...} comment above that {@code inv} in {@code check.ocl}.
     */
    private static final class MeaningResolver {
        private final Map<String, String> meaningByOclCode;
        private final Map<String, String> meaningByInvName;

        private MeaningResolver(Map<String, String> meaningByOclCode, Map<String, String> meaningByInvName) {
            this.meaningByOclCode = meaningByOclCode;
            this.meaningByInvName = meaningByInvName;
        }

        static MeaningResolver fromCompleteOclFile(File completeOclFile) {
            if (completeOclFile == null || !completeOclFile.exists()) {
                return new MeaningResolver(Map.of(), Map.of());
            }
            try {
                List<String> lines = Files.readAllLines(completeOclFile.toPath(), StandardCharsets.UTF_8);
                Map<String, String> byCode = new HashMap<>();
                Map<String, String> byInv = new HashMap<>();

                String currentContext = null;
                for (int i = 0; i < lines.size(); i++) {
                    String trimmed = lines.get(i).trim();
                    if (trimmed.startsWith("context ")) {
                        currentContext = trimmed.substring("context ".length()).trim().split("\\s+")[0];
                        continue;
                    }
                    if (!trimmed.startsWith("inv ")) {
                        continue;
                    }
                    if (currentContext == null || currentContext.isBlank()) {
                        continue;
                    }
                    String invName = trimmed.substring("inv ".length()).trim();
                    int colon = invName.indexOf(':');
                    if (colon >= 0) {
                        invName = invName.substring(0, colon).trim();
                    }
                    if (invName.isBlank()) {
                        continue;
                    }

                    String key = currentContext + "::" + invName;
                    String meaning = findMeaningNear(lines, i);
                    if (meaning != null && !meaning.isBlank()) {
                        byCode.putIfAbsent(key, meaning);
                        byInv.putIfAbsent(invName, meaning);
                    }
                }

                return new MeaningResolver(byCode, byInv);
            } catch (IOException e) {
                return new MeaningResolver(Map.of(), Map.of());
            }
        }

        ViolationInfo resolve(String rawMessage) {
            if (rawMessage == null) {
                return new ViolationInfo("UNKNOWN", null, null);
            }

            Matcher m1 = OCL_CONSTRAINT_VIOLATED.matcher(rawMessage);
            if (m1.matches()) {
                String code = m1.group(1);
                String meaning = meaningByOclCode.get(code);
                if (meaning == null) {
                    String invName = code.contains("::") ? code.substring(code.indexOf("::") + 2) : code;
                    meaning = meaningByInvName.get(invName);
                }
                if (meaning == null) {
                    meaning = "违反约束：" + code;
                }
                return new ViolationInfo("OCL", code, meaning);
            }

            Matcher emf = EMF_REQUIRED_FEATURE.matcher(rawMessage);
            if (emf.matches()) {
                String feature = emf.group(1);
                return new ViolationInfo("EMF", "EMF_REQUIRED_FEATURE", "必填字段未设置：" + feature);
            }

            Matcher invalid = OCL_CONSTRAINT_RESULT_INVALID.matcher(rawMessage);
            if (invalid.matches()) {
                String constraint = invalid.group(1);
                Matcher nullSource = OCL_NULL_SOURCE.matcher(rawMessage);
                if (nullSource.matches()) {
                    String ref = nullSource.group(1);
                    return new ViolationInfo("OCL", "OCL_EVAL_NULL_SOURCE", "约束求值失败（空值）：" + constraint + " / " + ref);
                }
                return new ViolationInfo("OCL", "OCL_EVAL_INVALID_RESULT", "约束求值失败（结果非法）：" + constraint);
            }

            return new ViolationInfo("UNKNOWN", "UNKNOWN", null);
        }

        private static String findMeaningNear(List<String> lines, int invLineIndex) {
            String direct = collectCommentBlockAbove(lines, invLineIndex - 1);
            String cleaned = cleanMeaning(direct);
            if (cleaned != null) {
                return cleaned;
            }

            int j = invLineIndex - 1;
            while (j >= 0 && lines.get(j).trim().isBlank()) {
                j--;
            }
            if (j >= 0 && lines.get(j).trim().startsWith("context ")) {
                String ctx = collectCommentBlockAbove(lines, j - 1);
                return cleanMeaning(ctx);
            }
            return null;
        }

        private static String collectCommentBlockAbove(List<String> lines, int startIndex) {
            List<String> collected = new ArrayList<>();
            int i = startIndex;
            while (i >= 0) {
                String t = lines.get(i).trim();
                if (t.isBlank()) {
                    if (!collected.isEmpty()) {
                        break;
                    }
                    i--;
                    continue;
                }
                if (!t.startsWith("--")) {
                    break;
                }
                collected.add(t.substring(2).trim());
                i--;
            }
            if (collected.isEmpty()) {
                return null;
            }
            StringBuilder sb = new StringBuilder();
            for (int k = collected.size() - 1; k >= 0; k--) {
                String s = collected.get(k);
                if (!s.isBlank()) {
                    if (sb.length() > 0) {
                        sb.append(' ');
                    }
                    sb.append(s);
                }
            }
            return sb.toString().trim();
        }

        private static String cleanMeaning(String meaning) {
            if (meaning == null) {
                return null;
            }
            String m = meaning.trim();
            if (m.isBlank()) {
                return null;
            }
            if (m.matches("=+.*") || m.matches("-+.*") || m.contains("============")) {
                return null;
            }
            return m;
        }
    }

    private static String toReportMarkdown(Path xmiDir,
                                          List<ModelResult> results,
                                          int okCount, int violationModels, int totalViolations,
                                          long durationMs) {
        StringBuilder sb = new StringBuilder(1024 + results.size() * 64);
        sb.append("# OCL Batch Report\n\n");
        sb.append("- XMI dir: `").append(xmiDir.toString()).append("`\n");
        sb.append("- Total: ").append(results.size()).append("\n");
        sb.append("- OK: ").append(okCount).append("\n");
        sb.append("- Not OK: ").append(violationModels).append("\n");
        sb.append("- Total violations: ").append(totalViolations).append("\n");
        sb.append("- Duration (ms): ").append(durationMs).append("\n\n");

        sb.append("| Model | OK | Violations | Duration (ms) |\n");
        sb.append("|---|---:|---:|---:|\n");
        for (ModelResult r : results) {
            sb.append("| `").append(r.relativePath).append("` | ")
              .append(r.ok ? "yes" : "no").append(" | ")
              .append(r.failures.size()).append(" | ")
              .append(r.durationMs).append(" |\n");
        }
        sb.append("\n");
        sb.append("Per-model JSON files are in `models/`.\n");
        return sb.toString();
    }

    private static File resolveExistingFile(String value, File fallback) {
        Path p = Path.of(value);
        if (p.isAbsolute()) {
            return p.toFile();
        }

        String mm = System.getProperty("maven.multiModuleProjectDirectory");
        if (mm != null && !mm.isBlank()) {
            Path candidate = Path.of(mm).resolve(p).toAbsolutePath().normalize();
            if (candidate.toFile().exists()) {
                return candidate.toFile();
            }
        }

        Path cwd = Path.of("").toAbsolutePath().normalize();
        Path dir = cwd;
        for (int i = 0; i < 12; i++) {
            Path candidate = dir.resolve(p).normalize();
            if (candidate.toFile().exists()) {
                return candidate.toFile();
            }
            dir = dir.getParent();
            if (dir == null) {
                break;
            }
        }

        Path last = cwd.resolve(p).normalize();
        if (last.toFile().exists()) {
            return last.toFile();
        }
        return fallback;
    }

    private static Path resolvePathPreferProjectRoot(String value, Path fallback) {
        Path p = Path.of(value);
        if (p.isAbsolute()) {
            return p.toAbsolutePath().normalize();
        }

        String mm = System.getProperty("maven.multiModuleProjectDirectory");
        if (mm != null && !mm.isBlank()) {
            return Path.of(mm).resolve(p).toAbsolutePath().normalize();
        }

        Path cwd = Path.of("").toAbsolutePath().normalize();
        Path dir = cwd;
        for (int i = 0; i < 12; i++) {
            Path candidate = dir.resolve(p).normalize();
            if (candidate.getParent() != null && Files.isDirectory(candidate.getParent())) {
                return candidate.toAbsolutePath().normalize();
            }
            dir = dir.getParent();
            if (dir == null) {
                break;
            }
        }

        return fallback.toAbsolutePath().normalize();
    }

    private static Path resolveExistingDir(String value) {
        Path p = Path.of(value);
        if (p.isAbsolute()) {
            return p.toAbsolutePath().normalize();
        }

        String mm = System.getProperty("maven.multiModuleProjectDirectory");
        if (mm != null && !mm.isBlank()) {
            Path candidate = Path.of(mm).resolve(p).toAbsolutePath().normalize();
            if (Files.isDirectory(candidate)) {
                return candidate;
            }
        }

        Path cwd = Path.of("").toAbsolutePath().normalize();
        Path dir = cwd;
        for (int i = 0; i < 12; i++) {
            Path candidate = dir.resolve(p).normalize();
            if (Files.isDirectory(candidate)) {
                return candidate.toAbsolutePath().normalize();
            }
            dir = dir.getParent();
            if (dir == null) {
                break;
            }
        }

        return cwd.resolve(p).toAbsolutePath().normalize();
    }
}
