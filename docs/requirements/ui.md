# Frontend UI Requirements (Phase 3)

## Purpose

Browser-based UI that lets a user upload a football clip, wait for
processing, then interactively view detections, click a player to
highlight that player's track, and play the video with the highlight
following the player.

## Owner

Xiwen

## Stack

- **Vite + React 18 + TypeScript** (SPA, no SSR)
- **Tailwind CSS + shadcn/ui** for design system
- **TanStack Query** for server state (job polling, frame fetches)
- **Zustand** for client UI state (selected track, overlay visibility,
  scrub position)
- Video: native HTML `<video>` + Canvas/SVG overlay synchronized via
  `requestVideoFrameCallback` (frame-accurate; falls back to
  `currentTime`-based polling on browsers without rVFC)
- Build output: static assets served independently from the API; for
  dev, Vite proxies `/api/*` to the FastAPI backend.

## Repo location

`web/` at repo root. Independent `package.json`. Lockfile committed
(`pnpm-lock.yaml` or `package-lock.json`). The Python project has no
build dependency on the frontend.

## Top-level state machine

```
idle
  ↓ user picks a file
uploading
  ↓ POST /jobs returns job_id
processing  ←─ poll GET /jobs/{id} every 1s
  ↓ status === "ready"
ready
  ↕ user actions never leave this state in v1
   - scrub: seeks <video>, fetches detections for the new frame, draws overlay
   - select track: highlights chosen track, fades others
   - play: video plays; overlay updates per frame; selected track stays highlighted
   - toggle "show others": hides non-selected boxes
```

Any failure (upload error, processing error, network drop) takes the
app to a `failed` state with a retry button.

## Key views

1. **Upload screen** — drop zone + file picker. Shows allowed formats
   (mp4 / mov / mkv) and max size (configurable, default 1 GB).
2. **Processing screen** — progress bar bound to `GET /jobs/{id}`,
   estimated remaining time once decoding is done, current stage label.
3. **Player screen** — main work surface:
   - Video centered, native controls hidden (custom controls below)
   - Custom timeline: scrubbable, shows track density heatmap (later)
   - Frame counter and timestamp readout
   - Overlay: bbox per detection. Selected track gets a thicker border
     and a brand-color highlight; other tracks render with a low-opacity
     stroke when "show others" is on, hidden when off.
   - Side panel:
     - List of tracks (from `GET /jobs/{id}/tracks`) with thumbnail and
       frame range; clicking selects that track.
     - Toggles: "show other detections", "show track trail", "show track id".

## Interaction details

- **Scrub** debounced (50 ms) before fetching that frame's detections;
  cache in TanStack Query keyed by `(job_id, frame_id)`.
- **Click on a bbox** → set `selected_track_id` in Zustand → app fetches
  `GET /jobs/{id}/tracks/{track_id}` once and caches.
- **Play** → use `requestVideoFrameCallback` to redraw the overlay each
  frame. The detections for the current frame are looked up from
  TanStack Query cache; on a cache miss, draw the previous frame's
  overlay until data arrives (no flicker).
- **Selected track persists across pause/play and scrub.** Only
  cleared by clicking the cleared "deselect" button or selecting
  another track.

## Visual style (deferred)

`shadcn/ui` defaults provide a neutral, modern look. A specific theme
(dark/light, accent color) can be picked when Phase 3 starts. Until
then assume:

- Dark theme primary
- Accent: a distinguishable highlight color for selected track
  (orange or cyan, decided in Phase 3 kickoff)
- Boxes: 2 px stroke; selected track 3 px + glow
- Typography: shadcn/ui defaults (Inter / system sans)

## Performance targets (v1)

- Idle CPU on the player screen under 5%
- Overlay redraw during playback at the video's source fps without
  dropped frames on a recent Chrome build
- Initial bundle under 500 KB gzipped

## Testing

- Component tests with Vitest + React Testing Library on the overlay
  and player controls
- Playwright e2e for: upload → process (mock) → select track → play
- Frontend tests run via `npm test` / `pnpm test` inside `web/`,
  separate from Python pytest

## Out of scope for v1

- Mobile layout
- Multi-track selection
- Drawing annotations (manual labeling)
- Export / share / clip cutting
- Auth / saved sessions
