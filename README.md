# Merriam-Webster Dictionary CLI

A Python tool for looking up word definitions using the Merriam-Webster
Collegiate Dictionary API.

## Features

- Show all meanings for the word looked up
- Display part of speech (noun, verb, etc.)
- Optional etymology information
- No external dependencies (uses Python standard library only)

## Installation

Run the install script:

```bash
curl -fsSL https://raw.githubusercontent.com/quietlyecho/mw-dict-cli/main/install.sh | bash
```

This installs the `mw` command to `~/.local/bin`. Make sure this directory is in your PATH.

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
```

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
