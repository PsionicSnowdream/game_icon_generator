---
name: game-icon-generator
description: Makes sets of cartoon game icons (items, abilities, status effects, UI buttons) with Pollinations. Same style across the whole set, transparent background, ready for a game UI. Use when someone needs many small icons that look like they belong together.
license: MIT
compatibility: Python 3.9+, Pillow, numpy, and a Pollinations API key in POLLINATIONS_API_KEY.
---

# Game icon generator

Draws icons through the Pollinations image API, cuts the flat green background out, and saves square PNGs.
The point is a consistent set: one fixed style text, only the subject changes.

## Setup

```
pip install pillow numpy
python scripts/make_icon.py --login
```

`--login` signs in with Pollinations: the script prints a link and a code, the user opens the link,
approves, and sets a budget. Icons are paid from the user's own balance. Nobody pastes a key.
The key is saved in `~/.game-icon-generator/key`, so this is needed once.

If you are an agent: run the command, show the link and code to the user, and wait for it to finish.
`--logout` removes the saved key (it can also be revoked at https://enter.pollinations.ai/keys).
For CI there is still `POLLINATIONS_API_KEY` or `--key-file`.

## One icon

```
python scripts/make_icon.py "a red health potion" -o icons/potion.png
```

Options: `--size 256` (final side), `--seed 5` (same seed and prompt give the same icon),
`--keep-background` (skip the cut-out), `--force` (overwrite).

## A set

Put the subjects in a JSON file, name to subject:

```json
{
  "health-potion": "a round glass flask of glowing red liquid with a cork stopper",
  "iron-sword": "a steel sword with a leather-wrapped grip and a small golden crossguard"
}
```

```
python scripts/make_icon.py --batch icons.json -d icons/ --seed 5
```

Existing files are skipped, so a half-finished run can just be started again.
Then look at everything at once:

```
python scripts/contact_sheet.py icons/ -o sheet.png
```

## Writing subjects

- One object per icon. Two or three things on one icon turn into a mess at 64 px.
- Say what the icon means by what it shows. "Enemies +30%" is a crowd of small angry monsters with an arrow up, not the word "more".
- No text or letters in the subject. The model draws gibberish.
- Be concrete about shape and color: "a round glass flask of glowing red liquid", not "a potion".
- Keep the style text the same for the whole set. Change it only if you redo the whole set. `--style-file` reads it from a file.
- A subject that is mostly green on the green background can lose parts to the cut-out. Pick another background color in the style text for those.

## Look at the result

Check the sheet, not single files. Things that go wrong most often: a second object sneaking in,
a halo of background color on the edge, an icon that is clearly a different style from the rest.
Redo those with another `--seed`, one name at a time (put just that name in a small JSON and use `--force`).

## Limits

- The default model is `microsoft/mai-image-2.7-flash`. It refuses images smaller than 768 px, so the script asks for 768 and shrinks.
- About 12 requests a minute. The script uses 3 parallel requests and waits and retries when the API says to slow down.
- Roughly 0.0045 pollen per image. Check your balance before a big set.
- Check your platform's rules for images before uploading generated art (for example no alcohol, gambling or gore on kid-oriented platforms).

Made with [pollinations.ai](https://pollinations.ai).
