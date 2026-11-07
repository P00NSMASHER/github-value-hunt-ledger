import { getLlama, LlamaChatSession } from "node-llama-cpp";

const prompt = process.argv[2];
if (!prompt || prompt.length > 4096) throw Error("missing or oversized bounded job");
const llama = await getLlama({ gpu:false, build:"never", skipDownload:true, maxThreads:4,
    progressLogs:false, logLevel:"error" });
try {
    const model = await llama.loadModel({modelPath:"/local/model.gguf", gpuLayers:0});
    const context = await model.createContext({contextSize:1024, threads:4, flashAttention:false});
    const sequence = context.getSequence();
    const session = new LlamaChatSession({contextSequence:sequence,
        systemPrompt:"You are a SQLite engineer. Answer the user with SQL only."});
    const result = await session.prompt(prompt, {maxTokens:140, temperature:0, seed:42});
    console.log(JSON.stringify({result, usage:sequence.tokenMeter.getState()}));
} finally { await llama.dispose(); }
