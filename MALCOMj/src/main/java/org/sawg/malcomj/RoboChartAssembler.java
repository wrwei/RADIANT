package org.sawg.malcomj;

import circus.robocalc.robochart.RoboChartPackage;
import circus.robocalc.robochart.textual.RoboChartStandaloneSetup;
import com.google.inject.Injector;
import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.common.util.TreeIterator;
import org.eclipse.emf.ecore.EAttribute;
import org.eclipse.emf.ecore.EClass;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EStructuralFeature;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.resource.ResourceSet;
import org.eclipse.emf.ecore.util.EcoreUtil;
import org.eclipse.xtext.nodemodel.INode;
import org.eclipse.xtext.nodemodel.util.NodeModelUtils;
import org.eclipse.xtext.resource.XtextResourceSet;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.nio.file.Path;

/**
 * Assemble a complete, generator-ready RoboChart .rct from a bare state machine.
 *
 * <p>Parses the bare {@code stm} into a RoboChart EMF model via the official
 * RoboChart Xtext setup, then runs the vendored {@code robochart2rct.egl} (which
 * synthesises the Inputs/Outputs interfaces, Ctrl_State/Constants, controller and a
 * unified module with a robotic platform + connections). Output is compatible with
 * the standalone RoboChart CSP generator.
 *
 * <p>Usage:
 * <pre>--input &lt;bare_stm.rct&gt; --egl &lt;robochart2rct.egl&gt; --output &lt;complete.rct&gt;</pre>
 */
public class RoboChartAssembler {

    public static void main(String[] args) throws Exception {
        Map<String, String> a = parseArgs(args);
        Path input = Path.of(a.get("input"));
        Path egl = Path.of(a.get("egl"));
        Path output = Path.of(a.get("output"));

        // 1. Official RoboChart Xtext setup -> ResourceSet that parses .rct text
        //    into a fully-structured RoboChart EMF model (expression trees and all).
        Injector injector = new RoboChartStandaloneSetup()
                .createInjectorAndDoEMFRegistration();
        ResourceSet rs = injector.getInstance(XtextResourceSet.class);
        Resource model = rs.getResource(
                URI.createFileURI(input.toAbsolutePath().toString()), true);
        if (!model.getErrors().isEmpty()) {
            throw new IllegalStateException(
                    "RoboChart parse errors in " + input + ":\n" + model.getErrors());
        }

        // Normalise the canonical Xtext model into the shape FORGE's EGL expects
        // (bare names as CallExp+StringExp rather than resolved RefExp).
        normaliseExpressions(model);
        // Ensure a Constants interface object exists so the EGL emits
        // `provides Constants` on the robotic platform (it synthesises the
        // Constants *text* from guard-mining, but the platform-provides check
        // keys off pkg.interfaces — which a parsed bare stm lacks).
        ensureInterface(model, "Constants");

        // 2. Run the EGL. The model name MUST be "RoboChart" — the template refers
        //    to RoboChart!RCPackage. Inject the two globals FORGE's pipeline supplies:
        //    - constantDefaults: empty map (template guards on .isDefined(); constants
        //      default to `= 1`);
        //    - traceEntries: a mutable list the template's extractRctTrace appends to.
        //      REMEDIATE has its own traceability, so the collected entries are
        //      discarded — we only need the operation to run. A read-only Epsilon
        //      variable still permits .add() on the underlying list.
        Map<String, Object> vars = new HashMap<>();
        vars.put("constantDefaults", new HashMap<String, Object>());
        vars.put("traceEntries", new ArrayList<Object>());
        String rct = new EglGenerationRunner().run(
                egl, "RoboChart", model, RoboChartPackage.eINSTANCE, output, vars);
        System.out.println("RoboChartAssembler: wrote " + output
                + " (" + rct.length() + " chars)");
    }

    /**
     * Rewrite resolved {@code RefExp} nodes into FORGE's expected encoding so the
     * vendored EGL can mine and render them. FORGE builds its model in Java with
     * bare names as unresolved {@code CallExp} whose {@code function} is a
     * {@code StringExp}; the official Xtext parser instead produces {@code RefExp}
     * cross-references. For each RefExp we take the referenced element's name and:
     *   - if the RefExp is the {@code function} slot of a CallExp (a function call
     *     like {@code odist(x)}) -> replace it with {@code StringExp(name)};
     *   - otherwise (a bare variable/constant reference) -> replace it with
     *     {@code CallExp{function: StringExp(name), args: []}}.
     */
    private static void normaliseExpressions(Resource model) {
        RoboChartPackage rc = RoboChartPackage.eINSTANCE;
        EClass callExpC = (EClass) rc.getEClassifier("CallExp");
        EClass stringExpC = (EClass) rc.getEClassifier("StringExp");
        EStructuralFeature callFunc = callExpC.getEStructuralFeature("function");
        EAttribute stringVal = (EAttribute) stringExpC.getEStructuralFeature("value");

        List<EObject> refExps = new ArrayList<>();
        for (TreeIterator<EObject> it = model.getAllContents(); it.hasNext();) {
            EObject o = it.next();
            if (o.eClass().getName().equals("RefExp")) {
                refExps.add(o);
            }
        }
        for (EObject ref : refExps) {
            String name = refName(ref);
            if (name.isEmpty()) {
                continue;   // no recoverable name — leave it; the EGL backstop reports it
            }
            EObject strExp = EcoreUtil.create(stringExpC);
            strExp.eSet(stringVal, name);

            boolean isFunctionSlot = ref.eContainer() != null
                    && ref.eContainer().eClass().getName().equals("CallExp")
                    && ref.eContainingFeature() == callFunc;
            if (isFunctionSlot) {
                EcoreUtil.replace(ref, strExp);
            } else {
                EObject callExp = EcoreUtil.create(callExpC);
                callExp.eSet(callFunc, strExp);
                EcoreUtil.replace(ref, callExp);
            }
        }
    }

    /** Add an empty named {@code Interface} to the RCPackage if absent. */
    @SuppressWarnings("unchecked")
    private static void ensureInterface(Resource model, String name) {
        if (model.getContents().isEmpty()) {
            return;
        }
        EObject pkg = model.getContents().get(0);   // RCPackage
        EStructuralFeature ifaceFeat = pkg.eClass().getEStructuralFeature("interfaces");
        if (ifaceFeat == null) {
            return;
        }
        List<EObject> ifaces = (List<EObject>) pkg.eGet(ifaceFeat);
        for (EObject i : ifaces) {
            if (name.equals(simpleName(i))) {
                return;
            }
        }
        EClass ifaceC = (EClass) RoboChartPackage.eINSTANCE.getEClassifier("Interface");
        EObject ci = EcoreUtil.create(ifaceC);
        ci.eSet(ifaceC.getEStructuralFeature("name"), name);
        ifaces.add(ci);
    }

    /** Name a RefExp refers to: the resolved target's name, or — when the cross
     *  reference is unresolved (an undeclared guard variable such as a
     *  function-rewritten `odist_cdyn`) — the concrete-syntax text from the node
     *  model, so it still becomes a bare CallExp instead of rendering UNKNOWN. */
    private static String refName(EObject ref) {
        EStructuralFeature refFeat = ref.eClass().getEStructuralFeature("ref");
        if (refFeat != null) {
            Object target = ref.eGet(refFeat, false);          // do not resolve the proxy
            if (target instanceof EObject && !((EObject) target).eIsProxy()) {
                String n = simpleName(target);
                if (!n.isEmpty()) {
                    return n;
                }
            }
            for (INode node : NodeModelUtils.findNodesForFeature(ref, refFeat)) {
                String text = NodeModelUtils.getTokenText(node).trim();
                if (!text.isEmpty()) {
                    return text;
                }
            }
        }
        return "";
    }

    private static String simpleName(Object o) {
        if (!(o instanceof EObject)) {
            return "";
        }
        EObject e = (EObject) o;
        EStructuralFeature nf = e.eClass().getEStructuralFeature("name");
        Object v = nf == null ? null : e.eGet(nf);
        return v == null ? "" : v.toString();
    }

    private static Map<String, String> parseArgs(String[] args) {
        Map<String, String> m = new HashMap<>();
        for (int i = 0; i + 1 < args.length; i += 2) {
            m.put(args[i].replaceFirst("^--", ""), args[i + 1]);
        }
        return m;
    }
}
