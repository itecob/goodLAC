#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import net from "node:net";
import { createAssistantMessageEventStream, Type } from "/pi/packages/ai/dist/index.js";
import { createGovernedLacTools, GOVERNED_TOOL_NAMES } from "./governed_pi.mjs";

const BROKER_SOCKET = String(process.env.LAC_PI005_BROKER_SOCKET || "");
if (BROKER_SOCKET !== "/lac/broker.sock") throw new Error("LAC broker socket path is unavailable");
const socket = net.createConnection({ path: BROKER_SOCKET });
const connected = new Promise((resolve, reject) => {
  socket.once("connect", resolve);
  socket.once("error", reject);
});
socket.setEncoding("utf8");
let buffer = "";
const queue = [];
const waiters = [];
let rpcCounter = 0;

function emit(value) { socket.write(`${JSON.stringify(value)}\n`); }
function deliver(value) {
  const waiter = waiters.shift();
  if (waiter) waiter.resolve(value); else queue.push(value);
}
function failWaiters(error) {
  while (waiters.length) waiters.shift().reject(error);
}
socket.on("data", (chunk) => {
  buffer += chunk;
  for (;;) {
    const i = buffer.indexOf("\n");
    if (i < 0) break;
    const line = buffer.slice(0, i); buffer = buffer.slice(i + 1);
    if (!line) continue;
    try { deliver(JSON.parse(line)); } catch (error) { failWaiters(error); }
  }
});
socket.on("error", failWaiters);
socket.on("close", () => failWaiters(new Error("LAC broker closed")));
function nextMessage() {
  if (queue.length) return Promise.resolve(queue.shift());
  return new Promise((resolve, reject) => waiters.push({ resolve, reject }));
}
async function rpc(kind, payload) {
  const id = `rpc-${++rpcCounter}`;
  emit({ type: "rpc", id, kind, payload });
  const response = await nextMessage();
  if (!response || response.type !== "rpc_response" || response.id !== id || typeof response.ok !== "boolean") {
    throw new Error("LAC broker response did not bind active request");
  }
  if (!response.ok) throw new Error(String(response.error || `${kind} failed`));
  return response.payload;
}

function cloneUsage() {
  return { input:0, output:0, cacheRead:0, cacheWrite:0, totalTokens:0,
    cost:{ input:0, output:0, cacheRead:0, cacheWrite:0, total:0 } };
}
function mapUsage(raw) {
  if (!raw || typeof raw !== "object") return cloneUsage();
  const input=Number(raw.input_tokens ?? 0), output=Number(raw.output_tokens ?? 0), cached=Number(raw.cached_input_tokens ?? 0);
  return { input:Math.max(0,input-cached), output:Math.max(0,output), cacheRead:Math.max(0,cached), cacheWrite:0,
    totalTokens:Math.max(0,Number(raw.total_tokens ?? input+output)), cost:{ input:0, output:0, cacheRead:0, cacheWrite:0, total:0 } };
}
function jsonArguments(raw) {
  if (raw === "" || raw == null) return {};
  if (typeof raw === "object") return raw;
  const parsed=JSON.parse(raw);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("tool arguments must be object");
  return parsed;
}
function makeRpcStreamFn(timeoutSeconds, mode) {
  return (model, context, options={}) => {
    const stream=createAssistantMessageEventStream();
    const partial={ role:"assistant", content:[], api:model.api, provider:model.provider, model:model.id,
      usage:cloneUsage(), stopReason:"pending", timestamp:Date.now() };
    queueMicrotask(async () => {
      let started=false, textIndex=null, thinkingIndex=null, finishReason=null;
      const toolStates=new Map();
      const start=()=>{ if(!started){ started=true; stream.push({type:"start",partial}); } };
      const endText=()=>{ if(textIndex!==null){ const b=partial.content[textIndex]; stream.push({type:"text_end",contentIndex:textIndex,content:b.text,partial}); textIndex=null; } };
      const endThinking=()=>{ if(thinkingIndex!==null){ const b=partial.content[thinkingIndex]; stream.push({type:"thinking_end",contentIndex:thinkingIndex,content:b.thinking,partial}); thinkingIndex=null; } };
      try {
        start();
        const events=await rpc("model_request", { model:model.id, context, options:{ maxTokens:options.maxTokens ?? 2048,
          temperature:options.temperature ?? 0, toolChoice:options.toolChoice ?? "auto", reasoning:options.reasoning, timeoutSeconds } });
        if (!Array.isArray(events)) throw new Error("model broker response must be event array");
        for (const event of events) {
          if (!event || typeof event !== "object") throw new Error("malformed model broker event");
          if (event.kind === "error") throw new Error(event.message || "model broker failed closed");
          if (event.kind === "text_delta") {
            endThinking();
            if (textIndex===null){ textIndex=partial.content.length; partial.content.push({type:"text",text:""}); stream.push({type:"text_start",contentIndex:textIndex,partial}); }
            const delta=String(event.value ?? ""); partial.content[textIndex].text+=delta; stream.push({type:"text_delta",contentIndex:textIndex,delta,partial}); continue;
          }
          if (event.kind === "reasoning_delta") {
            endText();
            if (thinkingIndex===null){ thinkingIndex=partial.content.length; partial.content.push({type:"thinking",thinking:""}); stream.push({type:"thinking_start",contentIndex:thinkingIndex,partial}); }
            const delta=String(event.value ?? ""); partial.content[thinkingIndex].thinking+=delta; stream.push({type:"thinking_delta",contentIndex:thinkingIndex,delta,partial}); continue;
          }
          if (event.kind === "tool_call_delta") {
            endText(); endThinking();
            if (!Array.isArray(event.value)) throw new Error("tool_call_delta must be array");
            for (const delta of event.value) {
              const idx=Number.isInteger(delta.index)?delta.index:0; let state=toolStates.get(idx);
              if(!state){ const contentIndex=partial.content.length; state={contentIndex,id:"",name:"",argumentsText:""}; toolStates.set(idx,state);
                partial.content.push({type:"toolCall",id:"pending",name:"pending",arguments:{}}); stream.push({type:"toolcall_start",contentIndex,partial}); }
              if(typeof delta.id === "string") state.id+=delta.id;
              const fn=delta.function;
              if(fn && typeof fn === "object") { if(typeof fn.name === "string") state.name+=fn.name;
                if(typeof fn.arguments === "string"){ state.argumentsText+=fn.arguments; stream.push({type:"toolcall_delta",contentIndex:state.contentIndex,delta:fn.arguments,partial}); }
                else if(fn.arguments && typeof fn.arguments === "object"){ const enc=JSON.stringify(fn.arguments); state.argumentsText+=enc; stream.push({type:"toolcall_delta",contentIndex:state.contentIndex,delta:enc,partial}); }
              }
            }
            continue;
          }
          if(event.kind === "usage"){ partial.usage=mapUsage(event.value); continue; }
          if(event.kind === "finish"){ finishReason=String(event.value ?? "stop"); continue; }
          if(event.kind === "done") continue;
          throw new Error(`unknown model broker event: ${String(event.kind)}`);
        }
        endText(); endThinking();
        for(const [,state] of [...toolStates.entries()].sort((a,b)=>a[0]-b[0])){
          const toolCall={type:"toolCall",id:state.id || `lac-tool-${state.contentIndex}`,name:state.name,arguments:jsonArguments(state.argumentsText)};
          if(!toolCall.name) throw new Error("tool call ended without name");
          partial.content[state.contentIndex]=toolCall; stream.push({type:"toolcall_end",contentIndex:state.contentIndex,toolCall,partial});
        }
        const reason=(finishReason === "length")?"length":(toolStates.size?"toolUse":"stop");
        const message={...partial,stopReason:reason,timestamp:Date.now()};
        stream.push({type:"done",reason,message}); stream.end(message);
        if (mode === "probe" && reason !== "toolUse") socket.unref();
      } catch(error) {
        const message={ role:"assistant", content:partial.content, api:model.api, provider:model.provider, model:model.id,
          usage:cloneUsage(), stopReason:"error", errorMessage:error instanceof Error?error.message:String(error), timestamp:Date.now() };
        stream.push({type:"error",reason:"error",error:message}); stream.end(message);
      }
    });
    return stream;
  };
}

async function connectProbe(host, port) {
  return await new Promise((resolve) => {
    const s=net.createConnection({host,port:Number(port)}); let done=false;
    const finish=(connected)=>{ if(done)return; done=true; s.destroy(); resolve(connected); };
    s.setTimeout(400,()=>finish(false)); s.once("connect",()=>finish(true)); s.once("error",()=>finish(false));
  });
}
async function ambientProbes(bootstrap) {
  let hostFileReadable=false, hostWorkspaceReadable=false, hostWorkspaceWrite=false;
  try { readFileSync(String(bootstrap.hostFilePath),"utf8"); hostFileReadable=true; } catch {}
  try { readFileSync(String(bootstrap.workspaceProbeReadPath),"utf8"); hostWorkspaceReadable=true; } catch {}
  try { writeFileSync(String(bootstrap.workspaceProbeWritePath),"escaped\n","utf8"); hostWorkspaceWrite=true; } catch {}
  const inheritedCredential=Object.hasOwn(process.env,String(bootstrap.syntheticCredentialName));
  const launched=spawnSync("/usr/bin/touch",[String(bootstrap.processMarkerPath)],{encoding:"utf8"});
  return { host_file_readable:hostFileReadable, host_workspace_readable:hostWorkspaceReadable,
    host_workspace_write_effect:hostWorkspaceWrite, synthetic_service_credential_inherited:inheritedCredential,
    arbitrary_host_executable_launched:!launched.error, loopback_connected:await connectProbe("127.0.0.1",bootstrap.loopbackPort),
    private_network_connected:await connectProbe("10.255.255.1",9), admin_socket_visible:existsSync(String(bootstrap.adminSocketPath)),
    pid:process.pid, cwd:process.cwd() };
}

export default async function lacGovernedPiExtension(pi) {
  await connected;
  const bootstrap=await nextMessage();
  if(!bootstrap || bootstrap.type!=="bootstrap" || !["interactive","probe"].includes(bootstrap.mode)) throw new Error("invalid PI005 bootstrap");
  const executeLac=async ({toolCallId,toolName,arguments:toolArguments})=>{
    const response=await rpc("effect_request",{toolCallId,toolName,arguments:toolArguments});
    if(!response || response.ok!==true) throw new Error(`LAC effect failed closed (${String(response?.error_type || "unknown")})`);
    return response.result;
  };
  for(const tool of createGovernedLacTools({Type,executeLac})) pi.registerTool(tool);
  pi.registerProvider("lac-freetoken",{
    name:"LAC FreeToken broker",
    baseUrl:"http://127.0.0.1:1",
    apiKey:"LAC_PI005_LOCAL_BROKER_NONSECRET",
    api:"openai-completions",
    models:[{ id:String(bootstrap.modelId), name:"LAC governed gpt-oss-20b", reasoning:true, input:["text"],
      cost:{input:0,output:0,cacheRead:0,cacheWrite:0}, contextWindow:131072, maxTokens:2048 }],
    streamSimple:makeRpcStreamFn(Number(bootstrap.timeoutSeconds || 300), String(bootstrap.mode)),
  });
  const argv=process.argv.slice(2);
  const required=["--no-builtin-tools","--no-extensions","--no-skills","--no-prompt-templates","--no-themes","--no-context-files","--no-session"];
  for(const flag of required) if(!argv.includes(flag)) throw new Error(`missing governed Pi lockdown flag: ${flag}`);
  const extIndex=argv.indexOf("-e");
  if(extIndex<0 || argv[extIndex+1]!=="/lac/pi_native_tui.mjs") throw new Error("trusted PI005 extension is not the explicit extension path");
  const probes=await ambientProbes(bootstrap);
  emit({ type:"ready", tool_surface:[...GOVERNED_TOOL_NAMES], frontend:"PiSourceCLI", entrypoint:"/pi/packages/coding-agent/src/cli.ts",
    resources:{extension_discovery:false,skills:false,prompt_templates:false,themes:false,context_files:false,session_persistence:false}, probes });
  const ack=await nextMessage();
  if(!ack || ack.type!=="ready_ack" || ack.ok!==true) throw new Error("PI005 ready acknowledgement missing");
}
