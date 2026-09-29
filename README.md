# Merriam-Webster Dictionary CLI

A Python tool for looking up word definitions using the Merriam-Webster
Collegiate Dictionary API.

## Features

- Show all meanings for the word looked up
- Display part of speech (noun, verb, etc.)
- Optional etymology information
- Filter entries by part of speech
- No external dependencies (uses Python standard library only)

## Installation

Install with [pipx](https://pipx.pypa.io) (`brew install pipx` on
macOS), straight from GitHub:

```bash
pipx install git+https://github.com/quietlyecho/mw-dict-cli
pipx ensurepath     # once, if ~/.local/bin is not yet on your PATH
```

`pipx upgrade mw-dict-cli` updates it, `pipx uninstall mw-dict-cli`
removes it, and `mw --version` reports the installed version.
`uv tool install git+https://github.com/quietlyecho/mw-dict-cli` works
too, if you use uv.

For development, `pipx install -e .` from a clone installs `mw` so that
edits take effect immediately.

If you installed with the old `install.sh` script, delete that copy
first: `rm ~/.local/bin/mw`.

## Setup

Obtain an API key from Merriam Webster's
[developer site](https://www.dictionaryapi.com/)
(free for non-commercial use), then set it as an environment variable:

```bash
export MW_API_KEY="your_api_key_here"
```

## Usage

```bash
mw <word>
mw <word> -e        # Include etymology
mw -p verb <word>   # Only show entries where the word is a verb
mw -p noun,adjective <word>
mw --part-of-speech=noun,verb <word>
mw -p noun -p verb <word>
mw <word> <word>...  # Look up several words
printf 'apple\npear\n' | mw   # Read words from stdin (also: `mw -`)
```

`mw` exits 0 if any word was found, 1 if none was, and 2 on an error,
like `grep`. Diagnostics go to stderr, so `mw word >/dev/null` works as
a check. Bold and italics are shown only on a terminal, and never when
`NO_COLOR` is set.

Part-of-speech names are matched case-insensitively against Merriam-Webster's
labels (e.g. `noun`, `verb`, `adjective`, `adverb`, `phrase`). If nothing
matches, the available parts of speech for the word are listed.

## Example

```bash
> mw apple -e

============================================================

+-------------+
| Word: apple |
+-------------+

Part of Speech: noun

Meanings (2):
  1. the fleshy, usually rounded red, yellow, or green edible pome fruit of a usually cultivated tree (genus Malus) of the rose family
  2. a fruit (such as a star apple) or other vegetative growth (such as an oak apple) suggestive of an apple

Etymology:
  Middle English appel, from Old English æppel; akin to Old High German apful apple, Old Irish ubull, Old Church Slavic ablŭko

============================================================
```
