# Prime CPU engineering acceptance

The real Prime RPC worker generates a patch for the duplicate-inquiry SQL fixture with Qwen2.5-Coder-0.5B-Instruct on a local CPU. The first attempt used `ON CONFLICT` against a column without a unique constraint. The clean-clone verifier rejected it. A second job supplied a hint about SQLite set subtraction. The model generated the candidate SQL without an answer file. The broker strips an optional Markdown code fence and computes a unified diff against the fixture. It never changes the generated SQL.

The verified change produced one row for A after a lost acknowledgment and retry, and one row for B. The base produced two rows for A. The clean verifier produced tree `daf021a5b6987b53e5eb3f9358606f6f7f0eca7c`. See the two prompts, verbatim replies, token counts, elapsed time and verdicts in [first attempt](receipts/attempt-1.json) and [second attempt](receipts/attempt-2.json), alongside the [generated diff](receipts/attempt-2.patch). The lease kill/restart acceptance uses the separate deterministic replay.

## Reproduce

Start from the repository root, with Linux x86-64, the namespace tools listed in the [parent instructions](../README.md), Node 24 and the prepared upstream checkout in `$prime`. Use a fresh output directory. This downloads about 491 MB of weights.

```bash
weights=/tmp/retally-qwen-0.5b-q4_k_m.gguf
curl -fL --output "$weights" 'https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF/resolve/ebb2015119c907b064c512bf053e945850b5875f/qwen2.5-coder-0.5b-instruct-q4_k_m.gguf'
(cd ai_business_os/prime_pilot/cpu && npm ci --ignore-scripts --omit=optional --no-audit)
python3 ai_business_os/prime_pilot/cpu/run.py "$prime" "$weights" /tmp/retally-cpu-job-results
```

The worker verifies the full weight SHA-256 before mounting it read-only. The pinned node-llama-cpp 3.22.3 Linux CPU binary runs llama.cpp v0.9.0 on four threads with a 1,024-token context, 140-token response limit and temperature zero. The lockfile records npm package integrity. In this build, `llama-addon.node` had SHA-256 `75ff4df82472407736a1fc088c7e93eddf93a13d5d6413c0b69b48f812d2c678`, and the GGUF had SHA-256 `1d9614638d18024d0fbb36575a15f1302a3adf044df10345688ec4f6e1c4ff32`. Qwen lists these weights under Apache-2.0. The model and runtime are fetched during setup. The job receives a local fixture in a netless sandbox, with no provider credentials or replay answer mounted. Each model call has a 15-second inference subprocess timeout and a 25-second RPC wall limit.

[Model card at the tested revision](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF/blob/ebb2015119c907b064c512bf053e945850b5875f/README.md) · [Engine release](https://www.npmjs.com/package/node-llama-cpp/v/3.22.3)
