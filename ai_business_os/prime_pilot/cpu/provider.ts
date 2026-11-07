import {execFileSync} from "node:child_process";
import {createAssistantMessageEventStream} from "@earendil-works/pi-ai";
export default function register(pi) {
    const provider="retally-cpu", api="retally-local-llama-cpp", id="qwen2.5-coder-0.5b";
    pi.registerProvider(provider,{baseUrl:"local-process://llama",api,apiKey:"local-process-only",models:[{id,name:"Qwen CPU",reasoning:false,input:["text"],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},contextWindow:1024,maxTokens:140}],streamSimple(model,context) {
        const stream=createAssistantMessageEventStream();
        const user=context.messages.findLast(m=>m.role==="user");
        const prompt=typeof user.content==="string"?user.content:user.content.find(b=>b.type==="text").text;
        const output=JSON.parse(execFileSync(process.execPath,["/local/infer.mjs",prompt],{timeout:15000,maxBuffer:16384,encoding:"utf8"}));
        const usage={input:output.usage.usedInputTokens,output:output.usage.usedOutputTokens,cacheRead:0,cacheWrite:0,totalTokens:output.usage.usedInputTokens+output.usage.usedOutputTokens,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}};
        const message={role:"assistant",model:id,api,provider,content:[{type:"text",text:output.result}],usage,stopReason:"stop",timestamp:Date.now()};
        stream.push({type:"start",partial:message});
        stream.push({type:"text_start",contentIndex:0,partial:message});
        stream.push({type:"text_delta",contentIndex:0,delta:output.result,partial:message});
        stream.push({type:"text_end",contentIndex:0,content:output.result,partial:message});
        stream.push({type:"done",reason:"stop",message});
        return stream;
    }});
}
