#!/usr/bin/env python3

import argparse
import json
import os
import pprint
import re
import sys
import urllib.request
import urllib.error

# Find the value of `API_KEY` from environment variable
MW_API_KEY = os.getenv("MW_API_KEY")

# Set up argument parser
arg_parser = argparse.ArgumentParser()

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

args = arg_parser.parse_args()


def process_formatting_tokens(text):
    """
    Process Merriam-Webster formatting and punctuation tokens.

    Based on section 2.29.1 of the MW API documentation, these tokens
    mark up text according to its intended presentation.

    Tokens handled:
    - {b}...{/b}: Bold text (rendered with ANSI codes)
    - {it}...{/it}: Italic text (rendered with ANSI codes)
    - {sc}...{/sc}: Small caps (rendered as uppercase)
    - {sup}...{/sup}: Superscript (rendered with Unicode superscript where possible)
    - {bc}: Bold colon (rendered as ": ")
    - {ldquo}: Left double quote
    - {rdquo}: Right double quote
    - {inf}: Inferior/subscript marker
    - {p_br}: Page break (removed)
    - {sx|...}: Cross-references and other complex tokens (content extracted)

    Parameters
    ----------
    text : str
        Text containing MW formatting tokens.

    Returns
    -------
    text : str
        Text with formatting tokens processed for terminal display.
    """
    if not text:
        return text

    # Handle paired formatting tags
    # Bold: use ANSI escape codes for terminal display
    text = re.sub(r'\{b\}(.*?)\{/b\}', r'\033[1m\1\033[0m', text)

    # Italic: use ANSI escape codes for terminal display
    text = re.sub(r'\{it\}(.*?)\{/it\}', r'\033[3m\1\033[0m', text)

    # Small caps: convert to uppercase
    text = re.sub(r'\{sc\}(.*?)\{/sc\}', lambda m: m.group(1).upper(), text)

    # Superscript: use Unicode superscript characters where possible
    superscript_map = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
    text = re.sub(r'\{sup\}(.*?)\{/sup\}', lambda m: m.group(1).translate(superscript_map), text)

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

    # Handle cross-references and other complex tokens with pipe-delimited content
    # Extract just the display text (first part before |)
    text = re.sub(r'\{([a-z_]+)\|([^}|]+)(?:\|[^}]*)?\}', r'\2', text)

    # Remove any remaining unhandled tokens
    text = re.sub(r'\{[^}]+\}', '', text)

    return text.strip()


def extract_definitions_from_sseq(sseq):
    """
    Extract all definitions from the sense sequence structure.
    The sseq structure is nested: [[sense_type, sense_data], ...]
    """
    definitions = []

    for sense_group in sseq:
        for sense_item in sense_group:
            if isinstance(sense_item, list) and len(sense_item) >= 2:
                sense_type = sense_item[0]
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
                                clean_text = process_formatting_tokens(dt_content)
                                # If the first character is a colon, remove it
                                if clean_text.startswith(':'):
                                    clean_text = clean_text[1:].strip()
                                if clean_text and clean_text not in definitions:
                                    definitions.append(clean_text)

    return definitions


def extract_etymology(entry):
    """
    Extract etymology information from an entry.
    Etymology is stored in the 'et' field and may contain nested structure.
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
                clean_text = process_formatting_tokens(et_content)
                if clean_text:
                    etymology_parts.append(clean_text)

    return ' '.join(etymology_parts) if etymology_parts else None


# Define function to look up word
def lookup_mw_collegiate_dict(
    word,
    api_key: str = MW_API_KEY,
    show_etymology: bool = False,
):
    """
    Look up a word in the Merriam-Webster Dictionary API and return its definition.

    Args:
        word: The word to look up
        api_key: API key for Merriam-Webster API
        show_etymology: If True, include etymology information in the output
    """

    url = (
        "https://www.dictionaryapi.com/api/v3/references/collegiate/json/"
        f"{word}?key={api_key}"
    )

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise Exception(f"Error fetching data from MW API: {e.code}")

    # Check if we got suggestions instead of definitions
    if data and isinstance(data[0], str):
        print(f"No definition found for '{word}'. Did you mean: {', '.join(data[:5])}?")
        return

    # Find all matching entries for the word
    matching_entries = []
    for entry in data:
        if isinstance(entry, dict):
            entry_id = entry.get('meta', {}).get('id', '')
            # Check if this entry matches our word (may include homograph numbers like "battle:1")
            if entry_id.split(':')[0].lower() == word.lower():
                matching_entries.append(entry)

    if not matching_entries:
        print(f"No definition found for '{word}'.")
        return

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
                    definitions.extend(extract_definitions_from_sseq(def_section['sseq']))

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
            etymology = extract_etymology(entry)
            if etymology:
                print(f"Etymology:")
                print(f"  {etymology}")
                print()

    print(divider_lv0)


# Main execution
if __name__ == "__main__":
    lookup_mw_collegiate_dict(word=args.word, show_etymology=args.etymology)
