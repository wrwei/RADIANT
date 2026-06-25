package org.sawg.malcomj;

import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.EAnnotation;
import org.eclipse.emf.ecore.EAttribute;
import org.eclipse.emf.ecore.EClass;
import org.eclipse.emf.ecore.EClassifier;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EOperation;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.EParameter;
import org.eclipse.emf.ecore.EReference;
import org.eclipse.emf.ecore.EStructuralFeature;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.resource.ResourceSet;
import org.eclipse.emf.ecore.resource.impl.ResourceSetImpl;
import org.eclipse.emf.ecore.util.EcoreUtil;
import org.eclipse.emf.ecore.xmi.impl.XMIResourceFactoryImpl;
import org.eclipse.emf.emfatic.core.generator.ecore.Builder;
import org.eclipse.emf.emfatic.core.lang.gen.parser.EmfaticParserDriver;
import org.eclipse.gymnast.runtime.core.parser.ParseContext;
import org.eclipse.gymnast.runtime.core.parser.ParseError;
import org.eclipse.gymnast.runtime.core.parser.ParseMessage;
import org.eclipse.gymnast.runtime.core.parser.ParseWarning;

import java.io.FileReader;
import java.io.IOException;
import java.io.PrintStream;
import java.io.Reader;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

/**
 * Parses an Emfatic file via the Eclipse Emfatic compiler and emits a
 * normalised JSON description for the D5 evaluation metrics package.
 *
 * Usage:
 *   java -cp ... org.sawg.malcomj.EmfaticHelper INPUT.emf [OUTPUT.json]
 *
 * Output JSON shape (always a single line, written to stdout if no output
 * path is given):
 * {
 *   "syntax_ok": bool,
 *   "errors":    [{"offset": int, "length": int, "message": string}, ...],
 *   "warnings":  [...],
 *   "packages":  [{
 *       "name": string, "ns_uri": string, "ns_prefix": string,
 *       "classes": [{
 *           "name": string,
 *           "abstract": bool,
 *           "interface": bool,
 *           "supertypes": [string, ...],
 *           "attributes": [{"name": string, "type": string, "lower": int, "upper": int, "id": bool}, ...],
 *           "references": [{"name": string, "type": string, "containment": bool, "lower": int, "upper": int}, ...],
 *           "operations": [{"name": string, "return_type": string, "parameters": [{"name": string, "type": string}, ...]}, ...]
 *       }, ...],
 *       "datatypes": [{"name": string, "instance_type": string}, ...],
 *       "enums":     [{"name": string, "literals": [string, ...]}, ...]
 *   }, ...]
 * }
 *
 * Exit code is always 0 on a clean run (syntax errors are reported in the
 * "syntax_ok": false field, not via the exit code). A non-zero exit code
 * means an unexpected runtime error.
 */
public final class EmfaticHelper {

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: EmfaticHelper INPUT.emf [OUTPUT.json]");
            System.exit(2);
        }
        Path input = Paths.get(args[0]);
        String json;
        try {
            json = parseEmfatic(input);
        } catch (RuntimeException | IOException ex) {
            json = "{\"syntax_ok\":false,\"errors\":[{\"offset\":0,\"length\":0,\"message\":"
                    + jsonString(ex.getClass().getSimpleName() + ": " + ex.getMessage())
                    + "}],\"warnings\":[],\"packages\":[]}";
        }
        if (args.length >= 2) {
            try {
                Files.writeString(Paths.get(args[1]), json, StandardCharsets.UTF_8);
            } catch (IOException ex) {
                System.err.println("Failed to write " + args[1] + ": " + ex.getMessage());
                System.exit(3);
            }
        } else {
            System.out.println(json);
        }
    }

    static String parseEmfatic(Path input) throws IOException {
        URI uri = URI.createFileURI(input.toAbsolutePath().toString());
        EmfaticParserDriver parser = new EmfaticParserDriver(uri);

        ParseContext ctx;
        try (Reader reader = new FileReader(input.toFile(), StandardCharsets.UTF_8)) {
            ctx = parser.parse(reader);
        }

        StringBuilder sb = new StringBuilder();
        sb.append('{');
        sb.append("\"syntax_ok\":").append(!ctx.hasErrors()).append(',');
        sb.append("\"errors\":").append(messages(ctx, ParseError.class)).append(',');
        sb.append("\"warnings\":").append(messages(ctx, ParseWarning.class)).append(',');

        List<EPackage> packages = new ArrayList<>();
        List<String> builderErrors = new ArrayList<>();
        if (!ctx.hasErrors()) {
            // Build an EMF Resource from the parse tree so we can walk EPackage/EClass etc.
            // Standalone EMF needs the XMI factory registered for .ecore so createResource
            // doesn't return null.
            ResourceSet resourceSet = new ResourceSetImpl();
            resourceSet.getResourceFactoryRegistry().getExtensionToFactoryMap()
                    .put("ecore", new XMIResourceFactoryImpl());
            Resource resource = resourceSet.createResource(
                    URI.createFileURI(input.toAbsolutePath().toString()
                            .replaceFirst("\\.emf$", ".ecore")));
            try {
                new Builder().build(ctx, resource, null);
                for (EObject root : resource.getContents()) {
                    if (root instanceof EPackage) {
                        packages.add((EPackage) root);
                    }
                }
            } catch (Exception ex) {
                builderErrors.add(ex.getClass().getSimpleName() + ": " + ex.getMessage());
            }
        }
        if (!builderErrors.isEmpty()) {
            sb.append("\"builder_errors\":[");
            for (int i = 0; i < builderErrors.size(); i++) {
                if (i > 0) sb.append(',');
                sb.append(jsonString(builderErrors.get(i)));
            }
            sb.append("],");
        }

        sb.append("\"packages\":[");
        for (int i = 0; i < packages.size(); i++) {
            if (i > 0) sb.append(',');
            renderPackage(sb, packages.get(i));
        }
        sb.append(']');
        sb.append('}');
        return sb.toString();
    }

    private static String messages(ParseContext ctx, Class<? extends ParseMessage> kind) {
        StringBuilder sb = new StringBuilder("[");
        boolean first = true;
        for (ParseMessage m : ctx.getMessages()) {
            if (!kind.isInstance(m)) continue;
            if (!first) sb.append(',');
            first = false;
            sb.append('{');
            sb.append("\"offset\":").append(m.getOffset()).append(',');
            sb.append("\"length\":").append(m.getLength()).append(',');
            sb.append("\"message\":").append(jsonString(String.valueOf(m.getMessage())));
            sb.append('}');
        }
        sb.append(']');
        return sb.toString();
    }

    private static void renderPackage(StringBuilder sb, EPackage pkg) {
        sb.append('{');
        sb.append("\"name\":").append(jsonString(pkg.getName())).append(',');
        sb.append("\"ns_uri\":").append(jsonString(pkg.getNsURI())).append(',');
        sb.append("\"ns_prefix\":").append(jsonString(pkg.getNsPrefix())).append(',');

        List<EClass> classes = new ArrayList<>();
        List<EClassifier> datatypes = new ArrayList<>();
        List<EClassifier> enums = new ArrayList<>();
        for (EClassifier c : pkg.getEClassifiers()) {
            if (c instanceof EClass) {
                classes.add((EClass) c);
            } else if (c instanceof org.eclipse.emf.ecore.EEnum) {
                enums.add(c);
            } else {
                datatypes.add(c);
            }
        }

        sb.append("\"classes\":[");
        for (int i = 0; i < classes.size(); i++) {
            if (i > 0) sb.append(',');
            renderClass(sb, classes.get(i));
        }
        sb.append("],");

        sb.append("\"datatypes\":[");
        for (int i = 0; i < datatypes.size(); i++) {
            if (i > 0) sb.append(',');
            EClassifier c = datatypes.get(i);
            sb.append('{');
            sb.append("\"name\":").append(jsonString(c.getName())).append(',');
            sb.append("\"instance_type\":").append(
                    jsonString(c.getInstanceTypeName() != null ? c.getInstanceTypeName() : ""));
            sb.append('}');
        }
        sb.append("],");

        sb.append("\"enums\":[");
        for (int i = 0; i < enums.size(); i++) {
            if (i > 0) sb.append(',');
            org.eclipse.emf.ecore.EEnum e = (org.eclipse.emf.ecore.EEnum) enums.get(i);
            sb.append('{');
            sb.append("\"name\":").append(jsonString(e.getName())).append(',');
            sb.append("\"literals\":[");
            List<org.eclipse.emf.ecore.EEnumLiteral> lits = e.getELiterals();
            for (int j = 0; j < lits.size(); j++) {
                if (j > 0) sb.append(',');
                sb.append(jsonString(lits.get(j).getLiteral()));
            }
            sb.append(']');
            sb.append('}');
        }
        sb.append(']');

        sb.append('}');
    }

    private static void renderClass(StringBuilder sb, EClass cls) {
        sb.append('{');
        sb.append("\"name\":").append(jsonString(cls.getName())).append(',');
        sb.append("\"abstract\":").append(cls.isAbstract()).append(',');
        sb.append("\"interface\":").append(cls.isInterface()).append(',');

        sb.append("\"supertypes\":[");
        List<EClass> sup = cls.getESuperTypes();
        for (int i = 0; i < sup.size(); i++) {
            if (i > 0) sb.append(',');
            sb.append(jsonString(sup.get(i).getName()));
        }
        sb.append("],");

        sb.append("\"attributes\":[");
        boolean first = true;
        for (EStructuralFeature f : cls.getEStructuralFeatures()) {
            if (!(f instanceof EAttribute)) continue;
            EAttribute a = (EAttribute) f;
            if (!first) sb.append(',');
            first = false;
            sb.append('{');
            sb.append("\"name\":").append(jsonString(a.getName())).append(',');
            sb.append("\"type\":").append(jsonString(typeName(a.getEType()))).append(',');
            sb.append("\"lower\":").append(a.getLowerBound()).append(',');
            sb.append("\"upper\":").append(a.getUpperBound()).append(',');
            sb.append("\"id\":").append(a.isID());
            sb.append('}');
        }
        sb.append("],");

        sb.append("\"references\":[");
        first = true;
        for (EStructuralFeature f : cls.getEStructuralFeatures()) {
            if (!(f instanceof EReference)) continue;
            EReference r = (EReference) f;
            if (!first) sb.append(',');
            first = false;
            sb.append('{');
            sb.append("\"name\":").append(jsonString(r.getName())).append(',');
            sb.append("\"type\":").append(jsonString(typeName(r.getEType()))).append(',');
            sb.append("\"containment\":").append(r.isContainment()).append(',');
            sb.append("\"lower\":").append(r.getLowerBound()).append(',');
            sb.append("\"upper\":").append(r.getUpperBound());
            sb.append('}');
        }
        sb.append("],");

        sb.append("\"operations\":[");
        List<EOperation> ops = cls.getEOperations();
        for (int i = 0; i < ops.size(); i++) {
            if (i > 0) sb.append(',');
            EOperation op = ops.get(i);
            sb.append('{');
            sb.append("\"name\":").append(jsonString(op.getName())).append(',');
            sb.append("\"return_type\":").append(
                    jsonString(op.getEType() != null ? typeName(op.getEType()) : "void")).append(',');
            sb.append("\"parameters\":[");
            List<EParameter> ps = op.getEParameters();
            for (int j = 0; j < ps.size(); j++) {
                if (j > 0) sb.append(',');
                EParameter p = ps.get(j);
                sb.append('{');
                sb.append("\"name\":").append(jsonString(p.getName())).append(',');
                sb.append("\"type\":").append(
                        jsonString(p.getEType() != null ? typeName(p.getEType()) : ""));
                sb.append('}');
            }
            sb.append(']');
            sb.append('}');
        }
        sb.append(']');

        sb.append('}');
    }

    private static String typeName(EClassifier c) {
        if (c == null) return "";
        return c.getName() == null ? "" : c.getName();
    }

    /** RFC 8259 string escaping, sufficient for source-code identifiers and English diagnostics. */
    private static String jsonString(String s) {
        if (s == null) return "null";
        StringBuilder sb = new StringBuilder(s.length() + 2);
        sb.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"':  sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n");  break;
                case '\r': sb.append("\\r");  break;
                case '\t': sb.append("\\t");  break;
                case '\b': sb.append("\\b");  break;
                case '\f': sb.append("\\f");  break;
                default:
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        sb.append('"');
        return sb.toString();
    }
}
