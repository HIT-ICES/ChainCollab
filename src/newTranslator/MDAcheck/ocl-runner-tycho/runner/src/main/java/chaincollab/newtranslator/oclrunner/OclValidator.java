package chaincollab.newtranslator.oclrunner;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.eclipse.emf.common.util.Diagnostic;
import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.EValidator;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.resource.ResourceSet;
import org.eclipse.emf.ecore.resource.impl.ResourceSetImpl;
import org.eclipse.emf.ecore.util.Diagnostician;
import org.eclipse.emf.ecore.xmi.impl.EcoreResourceFactoryImpl;
import org.eclipse.emf.ecore.xmi.impl.XMIResourceFactoryImpl;
import org.eclipse.ocl.pivot.utilities.OCL;
import org.eclipse.ocl.pivot.utilities.PivotStandaloneSetup;
import org.eclipse.ocl.pivot.validation.ComposedEValidator;
import org.eclipse.ocl.xtext.completeocl.CompleteOCLStandaloneSetup;
import org.eclipse.ocl.xtext.completeocl.validation.CompleteOCLEObjectValidator;

public final class OclValidator {
    private OclValidator() {}

    public static List<Diagnostic> validate(File ecoreFile, File completeOclFile, File xmiFile) {
        PivotStandaloneSetup.doSetup();
        CompleteOCLStandaloneSetup.doSetup();

        ResourceSet resourceSet = new ResourceSetImpl();
        registerResourceFactories(resourceSet);

        EPackage ePackage = loadAndRegisterEcore(resourceSet, ecoreFile);
        OCL ocl = OCL.newInstance(resourceSet);

        // Install Complete OCL validator
        URI oclURI = URI.createFileURI(completeOclFile.getAbsolutePath());
        CompleteOCLEObjectValidator oclValidator = new CompleteOCLEObjectValidator(
                ePackage, oclURI, ocl.getEnvironmentFactory());
        boolean initialized = oclValidator.initialize(
            (org.eclipse.ocl.pivot.internal.utilities.EnvironmentFactoryInternal) ocl.getEnvironmentFactory());
        if (!initialized) {
            throw new IllegalStateException("Failed to initialize OCL validator - check OCL file for errors: " + completeOclFile);
        }

        // Create a local EValidator.Registry and install the OCL validator
        EValidator.Registry localRegistry = new org.eclipse.emf.ecore.impl.EValidatorRegistryImpl();
        // Copy existing validators
        EValidator existingValidator = EValidator.Registry.INSTANCE.getEValidator(ePackage);
        if (existingValidator != null) {
            localRegistry.put(ePackage, existingValidator);
        }
        // Install OCL validator on top
        ComposedEValidator.install(localRegistry, ePackage, oclValidator);

        // Create a Diagnostician that uses our local registry
        Diagnostician diagnostician = new Diagnostician(localRegistry);

        Resource xmi = loadXmi(resourceSet, xmiFile);
        List<Diagnostic> failures = new ArrayList<>();
        for (EObject root : xmi.getContents()) {
            Diagnostic diagnostic = diagnostician.validate(root);
            collectErrors(diagnostic, failures);
        }
        ocl.dispose();
        return failures;
    }

    private static void registerResourceFactories(ResourceSet resourceSet) {
        Map<String, Object> ext = resourceSet.getResourceFactoryRegistry().getExtensionToFactoryMap();
        ext.put("ecore", new EcoreResourceFactoryImpl());
        ext.put("xmi", new XMIResourceFactoryImpl());
        // Don't register default extension - let Xtext handle .ocl files
    }

    private static EPackage loadAndRegisterEcore(ResourceSet resourceSet, File ecoreFile) {
        URI uri = URI.createFileURI(ecoreFile.getAbsolutePath());
        Resource resource = resourceSet.getResource(uri, true);
        if (resource.getContents().isEmpty() || !(resource.getContents().get(0) instanceof EPackage)) {
            throw new IllegalArgumentException("Invalid .ecore: root is not an EPackage: " + ecoreFile);
        }
        EPackage ePackage = (EPackage) resource.getContents().get(0);
        resourceSet.getPackageRegistry().put(ePackage.getNsURI(), ePackage);

        // Register URI mapping for platform:/resource/ocltest/b2c.ecore -> actual file
        // This allows Complete OCL imports to resolve correctly outside Eclipse
        resourceSet.getURIConverter().getURIMap().put(
            URI.createURI("platform:/resource/ocltest/b2c.ecore"),
            uri
        );

        return ePackage;
    }

    private static Resource loadXmi(ResourceSet resourceSet, File xmiFile) {
        URI uri = URI.createFileURI(xmiFile.getAbsolutePath());
        return resourceSet.getResource(uri, true);
    }

    private static void collectErrors(Diagnostic diagnostic, List<Diagnostic> failures) {
        // OCL constraint violations are reported as WARNINGs by default
        // Treat both ERROR and WARNING as validation failures
        if (diagnostic.getSeverity() == Diagnostic.ERROR || diagnostic.getSeverity() == Diagnostic.WARNING) {
            // Only add leaf diagnostics (actual violations), not container diagnostics
            if (diagnostic.getChildren().isEmpty() ||
                diagnostic.getMessage().contains("constraint is violated")) {
                failures.add(diagnostic);
            }
        }
        for (Diagnostic child : diagnostic.getChildren()) {
            collectErrors(child, failures);
        }
    }
}
