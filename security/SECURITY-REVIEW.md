# MeetMind security assessment

Assessment date: 10 November 2026. Scope: this local checkout, including `app.py`, the media pipeline, Chroma storage, RAG prompts, and dev-container configuration.

**Result: fix the input boundary and shared storage before exposing this app to multiple untrusted users.** Five bounded local probes reproduced security-relevant behavior. Other findings below are based on source review and are labeled accordingly.

## Strix status and assessment limits

The requested Strix plugin was contacted to locate a MeetMind repository/domain. Its asset-list tools repeatedly returned `Authentication for Strix was requested and accepted. Retry this tool call now.` Retrying did not return assets. **No Strix scan was launched, no scan ID was issued, and these findings are not a Strix report.** Reconnect Strix to continue its remote assessment.

No deployed application URL was provided or tested. This was a local code and component assessment, not a completed browser/network pentest. The probes used synthetic recordings, a loopback-only HTTP fixture, temporary Chroma storage, deterministic test embeddings, and a fake model response. They did not access the existing meeting database or recordings, call NVIDIA/Sarvam, stress the app, or test external infrastructure. The yt-dlp probe adds short timeouts, disables retries and environmental proxies, and otherwise exercises the existing URL handling. Dependency CVEs, deployment TLS/proxy controls, and git-history secrets were not assessed.

## Priorities

| ID | Severity | Gap | Evidence |
| --- | --- | --- | --- |
| MM-01 | High | User URL triggers requests to internal services (SSRF) | Reproduced with real HTTP to loopback |
| MM-02 | High | URL input accepts server-side audio file paths | Reproduced with synthetic local WAV |
| MM-03 | High | One analysis deletes another meeting's vector collection | Reproduced with actual Chroma |
| MM-04 | High if publicly reachable | No application login, processing quotas, or job admission limits | Source review; external access controls unknown |
| MM-05 | Medium | Upload filenames collide and overwrite other users' audio | Executed the app's upload-write statements |
| MM-06 | Medium | Dev-container disables CORS and XSRF protection | Explicit launch flags; deployment-dependent exposure |
| MM-07 | Medium | Untrusted transcript instructions enter the system prompt | Captured the constructed prompt; model exploit untested |
| MM-08 | Medium | Meeting data persists in files, embeddings, and logs without a clear deletion lifecycle | Source review |

### MM-01: server-side request forgery

Source: [`utils/audio_processor.py:64`](../utils/audio_processor.py#L64), [`utils/audio_processor.py:33`](../utils/audio_processor.py#L33), [`app.py:281`](../app.py#L281).

The UI calls the field “YouTube URL,” but `process_input` accepts any string beginning with HTTP(S), and sends it to yt-dlp without a YouTube hostname or destination-network restriction. yt-dlp's generic extractor can fetch other sites.

The probe passed `http://127.0.0.1:<fixture-port>/audit-fixture` into the real media input function. The fixture received an HTTP GET. Extraction subsequently failed because the fixture contained no media; that failure does not undo the request.

Impact: a user can cause the application server to contact reachable internal HTTP services. Arbitrary methods, cloud metadata retrieval, response exfiltration, and access beyond loopback were not demonstrated.

Fix: make the web input accept a supported YouTube video identifier or strictly parsed supported YouTube URL, then construct the canonical video URL server-side. Restrict downloader egress to public destinations, including after DNS resolution and redirects; block loopback, private, link-local, and IPv6 equivalents. Do not rely on a client-side label or string-prefix check. Put the downloader in a worker with restricted network access.

Acceptance: the web input rejects non-YouTube URLs and a local HTTP fixture receives zero requests, including when reached through a redirect or an alternate IP representation.

### MM-02: server-side audio file access through the URL widget

Source: [`app.py:212`](../app.py#L212), [`app.py:281`](../app.py#L281), [`utils/audio_processor.py:64`](../utils/audio_processor.py#L64).

The same source string is used for trusted CLI paths, web URL input, and uploaded files. Any web input without an HTTP(S) prefix falls into the local-file conversion branch. There is no check tying that path to the user's upload.

The probe created a synthetic WAV outside the upload flow and successfully converted/chunked it through `process_input`. In the UI, successful pipeline processing would return its transcript and analysis to the submitting session.

Impact: a user who knows or guesses a readable server audio/video path can submit it for transcription, potentially exposing someone else's recording. This finding does **not** establish arbitrary text-file or `.env` disclosure: the input still has to pass media decoding.

Fix: separate web URL and uploaded-media entry points. Resolve uploads using server-issued opaque IDs tied to the owning session/user. Do not accept filesystem paths from web text fields. Keep trusted local-path support confined to the CLI.

Acceptance: entering the path of a synthetic server-only WAV into the web URL flow is rejected before file access, while an upload owned by the caller still works.

### MM-03: shared vector collection deletion

Source: [`core/vector_store.py:9`](../core/vector_store.py#L9), [`core/vector_store.py:47`](../core/vector_store.py#L47).

Every analysis uses `vector_db` and `meeting_transcript`. `build_vector_store` deletes that collection before creating the next one. Streamlit session state isolates the Python results dictionary, but it does not isolate this shared storage.

Using the real Chroma implementation with deterministic synthetic embeddings, the probe built Alice's meeting, then Bob's. Bob's build removed Alice's documents; querying Alice's existing handle then raised `NotFoundError`. Reopening the shared namespace returned Bob's meeting.

Impact: one user can destroy another active analysis's retrieval data and break their chat. A cross-user answer/data leak was not demonstrated with the installed Chroma version; the observed failure was deletion and loss of availability.

Fix: give each analysis an independent store or collection with a random meeting ID. Tie it to its owner and enforce that ownership whenever loading/querying/deleting it. If persistence is unnecessary, prefer a per-analysis in-memory store. Delete only the caller's collection when clearing their analysis.

Acceptance: two sessions can ingest and query distinct synthetic meetings concurrently; each sees only its own marker, and clearing/rebuilding either one leaves the other usable.

### MM-04: unbounded processing and API spending

Source: [`app.py:273`](../app.py#L273), [`utils/audio_processor.py:42`](../utils/audio_processor.py#L42), [`utils/audio_processor.py:49`](../utils/audio_processor.py#L49), [`main.py:11`](../main.py#L11).

There is no application authentication/authorization gate before Analyze or chat. There are no application per-user quotas, maximum recording-duration checks, download-byte limits, global concurrency limits, or bounded job execution. `is_processing` records session state but is not used as an admission guard. Audio is decoded into memory before chunking, and long transcripts cause additional summarization work and paid requests.

Streamlit may impose a default upload-byte limit; that does not bound remote downloads, decoded media size, recording duration, total concurrent users, or API spending. An authenticated reverse proxy could reduce anonymous exposure, but no such deployment was verified.

Impact if internet-accessible: anonymous users can consume CPU/GPU, memory, disk, and shared provider quota; new sessions bypass a purely session-local limit. No resource-exhaustion attack was executed.

Fix: require access control for a hosted service. Add account quotas and rate limits for Analyze and chat, a bounded worker queue, global concurrency and wall-clock limits, remote download limits, and media duration/decoded-size limits before expensive work. Run media parsers in an isolated worker with restricted filesystem/network access. Bound chat length and answer generation as well.

Acceptance: rejected/over-quota jobs never reach transcription or a paid API; oversized and overly long media are rejected early; concurrent work remains within configured capacity.

### MM-05: upload collision across sessions

Source: [`app.py:231`](../app.py#L231).

Uploads are written to the common temporary directory as `meetmind_{int(time.time())}{suffix}` using `open(..., "wb")`. Two uploads with the same extension in the same second use the same file, regardless of original filename or session. Writing also occurs on reruns while the uploaded file remains selected.

The probe executed the actual suffix/path/write statements extracted from `app.py`, supplied two synthetic users at the same timestamp, and confirmed that Bob's bytes replaced Alice's bytes. It did not simulate two complete browser sessions.

Impact: concurrent users can overwrite a pending recording, causing processing failures or the wrong recording to be analyzed. The specific first-session transcript disclosure outcome was not exercised.

Fix: use securely and atomically created temporary files, each inside a private per-job directory, with explicit ownership and cleanup. Retain the allocated path for that upload rather than rewriting it on unrelated widget reruns. Keep media extensions server-controlled.

Acceptance: two uploads with identical extensions and timestamps always have different paths and preserve their own bytes.

### MM-06: browser protections explicitly disabled

Source: [`.devcontainer/devcontainer.json:22`](../.devcontainer/devcontainer.json#L22).

The dev-container starts Streamlit with `--server.enableCORS false --server.enableXsrfProtection false`, and forwards port 8501. This deliberately removes protections against cross-origin access and forged requests in that launch mode. Whether another website can reach a user's instance depends on port exposure, browser behavior, and any gateway authentication; no browser exploit was run.

Fix: remove those disabling flags and use the secure defaults. Configure legitimate origins and proxy settings explicitly if required. Keep development forwarding private and verify production configuration separately.

Acceptance: the actual deployment has CORS/origin and XSRF protection enabled, and untrusted-origin requests are refused without breaking normal app use.

### MM-07: transcript content elevated into system instructions

Source: [`core/RAG.py:27`](../core/RAG.py#L27), [`core/RAG.py:39`](../core/RAG.py#L39); similar prompt boundaries warrant review in `core/summarize.py` and `core/extractor.py`.

Retrieved transcript text is inserted directly into a system-role message. A malicious participant or recording can include instructions that compete with the assistant's actual rules. The probe supplied a harmless instruction marker through the retriever and captured it unchanged in the system message sent toward the model.

Impact: prompt injection can undermine the integrity of meeting answers, decisions, and action items. The test confirms unsafe prompt construction, **not** that the live NVIDIA model followed the instruction. This app's RAG chain has no execution tools, and this finding does not establish access to environment variables or arbitrary code execution.

Fix: reserve system messages for trusted instructions. Put transcript evidence in a separate explicitly labeled untrusted-data message, instruct the model to describe rather than obey transcript instructions, and add citations/evidence validation for extracted decisions and tasks. Test adversarial transcripts using a separate bounded evaluation. Prompt wording is not an authorization boundary; enforce any future tool permissions outside the model.

Acceptance: adversarial transcript fixtures do not change the task, fabricate approved actions, or suppress relevant evidence, and outputs identify the transcript evidence they rely on.

### MM-08: sensitive data retention and logging

Source: [`main.py:17`](../main.py#L17), [`core/RAG.py:94`](../core/RAG.py#L94), [`core/transcriber.py:166`](../core/transcriber.py#L166), [`app.py:437`](../app.py#L437), [`.gitignore`](../.gitignore).

The pipeline logs transcript excerpts; RAG logs entire questions and answers; the Sarvam handler logs response bodies. Uploaded source files, converted WAVs, chunks, and persisted embeddings have no complete job cleanup lifecycle. Sarvam's small intermediate pieces are cleaned up, but that does not remove the rest. “Clear this analysis” only clears session state.

`.gitignore` ignores `downloads/` while the actual downloader uses `downloades/`; `vector_db/` and `debug.log` are also unignored and appeared as untracked paths during this assessment. That makes accidental inclusion of private meeting artifacts easier. Existing artifact contents were not inspected.

Impact: meeting content outlives the visible analysis in application logs and disk artifacts, and can be accidentally shared in source control. This is exposure to log/storage/repository readers, not proof that an unauthenticated web user can download those files.

Fix: use structured metadata-only logs, redact sensitive upstream errors, document retention, and clean job artifacts on success, failure, expiry, and explicit deletion. Ensure Clear/Delete performs the intended storage deletion for that meeting. Ignore actual generated directories and log files. Audit committed history separately before concluding that previous disclosures did not happen.

Acceptance: synthetic content does not appear in routine logs; deleting an analysis removes its authorized persistent artifacts; generated output paths are ignored by Git.

## Positive observations and additional reliability issue

- The title, transcript, and highlight input are HTML-escaped before insertion into custom HTML, reducing a direct HTML-injection path at those locations. This is not a full XSS audit.
- `.env` and `.streamlit/secrets.toml` are ignored. A limited current-tracked-text scan for literal key assignments and private-key headers found no matches. This does not cover every secret format, ignored files, or repository history.
- Sarvam requests have a 120-second HTTP timeout and per-piece cleanup in `finally`.
- Separate reliability bug: `load_rag_chain()` calls `get_retriever()` without the required `vector_store` argument at `core/RAG.py:60`. It would raise `TypeError` if called. The current UI builds a new chain, so this is not an authentication bypass.
- Most dependency versions are open-ended minimums and there is no tracked lockfile. Pin a tested environment and add dependency advisory scanning; no specific dependency vulnerability is asserted here.

## Reproduction and recommended order

From the repository root on Windows:

```powershell
.venv/Scripts/python.exe security/reproduce_findings.py
```

The harness writes [`probe-results.json`](probe-results.json). All five probes reproduced the current behavior on the installed environment. Its success exit code means the vulnerabilities were reproduced, not that the app is secure. The prompt probe uses a fake model and the vector probe uses real Chroma with fake embeddings. Synthetic scratch files are confined to `security/.fixtures/`, which is ignored; Windows can retain locked SQLite fixtures until the process exits.

Recommended implementation order:

1. Separate web inputs from trusted filesystem paths, restrict URLs and downloader network access, and isolate media jobs.
2. Give each analysis its own authorized vector storage and unique upload workspace.
3. Enable browser protections; add hosted-service access control, quotas, and bounded workers.
4. Implement deletion/retention and log redaction; improve the RAG trust boundary and evaluate adversarial transcripts.
5. Reconnect Strix, identify the repository/branch or verified deployment, and run a bounded assessment against that precise target. A source review can use the repository; a live test needs a reachable URL, with a staging target preferred where available. Strix scan tiers consume credits.

Application source was not modified by this assessment.
