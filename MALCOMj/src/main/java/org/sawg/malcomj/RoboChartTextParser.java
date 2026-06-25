package org.sawg.malcomj;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.EClass;
import org.eclipse.emf.ecore.EFactory;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.EStructuralFeature;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.resource.ResourceSet;
import org.eclipse.emf.ecore.resource.impl.ResourceSetImpl;
import org.eclipse.emf.ecore.xmi.impl.XMIResourceFactoryImpl;

/**
 * Parses a RoboChart text file (the {@code .txt} output of MALCOMp's
 * {@code state_machine_extraction} stage) into an EMF model conforming to
 * {@code robochart.ecore}.
 *
 * <p>This is intentionally minimal: it extracts the state-machine name,
 * its initial junction(s), state declarations, and transition declarations
 * with their {@code source}/{@code target} node references. Triggers,
 * conditions, actions, variables, constants, events, and functions are not
 * modelled — only the structure required for requirement-to-state-machine
 * traceability.
 *
 * <p>Usage:
 * <pre>
 *   --input &lt;path/to/result_behaviour_model.rct&gt;
 *   --output &lt;path/to/AUV.robochart&gt;
 *   --metamodel &lt;path/to/robochart.ecore&gt;
 * </pre>
 */
public class RoboChartTextParser {

    private static final Pattern LINE_COMMENT      = Pattern.compile("//[^\\n]*");
    private static final Pattern STM_HEADER        = Pattern.compile("\\bstm\\s+(\\w+)\\s*\\{");
    private static final Pattern INITIAL           = Pattern.compile("\\binitial\\s+(\\w+)\\b");
    private static final Pattern STATE_HEADER      = Pattern.compile("\\bstate\\s+(\\w+)\\s*\\{");
    private static final Pattern TRANSITION_HEADER = Pattern.compile("\\btransition\\s+(\\w+)\\s*\\{");
    private static final Pattern FROM_TO           = Pattern.compile("\\bfrom\\s+(\\w+).*?\\bto\\s+(\\w+)", Pattern.DOTALL);

    public static void main(String[] args) throws Exception {
        String input = null, output = null, metamodel = null;
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--input":     input     = args[++i]; break;
                case "--output":    output    = args[++i]; break;
                case "--metamodel": metamodel = args[++i]; break;
                default:
                    System.err.println("Unknown argument: " + args[i]);
                    System.exit(1);
            }
        }
        if (input == null || output == null || metamodel == null) {
            System.err.println("Usage: --input <stm.txt> --output <model.robochart> --metamodel <robochart.ecore>");
            System.exit(1);
        }

        EPackage pkg = loadMetamodel(metamodel);
        EFactory factory = pkg.getEFactoryInstance();

        String text = Files.readString(Path.of(input));
        text = LINE_COMMENT.matcher(text).replaceAll("");

        EObject rcPackage = factory.create((EClass) pkg.getEClassifier("RCPackage"));
        setName(rcPackage, removeExtension(new File(output).getName()));

        Matcher stmMatcher = STM_HEADER.matcher(text);
        while (stmMatcher.find()) {
            String name = stmMatcher.group(1);
            int braceIdx = stmMatcher.end() - 1;
            int closeIdx = findMatchingBrace(text, braceIdx);
            if (closeIdx < 0) {
                throw new RuntimeException("Unmatched brace in stm " + name);
            }
            String body = text.substring(braceIdx + 1, closeIdx);

            EObject machine = factory.create((EClass) pkg.getEClassifier("StateMachineDef"));
            setName(machine, name);
            getList(rcPackage, "machines").add(machine);
            parseMachineBody(body, machine, factory, pkg);
        }

        ResourceSet rs = new ResourceSetImpl();
        rs.getResourceFactoryRegistry().getExtensionToFactoryMap()
            .put("*", new XMIResourceFactoryImpl());
        File outFile = new File(output);
        outFile.getAbsoluteFile().getParentFile().mkdirs();
        Resource res = rs.createResource(URI.createFileURI(outFile.getAbsolutePath()));
        res.getContents().add(rcPackage);
        res.save(null);

        int totalNodes = 0, totalTransitions = 0;
        for (EObject machine : getList(rcPackage, "machines")) {
            int nodes = getList(machine, "nodes").size();
            int trans = getList(machine, "transitions").size();
            totalNodes += nodes;
            totalTransitions += trans;
            System.out.println("Machine " + getName(machine)
                + ": " + nodes + " nodes, " + trans + " transitions");
        }
        System.out.println("Wrote " + output
            + " (" + totalNodes + " nodes, " + totalTransitions + " transitions)");
    }

    private static void parseMachineBody(String body, EObject machine,
                                         EFactory factory, EPackage pkg) {
        Map<String, EObject> nodesByName = new HashMap<>();
        List<EObject> nodeList = getList(machine, "nodes");

        Matcher mi = INITIAL.matcher(body);
        while (mi.find()) {
            String name = mi.group(1);
            EObject initial = factory.create((EClass) pkg.getEClassifier("Initial"));
            setName(initial, name);
            nodeList.add(initial);
            nodesByName.put(name, initial);
        }

        Matcher ms = STATE_HEADER.matcher(body);
        while (ms.find()) {
            String name = ms.group(1);
            int closeIdx = findMatchingBrace(body, ms.end() - 1);
            if (closeIdx < 0) continue;
            EObject state = factory.create((EClass) pkg.getEClassifier("State"));
            setName(state, name);
            nodeList.add(state);
            nodesByName.put(name, state);
        }

        List<EObject> transList = getList(machine, "transitions");
        Matcher mt = TRANSITION_HEADER.matcher(body);
        while (mt.find()) {
            String name = mt.group(1);
            int braceIdx = mt.end() - 1;
            int closeIdx = findMatchingBrace(body, braceIdx);
            if (closeIdx < 0) continue;
            String tBody = body.substring(braceIdx + 1, closeIdx);

            Matcher mft = FROM_TO.matcher(tBody);
            if (!mft.find()) {
                System.err.println("Warning: transition " + name + " has no from/to clause");
                continue;
            }
            String fromName = mft.group(1);
            String toName   = mft.group(2);
            EObject src = nodesByName.get(fromName);
            EObject tgt = nodesByName.get(toName);
            if (src == null || tgt == null) {
                System.err.println("Warning: transition " + name
                    + " refers to unknown node(s): from=" + fromName + ", to=" + toName);
                continue;
            }

            EObject trans = factory.create((EClass) pkg.getEClassifier("Transition"));
            setName(trans, name);
            trans.eSet(trans.eClass().getEStructuralFeature("source"), src);
            trans.eSet(trans.eClass().getEStructuralFeature("target"), tgt);
            transList.add(trans);
        }
    }

    private static int findMatchingBrace(String text, int openIdx) {
        int depth = 1;
        for (int i = openIdx + 1; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c == '{') depth++;
            else if (c == '}') { if (--depth == 0) return i; }
        }
        return -1;
    }

    private static void setName(EObject obj, String name) {
        EStructuralFeature f = obj.eClass().getEStructuralFeature("name");
        if (f != null) obj.eSet(f, name);
    }

    private static String getName(EObject obj) {
        EStructuralFeature f = obj.eClass().getEStructuralFeature("name");
        return f == null ? "?" : (String) obj.eGet(f);
    }

    @SuppressWarnings("unchecked")
    private static List<EObject> getList(EObject obj, String featureName) {
        EStructuralFeature f = obj.eClass().getEStructuralFeature(featureName);
        return (List<EObject>) obj.eGet(f);
    }

    private static String removeExtension(String s) {
        int dot = s.lastIndexOf('.');
        return dot < 0 ? s : s.substring(0, dot);
    }

    private static EPackage loadMetamodel(String path) {
        Resource.Factory.Registry.INSTANCE.getExtensionToFactoryMap()
            .put("*", new XMIResourceFactoryImpl());
        ResourceSet rs = new ResourceSetImpl();
        rs.getResourceFactoryRegistry().getExtensionToFactoryMap()
            .put("ecore", new XMIResourceFactoryImpl());
        URI uri = URI.createFileURI(new File(path).getAbsolutePath());
        Resource res = rs.getResource(uri, true);
        for (EObject c : res.getContents()) {
            if (c instanceof EPackage) {
                EPackage pkg = (EPackage) c;
                if (EPackage.Registry.INSTANCE.getEPackage(pkg.getNsURI()) == null) {
                    EPackage.Registry.INSTANCE.put(pkg.getNsURI(), pkg);
                }
                return pkg;
            }
        }
        throw new RuntimeException("No EPackage found in " + path);
    }
}
