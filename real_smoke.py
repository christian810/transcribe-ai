"""Run optional real inference against authorized local speech fixtures.
python tests/real_smoke.py --es /path/spanish.wav --ca /path/catalan.wav
"""
import argparse
from pathlib import Path
import tempfile
from faster_whisper import WhisperModel
from media import normalize
from test_media import silent_wav


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--es', type=Path, required=True)
    parser.add_argument('--ca', type=Path, required=True)
    parser.add_argument('--model', default='small')
    args = parser.parse_args()
    model = WhisperModel(args.model, device='cpu', compute_type='int8')
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        for language, source in [('es', args.es), ('ca', args.ca)]:
            wav = folder / (language + '.wav')
            normalize(source.resolve(), wav)
            segments, info = model.transcribe(str(wav), language=language, vad_filter=True,
                                              condition_on_previous_text=False)
            text = ' '.join(s.text for s in segments).strip()
            assert text, f'Empty {language} result'
            print(language, info.language, text)
        silence = folder / 'silence.wav'
        silent_wav(silence)
        segments, _ = model.transcribe(str(silence), vad_filter=True, condition_on_previous_text=False)
        assert not ''.join(s.text for s in segments).strip(), 'Silence hallucination'
        print('Silence: passed. Listen and compare speech text manually for accuracy.')


if __name__ == '__main__':
    main()
