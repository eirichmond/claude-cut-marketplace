"""Build synthetic word-level transcripts for take-selection tests."""

WORD = 0.30   # seconds per word
GAP = 0.05    # gap between words inside an utterance


def transcript(utterances, source="synthetic.wav"):
    """utterances: list of (pause_before_seconds, text).

    Returns a transcribe.py-shaped dict. Word times are deterministic, so
    tests can predict every start and end.
    """
    return timed_transcript(utterances, source)[0]


def timed_transcript(utterances, source="synthetic.wav"):
    """Like transcript(), plus the (start, end) of each utterance."""
    t, words, spans = 0.0, [], []
    for pause, text in utterances:
        t += pause
        first = len(words)
        for i, w in enumerate(text.split()):
            if i:
                t += GAP
            words.append({"word": w, "start": round(t, 3),
                          "end": round(t + WORD, 3)})
            t += WORD
        spans.append((words[first]["start"], words[-1]["end"])
                     if len(words) > first else (round(t, 3), round(t, 3)))
    return ({"source": source, "duration": round(t + 1.0, 3), "words": words},
            spans)


# One session against tests/fixtures/timings/prompter.md:
#  - an off-script intro
#  - s1 and s2 run together with "Fine." (one pause-chunk, three sentences)
#  - a fluffed s3, "retake cut", then a clean s3
#  - s4 only half delivered (rescued partial take)
#  - s5 never said (missing), then an off-script sign-off
SESSION = [
    (0.5, "hi folks quick one today"),
    (1.5, "Welcome back to the channel everyone. Today we are going to fix "
          "the edit. Fine."),
    (1.5, "Open the settings panel on the"),
    (1.0, "retake cut"),
    (1.0, "Open the settings panel on the left side."),
    (1.5, "Click the big export"),
    (1.5, "okay that's a wrap"),
]
