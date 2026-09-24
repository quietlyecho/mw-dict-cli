#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

PROG = "mw"
MW_API_URL = (
    "https://www.dictionaryapi.com/api/v3/references/collegiate/json/"
)


class MWAPIError(Exception):
    """Raised when the Merriam-Webster API cannot be queried."""


def warn(message: str) -> None:
    """
    Print a diagnostic to stderr, prefixed with the program name.

    Parameters
    ----------
    message : str
        The diagnostic to print.
    """
    print(f"{PROG}: {message}", file=sys.stderr)


def parse_parts_of_speech(value: str) -> list[str]:
    """
    Split a `-p` option-argument on commas.

    Parameters
    ----------
    value : str
        A comma-separated list, e.g. "noun,verb".

    Returns
    -------
    list of str
        The non-empty, whitespace-stripped items.

    Raises
    ------
    argparse.ArgumentTypeError
        If the list has no non-empty items.
    """
    parts = [pos.strip() for pos in value.split(',') if pos.strip()]
    if not parts:
        raise argparse.ArgumentTypeError(
            "expected a comma-separated list such as noun,verb, "
            f"got {value!r}"
        )
    return parts


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser.

    Returns
    -------
    argparse.ArgumentParser
        The parser for the `mw` command.
    """
    arg_parser = argparse.ArgumentParser(prog=PROG)

    arg_parser.add_argument(
        "word",
        type=str,
        help="Look up a word in the Merriam-Webster Collegiate Dictionary"
    )

    arg_parser.add_argument(
        "-e", "--etymology",
        action="store_true",
        help="Include etymology information (if available)"
    )

    arg_parser.add_argument(
        "-p", "--part-of-speech",
        action="append",
        type=parse_parts_of_speech,
        metavar="POS[,POS...]",
        help=(
            "Only show entries for the given comma-separated part(s) of "
            "speech, e.g. noun,verb (case-insensitive; repeatable)"
        )
    )

    return arg_parser


def use_style() -> bool:
    """
    Decide whether to emit ANSI styling on stdout.

    Returns
    -------
    bool
        True if stdout is a terminal and `NO_COLOR` is unset or empty.

    Notes
    -----
    Follows the convention at https://no-color.org.
    """
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def process_formatting_tokens(text: str, style: bool = False) -> str:
    """
    Process Merriam-Webster formatting and punctuation tokens.

    Based on section 2.29.1 of the MW API documentation, these tokens
    mark up text according to its intended presentation.

    Tokens handled:
    - {b}...{/b}: Bold text (ANSI bold if `style`, else plain)
    - {it}...{/it}: Italic text (ANSI italic if `style`, else plain)
    - {sc}...{/sc}: Small caps (rendered as uppercase)
    - {sup}...{/sup}: Superscript (Unicode superscripts where possible)
    - {bc}: Bold colon (rendered as ": ")
    - {ldquo}: Left double quote
    - {rdquo}: Right double quote
    - {inf}: Inferior/subscript marker
    - {p_br}: Page break (removed)
    - {sx|...}: Cross-references and other complex tokens (content
      extracted)

    Parameters
    ----------
    text : str
        Text containing MW formatting tokens.
    style : bool, default False
        If True, render bold and italic with ANSI escape codes.

    Returns
    -------
    text : str
        Text with formatting tokens processed for terminal display.
    """
    if not text:
        return text

    # Handle paired formatting tags. Without styling, the catch-all at
    # the end strips the bare {b}/{it} markers.
    if style:
        text = re.sub(r'\{b\}(.*?)\{/b\}', r'\033[1m\1\033[0m', text)
        text = re.sub(r'\{it\}(.*?)\{/it\}', r'\033[3m\1\033[0m', text)

    # Small caps: convert to uppercase
    text = re.sub(r'\{sc\}(.*?)\{/sc\}', lambda m: m.group(1).upper(), text)

    # Superscript: use Unicode superscript characters where possible
    superscript_map = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
    text = re.sub(
        r'\{sup\}(.*?)\{/sup\}',
        lambda m: m.group(1).translate(superscript_map),
        text,
    )

    # Single tokens
    # Bold colon
    text = text.replace('{bc}', ': ')

    # Quotation marks
    text = text.replace('{ldquo}', '"')
    text = text.replace('{rdquo}', '"')

    # Inferior/subscript (simply remove marker, keep content)
    text = re.sub(r'\{inf\}(.*?)\{/inf\}', r'\1', text)

    # Page breaks (remove entirely)
    text = text.replace('{p_br}', '')

    # Cross-references and other pipe-delimited tokens: keep just the
    # display text (the first part before |)
    text = re.sub(r'\{([a-z_]+)\|([^}|]+)(?:\|[^}]*)?\}', r'\2', text)

    # Remove any remaining unhandled tokens
    text = re.sub(r'\{[^}]+\}', '', text)

    return text.strip()


def extract_definitions_from_sseq(
    sseq: list,
    style: bool = False,
) -> list[str]:
    """
    Extract all definitions from the sense sequence structure.

    Parameters
    ----------
    sseq : list
        MW sense sequence, nested as [[sense_type, sense_data], ...].
    style : bool, default False
        Passed through to `process_formatting_tokens`.

    Returns
    -------
    list of str
        Unique definitions in order of appearance.
    """
    definitions = []

    for sense_group in sseq:
        for sense_item in sense_group:
            if isinstance(sense_item, list) and len(sense_item) >= 2:
                sense_data = sense_item[1]

                # The actual definition is in the 'dt' (defining text) field
                if isinstance(sense_data, dict) and 'dt' in sense_data:
                    for dt_item in sense_data['dt']:
                        if isinstance(dt_item, list) and len(dt_item) >= 2:
                            dt_type = dt_item[0]
                            dt_content = dt_item[1]

                            # 'text' type contains the actual definition
                            if dt_type == 'text':
                                # Process formatting tokens properly
                                clean_text = process_formatting_tokens(
                                    dt_content, style
                                )
                                # If the first character is a colon, remove it
                                if clean_text.startswith(':'):
                                    clean_text = clean_text[1:].strip()
                                if clean_text and clean_text not in definitions:
                                    definitions.append(clean_text)

    return definitions


def extract_etymology(entry: dict, style: bool = False) -> str | None:
    """
    Extract etymology information from an entry.

    Parameters
    ----------
    entry : dict
        An MW entry; etymology lives in its 'et' field.
    style : bool, default False
        Passed through to `process_formatting_tokens`.

    Returns
    -------
    str or None
        The etymology text, or None if the entry has none.
    """
    if 'et' not in entry:
        return None

    etymology_parts = []
    for et_item in entry['et']:
        if isinstance(et_item, list) and len(et_item) >= 2:
            et_type = et_item[0]
            et_content = et_item[1]

            # 'text' type contains the etymology text
            if et_type == 'text':
                # Process formatting tokens properly
                clean_text = process_formatting_tokens(et_content, style)
                if clean_text:
                    etymology_parts.append(clean_text)

    return ' '.join(etymology_parts) if etymology_parts else None


def matches_part_of_speech(
    functional_label: str | None,
    parts_of_speech: list[str],
) -> bool:
    """
    Check whether an entry's functional label is one of the requested ones.

    Parameters
    ----------
    functional_label : str or None
        The entry's `fl` field, e.g. "noun" or "verb".
    parts_of_speech : list of str
        Requested parts of speech.

    Returns
    -------
    bool
        True if the label matches any requested part of speech,
        ignoring case and surrounding whitespace.

    Notes
    -----
    A label carrying a qualifier after a comma (e.g. "noun, plural in form")
    matches on the part before the comma.
    """
    if not functional_label:
        return False

    label = functional_label.split(',')[0].strip().lower()
    return label in {pos.strip().lower() for pos in parts_of_speech}


def fetch_mw_data(word: str, api_key: str) -> list:
    """
    Query the Merriam-Webster Collegiate Dictionary API for a word.

    Parameters
    ----------
    word : str
        The word or phrase to look up.
    api_key : str
        API key for the Merriam-Webster API.

    Returns
    -------
    list
        The decoded JSON response: entry dicts on a hit, suggestion
        strings on a near miss, or an empty list.

    Raises
    ------
    MWAPIError
        If the API is unreachable, returns an HTTP error, or returns
        something other than JSON (e.g. when the API key is invalid).
    """
    url = (
        MW_API_URL
        + urllib.parse.quote(word, safe='')
        + "?"
        + urllib.parse.urlencode({"key": api_key})
    )

    try:
        with urllib.request.urlopen(url) as response:
            body = response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        raise MWAPIError(f"MW API returned HTTP {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise MWAPIError(f"cannot reach MW API: {e.reason}") from e

    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        # MW answers a bad key with a plain-text message, not JSON.
        reply = body.strip().splitlines()[0] if body.strip() else "(empty)"
        raise MWAPIError(f"unexpected reply from MW API: {reply}") from e


def lookup_mw_collegiate_dict(
    word: str,
    api_key: str,
    show_etymology: bool = False,
    parts_of_speech: list[str] | None = None,
    style: bool = False,
) -> bool:
    """
    Look up a word in the Merriam-Webster API and print its definitions.

    Parameters
    ----------
    word : str
        The word to look up.
    api_key : str
        API key for the Merriam-Webster API.
    show_etymology : bool, default False
        If True, include etymology information in the output.
    parts_of_speech : list of str, optional
        If given, only show entries whose part of speech is one of these
        (e.g. ["noun", "verb"]).
    style : bool, default False
        If True, render bold and italic with ANSI escape codes.

    Returns
    -------
    bool
        True if at least one entry was printed, False if nothing matched.
        Diagnostics for the no-match case go to stderr.

    Raises
    ------
    MWAPIError
        If the API cannot be queried; see `fetch_mw_data`.
    """
    data = fetch_mw_data(word, api_key)

    # Check if we got suggestions instead of definitions
    if data and isinstance(data[0], str):
        warn(
            f"no definition found for '{word}'; "
            f"did you mean: {', '.join(data[:5])}?"
        )
        return False

    # Find all matching entries for the word
    matching_entries = []
    for entry in data:
        if isinstance(entry, dict):
            entry_id = entry.get('meta', {}).get('id', '')
            # Entry ids may carry homograph numbers, e.g. "battle:1"
            if entry_id.split(':')[0].lower() == word.lower():
                matching_entries.append(entry)

    if not matching_entries:
        warn(f"no definition found for '{word}'")
        return False

    if parts_of_speech:
        available = []
        for entry in matching_entries:
            label = entry.get('fl')
            if label and label not in available:
                available.append(label)

        matching_entries = [
            entry for entry in matching_entries
            if matches_part_of_speech(entry.get('fl'), parts_of_speech)
        ]

        if not matching_entries:
            warn(
                f"no {' / '.join(parts_of_speech)} definition found for "
                f"'{word}'; available parts of speech: "
                f"{', '.join(available) or 'none'}"
            )
            return False

    # Display all matching entries
    divider_lv0 = "=" * 60
    print(f"\n{divider_lv0}\n")

    for idx, entry in enumerate(matching_entries, 1):
        # Extract word info
        word_id = entry.get('meta', {}).get('id', word)
        functional_label = entry.get('fl', 'N/A')

        # Print header
        if len(matching_entries) > 1:
            len_divider = len(f"| Entry {idx}: {word_id} |")
            divider = "+" + "-" * (len_divider - 2) + "+"
            print(divider)
            print(f"| Entry {idx}: {word_id} |")
            print(divider)
        else:
            len_divider = len(f"| Word: {word_id} |")
            divider = "+" + "-" * (len_divider - 2) + "+"
            print(divider)
            print(f"| Word: {word_id} |")
            print(divider)
        print()
        print(f"Part of Speech: {functional_label}")
        print()

        # Extract all definitions from the full 'def' structure
        definitions = []
        if 'def' in entry:
            for def_section in entry['def']:
                if 'sseq' in def_section:
                    definitions.extend(
                        extract_definitions_from_sseq(
                            def_section['sseq'], style
                        )
                    )

        # If no full definitions found, fall back to shortdef
        if not definitions and 'shortdef' in entry:
            definitions = entry['shortdef']

        # Display all meanings
        if definitions:
            print(f"Meanings ({len(definitions)}):")
            for i, definition in enumerate(definitions, 1):
                print(f"  {i}. {definition}")
        else:
            print("No definitions available.")
        print()

        # Display etymology if requested
        if show_etymology:
            etymology = extract_etymology(entry, style)
            if etymology:
                print("Etymology:")
                print(f"  {etymology}")
                print()

    print(divider_lv0)
    return True


def main(argv: list[str] | None = None) -> int:
    """
    Run the `mw` command.

    Parameters
    ----------
    argv : list of str, optional
        Command-line arguments, excluding the program name. Defaults to
        `sys.argv[1:]`.

    Returns
    -------
    int
        Exit status, following grep(1): 0 if a definition was found,
        1 if none was, 2 on a usage or runtime error.
    """
    arg_parser = build_arg_parser()
    args = arg_parser.parse_args(argv)

    # Each `-p` yields a list; flatten `-p noun -p verb,adverb`.
    parts_of_speech = [
        pos for group in args.part_of_speech or [] for pos in group
    ] or None

    api_key = os.getenv("MW_API_KEY")
    if not api_key:
        warn("MW_API_KEY is not set; see the README for setup")
        return 2

    try:
        found = lookup_mw_collegiate_dict(
            word=args.word,
            api_key=api_key,
            show_etymology=args.etymology,
            parts_of_speech=parts_of_speech,
            style=use_style(),
        )
    except MWAPIError as e:
        warn(str(e))
        return 2

    return 0 if found else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # Reader went away (e.g. `mw word | head -1`). Point stdout at
        # devnull so the interpreter's final flush doesn't raise again;
        # exit as if killed by SIGPIPE, like other Unix filters.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(128 + 13)
