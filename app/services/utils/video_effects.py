from moviepy import Clip, vfx


# FadeIn
def fadein_transition(clip: Clip, t: float) -> Clip:
    return clip.with_effects([vfx.FadeIn(t)])


# FadeOut
def fadeout_transition(clip: Clip, t: float) -> Clip:
    return clip.with_effects([vfx.FadeOut(t)])


# SlideIn
def slidein_transition(clip: Clip, t: float, side: str) -> Clip:
    return clip.with_effects([vfx.SlideIn(t, side)])


# SlideOut
def slideout_transition(clip: Clip, t: float, side: str) -> Clip:
    return clip.with_effects([vfx.SlideOut(t, side)])


# Apply 30ms audio fade-in/out to prevent pops at cuts
def apply_audio_fade(clip: Clip, fade_duration: float = 0.03) -> Clip:
    if not hasattr(clip, "audio") or clip.audio is None:
        return clip
    try:
        from moviepy import afx
        audio = clip.audio
        if audio.duration and audio.duration > (fade_duration * 2):
            audio = audio.with_effects([
                afx.AudioFadeIn(fade_duration),
                afx.AudioFadeOut(fade_duration)
            ])
            return clip.with_audio(audio)
    except Exception:
        pass
    return clip


# Apply color grading presets to video clip
def apply_color_preset(clip: Clip, preset: str = "none") -> Clip:
    if not preset or preset == "none":
        return clip
    try:
        if preset == "cinematic_warm":
            return clip.with_effects([vfx.MultiplyColor(1.08)])
        elif preset == "vibrant_punch":
            return clip.with_effects([vfx.Colorx(1.15)])
        elif preset == "moody_dark":
            return clip.with_effects([vfx.MultiplyColor(0.88)])
        elif preset == "vintage_film":
            return clip.with_effects([vfx.MultiplyColor(0.95)])
    except Exception:
        pass
    return clip

