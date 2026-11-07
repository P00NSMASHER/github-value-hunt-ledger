// Synthetic transcript source for a network-isolated RPC acceptance test.
import { readFileSync } from "node:fs";
import { fauxAssistantMessage, getApiProvider, registerFauxProvider } from "@earendil-works/pi-ai";

export default function registerReplay(pi) {
    const faux = registerFauxProvider({ provider: "retally-replay", api: "retally-replay" });
    const model = faux.getModel();
    const result = { diff: readFileSync("/fixture/replay.patch", "utf8"), test_command: "python3 verify.py" };
    faux.setResponses([fauxAssistantMessage(JSON.stringify(result))]);
    pi.registerProvider(model.provider, {
        api: model.api, baseUrl: model.baseUrl, apiKey: "synthetic-offline-placeholder",
        models: [model], streamSimple: getApiProvider(model.api).streamSimple,
    });
}
