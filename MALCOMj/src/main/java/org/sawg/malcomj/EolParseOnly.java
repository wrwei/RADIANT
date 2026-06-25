package org.sawg.malcomj;

import org.eclipse.epsilon.eol.EolModule;

import java.io.File;
import java.util.List;

/**
 * Parse-only validator for EOL source files. Emits a single JSON line on
 * stdout describing whether parsing succeeded, plus any parse messages.
 *
 * Used by the D5 evaluation metrics package
 * (malcom.evaluation/metrics/eol_syntax_check.py).
 *
 * Usage:
 *   java -cp ... org.sawg.malcomj.EolParseOnly INPUT.eol
 */
public final class EolParseOnly {

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: EolParseOnly INPUT.eol");
            System.exit(2);
        }
        File f = new File(args[0]);
        if (!f.exists()) {
            System.out.println("{\"syntax_ok\":false,\"errors\":[\"file not found: "
                    + args[0].replace("\\", "\\\\") + "\"]}");
            return;
        }
        EolModule mod = new EolModule();
        try {
            mod.parse(f);
        } catch (Exception ex) {
            System.out.println("{\"syntax_ok\":false,\"errors\":["
                    + jsonString(ex.getClass().getSimpleName() + ": " + ex.getMessage()) + "]}");
            return;
        }
        var problems = mod.getParseProblems();
        boolean ok = problems == null || problems.isEmpty();
        StringBuilder sb = new StringBuilder("{\"syntax_ok\":").append(ok).append(",\"errors\":[");
        if (problems != null) {
            for (int i = 0; i < problems.size(); i++) {
                if (i > 0) sb.append(',');
                sb.append(jsonString(String.valueOf(problems.get(i))));
            }
        }
        sb.append("]}");
        System.out.println(sb);
    }

    private static String jsonString(String s) {
        if (s == null) return "null";
        StringBuilder sb = new StringBuilder().append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"':  sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n");  break;
                case '\r': sb.append("\\r");  break;
                case '\t': sb.append("\\t");  break;
                default:
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        return sb.append('"').toString();
    }
}
