# Merriam-Webster Dictionary CLI

A Python tool for looking up word definitions using the Merriam-Webster 
Collegiate Dictionary API.

## What it Does 

- Show all meanings for the word looked up
- Display part of speech (noun, verb, etc.)
- Optional etymology information

## Usage

```bash
./lookup_mw_dict.py <word>
./lookup_mw_dict.py <word> -e        # Include etymology
```

## Setup

First obtain an API key from Merriam Webster's 
[developer site](https://www.dictionaryapi.com/), 
it's free for non-commercial use. Then
set your API key as an environment variable:
```bash
export MW_API_KEY="your_api_key_here"
```

## Example

```bash
> ./lookup_mw_dict.py apple -e

============================================================

Word: apple
------------------------------------------------------------
Part of Speech: noun

Meanings (2):
  1. the fleshy, usually rounded red, yellow, or green edible  fruit of a usually cultivated tree (genus Malus) of the rose family
  2. a fruit (such as a star apple) or other vegetative growth (such as an oak apple) suggestive of an apple

Etymology:
  Middle English appel, from Old English æppel; akin to Old High German apful apple, Old Irish ubull, Old Church Slavic ablŭko

============================================================

```
