# KAKU & RONDO — test video #2 "Square Track" (vertical 9:16, 60 fps, 25.6 s = 12 bars at 112.5 BPM, loops)

Purpose: a NON-PUBLIC test so the owner can judge the concept "KAKU & RONDO" (wordless surreal sports-music comedy).
Design doc (owner-facing): /home/user/AI/drafts/2026-10-16-企画書-金盾チャンネル設計.md (see the KAKU section and episode #2).
Rules: /home/user/AI/tools/nonverbal/POLICY.md. Melody is a placeholder generated from the cube's faces (not for publishing).

Characters: KAKU = 1.8 m walnut cube, cream headband (always horizontal, slides when tipping), knot = where Kaku looks,
one chipped corner (faces F#, A, D' around it). Moves only by tipping 90 deg, one tip per beat, each landing = one marimba note
(face -> note: D E F# A B D'). Straight line = a 4-note loop; zigzag = the real melody. RONDO = blue steel ball, brass line;
fast, can't turn sharply; each brass-line touch = a vibraphone tick (triplet eighths). Stands = thousands of human-height brass
tuning forks; they glow/ring for Kaku's notes (6 sections = 6 notes). TI = one tiny fork near the finish that only rings to the
note "TI" which Kaku cannot play -> never rings. Referee = wooden metronome. Starter = faceless ceramic stickman with a mallet.

Beat map (beat = 0.5333 s; bar = 4 beats; cuts only on bar heads):
- b0 (0.00): frame 0 (start line, stands humming, starter mid-swing). b1 (0.53): start fork struck (first impact, must be weaker than the finale).
- b2..b9: first straight (+x), Kaku lands each beat; Rondo leads.  bar1 (2.13-4.27): high top-down reveal: the track is SQUARE.
- ~b8-b15: Rondo slows and swings wide at corner 1; the stands turn to watch Rondo (gag) with an unsettled chord; Kaku turns square at b10 and takes the lead.
- b10..b17 second straight; corner 2 (Kaku turns b18); Rondo swings wide again b20-b25 (stands turn again).
- b18..b25 third straight; b26 Kaku turns into the last straight; b27 = HESITATION (leans toward the straight way, only the metronome click).
- b28..b40: Kaku takes the zigzag score path: placeholder melody E F# A B E D E F# D A F# A D' (ends with the signature F#-A-D' as an L of footprints).
  Corner 3 (b31-b35): Rondo swings wide but the stands DO NOT turn this time (they keep listening to Kaku).
- ~b38.5 Rondo overtakes on the outside; Rondo crosses the finish at 20.86 s (b39.1); Kaku lands across the line at b40 (21.33 s, bar 10 head).
- b40: whole stand glows gold + rings (biggest moment). b41.6: Kaku's knot turns toward TI; TI does not ring.
- b44-b48: long lens on the scoreboard: cube icon shows a note (won the song), ball icon shows 1 (won the race); at b45 it flips back to 0-0; camera pulls back to frame 0 (seamless loop).
Shots: bar0 start (front, infield side); bar1 high reveal; bar2 low inside corner 1; bar3 rail side 2; bar4 corner 2 high outside; bar5 rail side 3;
bar6 last straight from the front (two ways on the ground: outlined straight cells vs faint warm score squares); bar7 top-down footprints;
bar8 low rail with Rondo closing; bar9 finish line from the far side; bar10 gold stand -> TI; bar11 scoreboard -> back to frame 0.

Files: preview video /tmp/claude-0/-home-user-AI/a8d01661-3d44-5b73-963d-5c11d7fedaad/scratchpad/kaku/preview_540.mp4 (540x960).
Code: timeline.py (all timing), camera.py (shots), kaku.glsl (scene), audio.py (sound), build.py.
Render speed ~0.4 s/frame at 540x960 on CPU. The final will be 1080x1920.
