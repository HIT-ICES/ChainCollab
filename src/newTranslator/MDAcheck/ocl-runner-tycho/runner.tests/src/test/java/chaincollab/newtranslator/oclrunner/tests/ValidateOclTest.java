package chaincollab.newtranslator.oclrunner.tests;

import java.io.File;
import java.nio.file.Path;
import java.util.List;

import org.eclipse.emf.common.util.Diagnostic;
import org.junit.Assert;
import org.junit.Test;

import chaincollab.newtranslator.oclrunner.OclValidator;

public class ValidateOclTest {
    @Test
    public void validateCompleteOclAgainstXmi() {
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
        if (value == null || value.isBlank()) {
            return defaultFile;
        }
        return new File(value);
    }
}

