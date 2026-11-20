#!/usr/bin/env python3
"""
Tiancheng Stone — YouTube kanalidan videolarni yuklab olib, avtomatik montaj qilish.

Nima qiladi:
  1) youtube.com/@tiancheng_stone kanalidan videolarni yuklab oladi (yt-dlp)
     - avval yuklanganlarini qayta yuklamaydi (archive.txt)
  2) Har bir videoni Reels/Shorts formatiga montaj qiladi (ffmpeg):
     - 9:16, 1080x1920, xira (blur) fon + markazda video yoki to'liq kesib olish
     - har 3 soniyada "punch-in" zoom (dinamika uchun)
     - toza, tiniq rang: kontrast/saturatsiya + sharpen (grain YO'Q)
     - ovoz balansi (loudnorm), ixtiyoriy fon musiqasi
     - ixtiyoriy logotip (watermark)
     - ixtiyoriy so'zma-so'z kinetik subtitr (faster-whisper)

O'rnatish (bir marta):
  pip install -U yt-dlp faster-whisper
  + ffmpeg o'rnatilgan bo'lishi kerak (Windows: winget install ffmpeg | Mac: brew install ffmpeg)
  + subtitr uchun "Montserrat" shriftini o'rnating (aks holda oddiy shrift ishlatiladi)

Ishlatish misollari:
  python tiancheng_montaj.py                       # oxirgi 5 ta video, subtitrsiz
  python tiancheng_montaj.py --limit 10 --subs     # 10 ta video + subtitr
  python tiancheng_montaj.py --shorts --subs --logo logo.png --music music.mp3
  python tiancheng_montaj.py --only-edit           # yuklamasdan, borlarini montaj qilish
  python tiancheng_montaj.py --max-len 60          # har bir reel 60 soniyadan oshmasin
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

CHANNEL = "https://www.youtube.com/@tiancheng_stone"
W, H = 1080, 1920


# ---------------------------------------------------------------- yordamchi
def run(cmd):
    print("  $", " ".join(str(c) for c in cmd)[:200])
    subprocess.run(cmd, check=True)


def check_tools(need_ytdlp, need_whisper):
    tools = ["ffmpeg", "ffprobe"] + (["yt-dlp"] if need_ytdlp else [])
    for tool in tools:
        if not shutil.which(tool):
            sys.exit(f"XATO: '{tool}' topilmadi. Yuqoridagi o'rnatish qismini bajaring.")
    if need_whisper:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            sys.exit("XATO: subtitr uchun:  pip install faster-whisper")


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    w, h = int(v["width"]), int(v["height"])
    # telefon videolarida burilish (rotate) metadata bo'ladi: 90/270 bo'lsa w va h almashadi
    rot = int(v.get("tags", {}).get("rotate", 0) or 0)
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    return w, h, float(info["format"]["duration"]), has_audio


# ---------------------------------------------------------------- 1. yuklash
def download(channel, out_dir, limit, shorts):
    out_dir.mkdir(parents=True, exist_ok=True)
    url = channel.rstrip("/") + ("/shorts" if shorts else "/videos")
    try:
        run([
            "yt-dlp", url,
            "--playlist-end", str(limit),
            "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/b",
            "--merge-output-format", "mp4",
            "--download-archive", str(out_dir / "archive.txt"),
            "--restrict-filenames",
            "-o", str(out_dir / "%(upload_date)s_%(id)s.%(ext)s"),
            "--no-overwrites", "--ignore-errors",
        ])
    except subprocess.CalledProcessError:
        # --ignore-errors bo'lsa ham bitta video xato bersa yt-dlp 1 qaytaradi — davom etamiz
        print("  ! ba'zi videolar yuklanmadi, borlari bilan davom etamiz")


# ---------------------------------------------------------------- 2. subtitr
def ass_time(t):
    h, t = divmod(t, 3600)
    m, s = divmod(t, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


_WHISPER = None


def make_subs(video, ass_path, lang, words_per_line=2):
    global _WHISPER
    from faster_whisper import WhisperModel
    print("  Whisper: nutq aniqlanmoqda...")
    if _WHISPER is None:  # modelni har video uchun qayta yuklamaslik
        _WHISPER = WhisperModel("small", device="auto", compute_type="auto")
    segments, _ = _WHISPER.transcribe(str(video), language=lang, word_timestamps=True,
                                      vad_filter=True)
    words = [w for seg in segments for w in (seg.words or [])]

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat ExtraBold,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,6,2,2,80,80,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for i in range(0, len(words), words_per_line):
        group = words[i:i + words_per_line]
        start, end = group[0].start, group[-1].end
        # har bir so'z aytilganda oltin rangga o'tadi (karaoke), blok "pop" bo'lib chiqadi
        parts = []
        for w in group:
            ws, we = int((w.start - start) * 1000), int((w.end - start) * 1000)
            txt = re.sub(r"[{}\\]", "", w.word.strip().upper())
            parts.append(r"{\t(%d,%d,\c&H3CC8FF&)}%s{\t(%d,%d,\c&HFFFFFF&)}" % (ws, ws + 1, txt, we, we + 1))
        pop = r"{\fscx70\fscy70\t(0,120,\fscx108\fscy108)\t(120,200,\fscx100\fscy100)}"
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Cap,,0,0,0,,{pop}{' '.join(parts)}")

    ass_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Subtitr tayyor: {len(lines)} qator")
    return len(lines) > 0


# ---------------------------------------------------------------- 3. montaj
def edit(video, out_path, args):
    vw, vh, dur, has_audio = probe(video)
    max_len = min(dur, args.max_len) if args.max_len else dur
    vertical = vh >= vw

    # punch-in zoom: har ZOOM_EVERY soniyada 1.00 <-> 1+zoom almashadi
    zoom = f"(1+{args.zoom}*mod(floor(t/{args.zoom_every}),2))"

    if vertical or args.fill:
        # to'liq ekran: kesib olish + zoom
        base = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"scale=w='trunc({W}*{zoom}/2)*2':h='trunc({H}*{zoom}/2)*2':eval=frame,"
            f"crop={W}:{H}[main]"
        )
    else:
        # gorizontal video: xira fon + markazda video (zoom bilan)
        base = (
            f"[0:v]split[a][b];"
            f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"boxblur=30:3,eq=brightness=-0.08[bg];"
            f"[b]scale={W}:-2,"
            f"scale=w='trunc({W}*{zoom}/2)*2':h=-2:eval=frame[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1[main]"
        )

    # toza, tiniq rang (grain yo'q)
    grade = "[main]eq=contrast=1.06:saturation=1.15:gamma=0.98,unsharp=5:5:0.6:3:3:0.0,format=yuv420p"
    inputs = ["-i", str(video)]
    n_in = 1  # nechta kirish fayli bor (indekslar uchun)
    vchain = base + ";" + grade

    if args.subs:
        ass = out_path.with_suffix(".ass")
        if make_subs(video, ass, args.lang):
            ass_esc = str(ass.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
            vchain += f",ass='{ass_esc}'"

    if args.logo:
        inputs += ["-i", args.logo]
        li, n_in = n_in, n_in + 1
        vchain += (f"[v0];[{li}:v]scale=220:-1,format=rgba,colorchannelmixer=aa=0.85[lg];"
                   f"[v0][lg]overlay=W-w-50:90[vpre]")
    else:
        vchain += "[vpre]"

    # ovoz
    achain = ""
    amap = []
    mi = None
    if args.music:
        inputs += ["-stream_loop", "-1", "-i", args.music]
        mi, n_in = n_in, n_in + 1

    if has_audio and mi is not None:
        achain = (f";[0:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,asplit=2[voice][vkey];"
                  f"[{mi}:a]aresample=48000,volume={args.music_vol}[mus];"
                  f"[mus][vkey]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=300[duck];"
                  f"[voice][duck]amix=inputs=2:duration=first:normalize=0[a]")
    elif has_audio:
        achain = ";[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    elif mi is not None:
        achain = f";[{mi}:a]volume={args.music_vol * 3}[a]"
    if achain:
        amap = ["-map", "[a]"]

    fade_out = max(0, max_len - 0.4)
    vchain += f";[vpre]fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out:.2f}:d=0.4[v]"

    # avval vaqtinchalik faylga yozamiz — yarim yo'lda to'xtasa, keyingi safar "tayyor" deb o'tkazib yubormaydi
    tmp = out_path.with_name(out_path.stem + ".part.mp4")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-stats", *inputs,
         "-filter_complex", vchain + achain,
         "-map", "[v]", *amap,
         "-t", f"{max_len:.2f}",
         "-c:v", "libx264", "-preset", args.preset, "-crf", "17", "-profile:v", "high",
         "-r", "30", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", str(tmp)])
    tmp.replace(out_path)


# ---------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description="Tiancheng Stone: YouTube -> Reels avto-montaj")
    p.add_argument("--channel", default=CHANNEL)
    p.add_argument("--limit", type=int, default=5, help="nechta oxirgi video")
    p.add_argument("--shorts", action="store_true", help="/videos o'rniga /shorts bo'limi")
    p.add_argument("--only-edit", action="store_true", help="yuklamaslik, faqat montaj")
    p.add_argument("--subs", action="store_true", help="so'zma-so'z subtitr (Whisper)")
    p.add_argument("--lang", default=None, help="nutq tili: uz, ru, zh, en (bo'sh = avto)")
    p.add_argument("--logo", help="PNG logotip (shaffof fon)")
    p.add_argument("--music", help="fon musiqasi (mp3)")
    p.add_argument("--music-vol", type=float, default=0.12)
    p.add_argument("--fill", action="store_true", help="gorizontal videoni ham to'liq kesib olish")
    p.add_argument("--zoom", type=float, default=0.08, help="punch-in kuchi (0 = o'chirish)")
    p.add_argument("--zoom-every", type=float, default=3.0, help="necha soniyada zoom almashadi")
    p.add_argument("--max-len", type=float, default=0, help="reel maksimal davomiyligi (s)")
    p.add_argument("--preset", default="slow", help="x264 tezligi: veryfast | medium | slow")
    p.add_argument("--src", default="youtube_videos")
    p.add_argument("--out", default="montaj_tayyor")
    args = p.parse_args()

    for f in (args.logo, args.music):
        if f and not Path(f).is_file():
            sys.exit(f"XATO: fayl topilmadi: {f}")

    check_tools(not args.only_edit, args.subs)
    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if not args.only_edit:
        print("\n== 1) YouTube'dan yuklab olish ==")
        download(args.channel, src, args.limit, args.shorts)

    # yt-dlp birlashtirilmagan oraliq fayllarni (video.f137.mp4) va .part fayllarni o'tkazib yuboramiz
    videos = sorted(v for v in src.glob("*.mp4")
                    if not re.search(r"\.f\d+$", v.stem) and not v.stem.endswith(".part"))
    print(f"\n== 2) Montaj: {len(videos)} ta video ==")
    ok = fail = 0
    for v in videos:
        target = out / f"{v.stem}_reel.mp4"
        if target.exists():
            print(f"- {v.name}: allaqachon tayyor, o'tkazib yuborildi")
            continue
        print(f"- {v.name}")
        try:
            edit(v, target, args)
            print(f"  ✓ {target}")
            ok += 1
        except (subprocess.CalledProcessError, StopIteration, KeyError, ValueError) as e:
            print(f"  ✗ xato: {e}")
            fail += 1

    print(f"\nTayyor! {ok} ta muvaffaqiyatli, {fail} ta xato. Natijalar: {out.resolve()}")


if __name__ == "__main__":
    main()
