package chaincollab.newtranslator.oclrunner.tests;

import java.io.File;
import java.nio.file.Path;
import java.util.List;

import org.eclipse.emf.common.util.Diagnostic;
import org.junit.Assert;
import org.junit.Assume;
import org.junit.Test;

import chaincollab.newtranslator.oclrunner.OclValidator;

public class ValidateOclTest {
    @Test
    public void validateCompleteOclAgainstXmi() {
        String xmiDirProp = System.getProperty("xmiDir");
        Assume.assumeTrue("xmiDir is set; skipping single-file validation test", isUnset(xmiDirProp));

        Path cwd = Path.of("").toAbsolutePath().normalize();
        File ecore = resolveArg("ecore", cwd.resolve("MDAcheck/b2c.ecore").toFile());
        File ocl = resolveArg("ocl", cwd.resolve("MDAcheck/check.ocl").toFile());
        File xmi = resolveArg("xmi", cwd.resolve("MDAcheck/chaincode.xmi").toFile());

        List<Diagnostic> failures = OclValidator.validate(ecore, ocl, xmi);

        // Always print validation result
        System.out.println("=== OCL Validation Result ===");
        System.out.println("Ecore: " + ecore.getAbsolutePath());
        System.out.println("OCL:   " + ocl.getAbsolutePath());
        System.out.println("XMI:   " + xmi.getAbsolutePath());
        System.out.println("Violations found: " + failures.size());

        if (!failures.isEmpty()) {
            StringBuilder sb = new StringBuilder();
            sb.append("Constraint violations: ").append(failures.size()).append("\n");
            for (Diagnostic d : failures) {
                sb.append(d.getMessage()).append("\n");
            }
            Assert.fail(sb.toString());
        }
    }

    private static File resolveArg(String key, File defaultFile) {
        String value = System.getProperty(key);
        if (isUnset(value)) {
            return defaultFile;
        }
        return resolveFile(value, defaultFile);
    }

    private static boolean isUnset(String value) {
        return value == null || value.isBlank() || "null".equalsIgnoreCase(value.trim());
    }

    private static File resolveFile(String value, File fallback) {
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
}
