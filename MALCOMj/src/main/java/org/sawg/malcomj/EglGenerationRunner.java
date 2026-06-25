package org.sawg.malcomj;

import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.epsilon.egl.EglTemplateFactoryModuleAdapter;
import org.eclipse.epsilon.emc.emf.InMemoryEmfModel;
import org.eclipse.epsilon.eol.execute.context.Variable;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Orchestrates Epsilon EGL model-to-text generation.
 * Runs .egl templates against EMF models to produce text output (e.g. CSP-M).
 *
 * <p>Vendored verbatim from FORGE
 * (forge.transformations/core/EglGenerationRunner.java); only the package
 * declaration differs. REMEDIATE and FORGE are separate workspaces.
 */
public class EglGenerationRunner {

    /**
     * Execute an EGL template against an EMF model and write the result to a file.
     *
     * @param eglTemplate path to the .egl template file
     * @param modelName   name the model is referred to in the EGL template
     * @param model       the input EMF resource
     * @param metamodel   the source EPackage
     * @param outputFile  path to write the generated text
     * @return the generated text
     * @throws Exception if parsing or execution fails
     */
    public String run(Path eglTemplate, String modelName, Resource model,
                      EPackage metamodel, Path outputFile) throws Exception {
        return run(eglTemplate, modelName, model, metamodel, outputFile, Collections.emptyMap());
    }

    /**
     * Execute an EGL template against an EMF model with injected variables
     * and write the result to a file.
     *
     * @param eglTemplate path to the .egl template file
     * @param modelName   name the model is referred to in the EGL template
     * @param model       the input EMF resource
     * @param metamodel   the source EPackage
     * @param outputFile  path to write the generated text
     * @param variables   name-value pairs to inject as read-only variables into the EGL context
     * @return the generated text
     * @throws Exception if parsing or execution fails
     */
    public String run(Path eglTemplate, String modelName, Resource model,
                      EPackage metamodel, Path outputFile,
                      Map<String, Object> variables) throws Exception {

        EglTemplateFactoryModuleAdapter module = new EglTemplateFactoryModuleAdapter();
        module.parse(eglTemplate.toUri());

        if (!module.getParseProblems().isEmpty()) {
            String problems = module.getParseProblems().stream()
                    .map(Object::toString)
                    .collect(Collectors.joining("\n"));
            throw new IllegalArgumentException("EGL parse errors in " + eglTemplate + ":\n" + problems);
        }

        // Wrap source model (read-only)
        InMemoryEmfModel source = new InMemoryEmfModel(modelName, model, metamodel);
        source.setReadOnLoad(false);
        source.setStoredOnDisposal(false);

        module.getContext().getModelRepository().addModel(source);

        // Inject variables into the EGL execution context
        if (variables != null) {
            for (Map.Entry<String, Object> entry : variables.entrySet()) {
                module.getContext().getFrameStack().put(
                        Variable.createReadOnlyVariable(entry.getKey(), entry.getValue()));
            }
        }

        try {
            String result = (String) module.execute();

            if (outputFile != null) {
                Files.createDirectories(outputFile.getParent());
                Files.writeString(outputFile, result);
            }

            return result;
        } finally {
            module.getContext().getModelRepository().dispose();
        }
    }
}
