# About this project

## Who / what
AES Help Assistant — a USPS Address Enterprise Service operator's chat
assistant. Lives inside the Address Enterprise Service Portal to answer
questions about loaded address records, validation issues, required fields,
submissions, plat maps, and USPS publication 28 rules.

## Primary user
A USPS address-data operator uploading and validating address records for a
geography (e.g. MATTHEWS, NC — ~21k records). Needs fast, voice-capable
answers while reviewing records on a second screen.

## Surface
- React + Tailwind chat widget (see `frontend/src/components/ChatView.tsx`).
- Blue USPS header with ONLINE status, records/issues stat bar, quick actions,
  rounded input, in-header TTS mute toggle.
- Browser `SpeechSynthesis` API drives text-to-speech — no server-side TTS.

## What breaks if Claude doesn't know this
- It'll rename the assistant to "AMIE" (old name). The current product name
  is **AES Help Assistant**.
- It'll propose server-side TTS vendors (ElevenLabs, Polly). TTS is
  client-side only — see `frontend/src/hooks/useTTS.ts`.
- It'll drift from USPS brand colors — use `usps-blue / usps-red / usps-gold`
  tokens in `frontend/tailwind.config.js`.
- It'll re-introduce unused `useState` / dead imports. The repo runs strict
  TS; unused symbols fail the build.
