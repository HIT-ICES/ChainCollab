package chaincollab.newtranslator.oclrunner;

import java.io.File;
import java.util.List;

import org.eclipse.emf.common.util.Diagnostic;

public final class Main {
    private Main() {}

    public static void main(String[] args) {
        Args parsed = Args.parse(args);
        if (parsed == null) {
            System.err.println("Usage: --ecore <file.ecore> --ocl <file.ocl> --xmi <file.xmi>");
            System.exit(2);
            return;
        }

        List<Diagnostic> failures = OclValidator.validate(parsed.ecore, parsed.ocl, parsed.xmi);
        if (failures.isEmpty()) {
            System.out.println("OK: no OCL violations.");
            System.exit(0);
            return;
        }

        System.out.println("Violations found: " + failures.size());
        for (Diagnostic d : failures) {
            System.out.println(d.getMessage());
        }
        System.exit(1);
    }

    private static final class Args {
        final File ecore;
        final File ocl;
        final File xmi;

        private Args(File ecore, File ocl, File xmi) {
            this.ecore = ecore;
            this.ocl = ocl;
            this.xmi = xmi;
        }

        static Args parse(String[] args) {
            File ecore = null;
            File ocl = null;
            File xmi = null;
            for (int i = 0; i < args.length; i++) {
                String a = args[i];
                if ("--ecore".equals(a) && i + 1 < args.length) {
                    ecore = new File(args[++i]);
                } else if ("--ocl".equals(a) && i + 1 < args.length) {
                    ocl = new File(args[++i]);
                } else if ("--xmi".equals(a) && i + 1 < args.length) {
                    xmi = new File(args[++i]);
                }
            }
            if (ecore == null || ocl == null || xmi == null) {
                return null;
            }
            return new Args(ecore, ocl, xmi);
        }
    }
}
