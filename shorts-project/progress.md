# Fantasy "what if" 3D Shorts — progress

## Status (2026-11-10)
- Phase 0: PARTIAL. Hardware, tools, network and render benchmark measured. Reference inventory BLOCKED.
- Phase 1A onward: NOT STARTED. Blocked: the 5 reference videos are not on this machine.

## Done since
- Official YouTube facts verified: see verified_facts.md.
- Session moved to environment "Shorts pipeline (claude repo)" with support.google.com allowed.

## Blockers
1. Reference videos and the pre-supplied project data live on the user's Windows PC
   (C:\Users\suvam\ricks clip(cloud)\reference and \project). Not present in the cloud container;
   no computer folder is shared with this session.
2. No GPU. Eevee does not start headless (libEGL.so.1 missing; apt package refresh stalls).
3. Network policy blocks: download.blender.org, huggingface.co, github.com release pages, polyhaven,
   ambientcg, pixabay, freesound, incompetech, kenney, quaternius, mixamo, sketchfab, opengameart,
   fonts.google.com, youtube.com, support.google.com. Reachable: PyPI, npm, Ubuntu archive,
   raw.githubusercontent.com.

## Measured (phase0/bench.py; toy scene: 1 rigged primitive character, 36 set objects, 3 lights, DoF f/1.8, motion blur, 1080x1920)
- Machine: Ubuntu 24.04, 4 vCPU Xeon 2.1 GHz, 15 GB RAM, 31 GB free disk, no GPU.
- Blender 5.2.3 (pip `bpy`, Python 3.13.18), ffmpeg 6.1.1.
- Cycles CPU 64 spp + denoise: 172.6 s, 167.9 s per frame (mean 170 s).
- Cycles CPU 8 spp + denoise: 30.1 s, 29.7 s per frame (mean 30 s).
- Eevee: fails to start (exit 134).
- 30 s Short (900 frames): 42.5 h at 64 spp; 7.5 h at 8 spp. 45 s (1350 frames): 63.8 h; 11.3 h.

## Next step on resume
Get the reference videos onto a machine the agent can read, then start Phase 1A.

## 2026-11-13: Short 01 (full, 34 s)
- short01/scene.py (6 shots), post.py + timeline.json, vo/ (Kokoro am_michael), package.md.
- Resume render: python short01/scene.py -- <frames_dir> 6 2   (skips existing frames)
- Then: python short01/post.py short01/timeline.json <frames_dir> short01/vo short01/Anton-Regular.ttf short01/out/short01.mp4
