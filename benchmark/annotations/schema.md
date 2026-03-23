# Annotation Schema

PerceptionComp annotations are stored as a flat JSON list. Each element corresponds to one five-choice question.

## Fields

- `key`: string or integer question identifier
- `video_id`: video filename stem; the corresponding video is expected at `benchmark/videos/<video_id>.mp4`
- `question`: question text
- `answer_choice_0` to `answer_choice_4`: five candidate answers
- `answer_id`: zero-based index of the correct answer
- `answer`: text form of the correct answer
- `category`: semantic category label
- `difficulty`: integer difficulty label

## Notes

- The official release file is currently `benchmark/annotations/official/1-1114.json`.
- The benchmark uses five-way multiple choice throughout the current release.
- Split files and construction-era question files are preserved separately under `benchmark/annotations/splits/` and `benchmark/annotations/legacy/`.
