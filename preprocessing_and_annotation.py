#!/usr/bin/env python3
"""
Corpus Preprocessing and Annotation Pipeline (UDPipe + Stanza)

Two-stage pipeline for preparing multilingual corpora and annotating them
with UDPipe (via LINDAT REST API) or Stanza (locally), or both.

Stage 1 - Preprocessing:
    Cleans and merges raw sentence files for each language (English, Czech, Greek).
    Removes leading numbers, bullets, and special characters from each line,
    then merges all source files into a single unified corpus file per language.

Stage 2 - Annotation:
    UDPipe: Splits the unified corpus into bundles of 5,000 sentences, sends
    each bundle to the UDPipe REST API, retries on failure, saves per-bundle
    CoNLL-U output, and merges into one complete CoNLL-U file per language.

    Stanza: Loads the unified corpus and annotates it locally using Stanza
    (version 1.11.0) with default tokenizer, POS tagger, lemmatizer, and
    dependency parser. Saves output directly as a CoNLL-U file.

    Checkpoint/resume support is provided for UDPipe to handle interruptions.

#please update paths and file names before running

Usage:
    # Run both stages, both parsers, all languages:
    python preprocessing_and_annotation.py --stage all --language all --parser both

    # Run only preprocessing for English:
    python preprocessing_and_annotation.py --stage preprocess --language english

    # Run UDPipe annotation for Greek only:
    python preprocessing_and_annotation.py --stage annotate --language greek --parser udpipe

    # Run Stanza annotation for Czech only:
    python preprocessing_and_annotation.py --stage annotate --language czech --parser stanza

    # Run annotation for all languages with custom bundle size (UDPipe):
    python preprocessing_and_annotation.py --stage annotate --language all --parser udpipe --bundle-size 3000
"""

import re
import os
import json
import time
import argparse
import urllib.request
import urllib.parse
from datetime import datetime


# ============================================================================
# CONFIGURATION — update these paths before running
# ============================================================================

LANGUAGE_CONFIGS = {
    'greek': {
        'input_files': [
            'ell_news_2020_1M-sentences.txt',
            'ell_wikipedia_2021_1M-sentences.txt',
            'ell_news_2024_1M-sentences.txt',
            'ell_news_2022_1M-sentences.txt',
            'ell_news_2023_1M-sentences.txt',
        ],
        'unified_file':        'el_unified_corpus_sentences.txt',
        'merged_conllu_udpipe':'greek_corpus_udpipe_complete.conllu',
        'merged_conllu_stanza':'greek_corpus_stanza_complete.conllu',
        'udpipe_model':        'greek-gud-ud-2.17-251125',
        'stanza_lang':         'el',
        # Greek letters unicode range preserved during cleaning
        'unicode_range':       r'\u0370-\u03FF\u1F00-\u1FFF',
    },
    'czech': {
        'input_files': [
            'ces_news_2020_1M-sentences.txt',
            'ces_wikipedia_2021_1M-sentences.txt',
            'ces_news_2024_1M-sentences.txt',
            'ces_news_2022_1M-sentences.txt',
            'ces_news_2023_1M-sentences.txt',
        ],
        'unified_file':        'cs_unified_corpus_sentences.txt',
        'merged_conllu_udpipe':'czech_corpus_udpipe_complete.conllu',
        'merged_conllu_stanza':'czech_corpus_stanza_complete.conllu',
        'udpipe_model':        'czech-pdtc-ud-2.17-251125',
        'stanza_lang':         'cs',
        'unicode_range':       None,
    },
    'english': {
        'input_files': [
            'eng_news_2019_1M-sentences.txt',
            'eng_wikipedia_2016_1M-sentences.txt',
            'eng_news_2024_1M-sentences.txt',
            'eng_news_2020_1M-sentences.txt',
            'eng_news_2023_1M-sentences.txt',
        ],
        'unified_file':        'en_unified_corpus_sentences.txt',
        'merged_conllu_udpipe':'english_corpus_udpipe_complete.conllu',
        'merged_conllu_stanza':'english_corpus_stanza_complete.conllu',
        'udpipe_model':        'english-gum-ud-2.17-251125',
        'stanza_lang':         'en',
        'unicode_range':       None,
    },
}

UDPIPE_API_URL  = "https://lindat.mff.cuni.cz/services/udpipe/api/process"
BUNDLE_SIZE     = 5000   # sentences per UDPipe API request
MAX_RETRIES     = 3
RETRY_DELAY     = 30     # seconds between retries
REQUEST_TIMEOUT = 600    # seconds (10 minutes) per request


# ============================================================================
# STAGE 1 — PREPROCESSING
# ============================================================================

def clean_line(line, unicode_range=None):
    """
    Remove leading numbers and special characters from a line.
    Preserves language-specific unicode characters.

    Args:
        line: Raw input line
        unicode_range: Optional unicode range string to preserve (e.g. for Greek)

    Returns:
        Cleaned line string
    """
    # Remove leading digits with optional punctuation (e.g. "1. ", "42) ")
    line = re.sub(r'^\d+[\.\):\-]*\s*', '', line)

    # Remove leading bullets, arrows, currency symbols, emoji, etc.
    line = re.sub(
        r'^[»,;€¢$%!£)•.▪✅❌✓✗➤\-–—\*\+#¾₂→←↑↓▫◦⚫➍➏⚪'
        r'🔴🔵⚠️❄️⭐★☆■□●○▲△▼▽►◄·‧∙⋅¼➐➑]+\s*',
        '', line
    )

    # Remove any remaining non-alphanumeric characters at start,
    # preserving language-specific unicode if specified
    if unicode_range:
        pattern = rf'^[^\w\s{unicode_range}]+'
    else:
        pattern = r'^[^\w\s]+'
    line = re.sub(pattern, '', line, flags=re.UNICODE)

    return line.strip()


def preprocess_language(language, config):
    """
    Clean and merge all source files for one language.

    Args:
        language: Language name string
        config: Language config dict from LANGUAGE_CONFIGS
    """
    print(f"\n{'='*70}")
    print(f"PREPROCESSING — {language.upper()}")
    print(f"{'='*70}\n")

    all_sentences = []
    unicode_range = config.get('unicode_range')

    for filepath in config['input_files']:
        if not os.path.exists(filepath):
            print(f"  WARNING: File not found — {filepath}")
            continue

        print(f"  Reading: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        before = len(all_sentences)
        for line in lines:
            cleaned = clean_line(line, unicode_range)
            if cleaned:
                all_sentences.append(cleaned)

        added = len(all_sentences) - before
        print(f"    Lines read: {len(lines):,}  |  Sentences added: {added:,}")

    output_file = config['unified_file']
    with open(output_file, 'w', encoding='utf-8') as f:
        for sentence in all_sentences:
            f.write(sentence + '\n')

    size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"\n  Output: {output_file}")
    print(f"  Total sentences: {len(all_sentences):,}")
    print(f"  File size: {size_mb:.2f} MB")
    print(f"\n  Sample (first 3 sentences):")
    for i, sent in enumerate(all_sentences[:3], 1):
        print(f"    {i}. {sent[:80]}{'...' if len(sent) > 80 else ''}")

    verify_unified_corpus(config['input_files'], output_file)


def verify_unified_corpus(input_files, unified_file):
    """Print a validation summary comparing original vs unified corpus."""
    print(f"\n  Verification:")
    total_lines = sum(
        sum(1 for _ in open(f, encoding='utf-8'))
        for f in input_files if os.path.exists(f)
    )
    unified_lines = sum(1 for _ in open(unified_file, encoding='utf-8'))
    diff = unified_lines - total_lines

    if abs(diff) <= 10:
        print(f"    OK — {unified_lines:,} lines in unified corpus (diff: {diff:+,})")
    else:
        print(f"    WARNING — Line difference: {diff:+,}  "
              f"(original: {total_lines:,}, unified: {unified_lines:,})")


# ============================================================================
# STAGE 2A — UDPIPE ANNOTATION
# ============================================================================

def load_checkpoint(checkpoint_file):
    """Load progress checkpoint to support resuming interrupted runs."""
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return {'completed': [], 'failed': []}


def save_checkpoint(checkpoint, checkpoint_file):
    """Save progress after each completed bundle."""
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)


def process_bundle_udpipe(bundle_text, model):
    """
    Send one bundle to the UDPipe REST API and return CoNLL-U output.

    Args:
        bundle_text: Plain text sentences (one per line)
        model: UDPipe model identifier string

    Returns:
        tuple: (success: bool, conllu: str or None, error: str or None)
    """
    try:
        params = {
            'data':      bundle_text,
            'model':     model,
            'tokenizer': '',   # default tokenizer
            'tagger':    '',   # default tagger
            'parser':    ''    # default parser
        }
        data = urllib.parse.urlencode(params).encode('utf-8')

        with urllib.request.urlopen(
            UDPIPE_API_URL, data=data, timeout=REQUEST_TIMEOUT
        ) as response:
            result = json.loads(response.read())

        if 'result' not in result or not result['result'].strip():
            return False, None, "Empty or missing result in API response"

        conllu = result['result']
        tokens = sum(
            1 for line in conllu.split('\n')
            if line and not line.startswith('#')
            and '\t' in line and line.split('\t')[0].isdigit()
        )

        if tokens == 0:
            return False, None, "No tokens found in CoNLL-U output"

        return True, conllu, None

    except urllib.error.HTTPError as e:
        return False, None, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, None, f"URL Error: {e.reason}"
    except Exception as e:
        return False, None, f"Unexpected error: {str(e)}"


def annotate_udpipe(language, config, bundle_size=BUNDLE_SIZE):
    """
    Annotate the unified corpus for one language using UDPipe.
    Splits into bundles, annotates each via REST API with retry logic,
    saves per-bundle CoNLL-U files, and merges into a single output file.
    Supports resume from checkpoint.
    """
    print(f"\n{'='*70}")
    print(f"UDPIPE ANNOTATION — {language.upper()}")
    print(f"{'='*70}\n")

    input_file      = config['unified_file']
    model           = config['udpipe_model']
    output_dir      = f"udpipe_output_{language}"
    merged_file     = config['merged_conllu_udpipe']
    checkpoint_file = f"udpipe_checkpoint_{language}.json"

    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(input_file):
        print(f"  ERROR: Unified corpus not found — {input_file}")
        print(f"  Run preprocessing first: --stage preprocess --language {language}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        all_sentences = [line.strip() for line in f if line.strip()]

    total       = len(all_sentences)
    num_bundles = (total + bundle_size - 1) // bundle_size

    print(f"  Corpus:      {input_file}")
    print(f"  Sentences:   {total:,}")
    print(f"  Bundles:     {num_bundles} x {bundle_size:,} sentences")
    print(f"  Model:       {model}\n")

    bundles = []
    for i in range(num_bundles):
        start = i * bundle_size
        end   = min(start + bundle_size, total)
        text  = '\n'.join(all_sentences[start:end])
        bundles.append({
            'id':            i,
            'text':          text,
            'num_sentences': end - start,
            'size_mb':       len(text.encode('utf-8')) / (1024 * 1024)
        })

    checkpoint   = load_checkpoint(checkpoint_file)
    start_time   = datetime.now()
    completed    = 0
    failed       = 0
    total_tokens = 0

    for bundle in bundles:
        bundle_name = f"bundle_{bundle['id']:03d}"
        output_file = os.path.join(output_dir, f"{bundle_name}.conllu")

        if bundle_name in checkpoint['completed']:
            print(f"  [{bundle['id']+1}/{num_bundles}] {bundle_name} — skipping (already done)")
            completed += 1
            continue

        print(f"  [{bundle['id']+1}/{num_bundles}] {bundle_name} "
              f"({bundle['num_sentences']:,} sentences, {bundle['size_mb']:.1f} MB)")

        success = False
        error   = None

        for attempt in range(1, MAX_RETRIES + 1):
            print(f"    Attempt {attempt}/{MAX_RETRIES}...")
            t0 = time.time()
            success, conllu, error = process_bundle_udpipe(bundle['text'], model)
            elapsed = time.time() - t0

            if success:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(conllu)

                tokens = sum(
                    1 for line in conllu.split('\n')
                    if line and not line.startswith('#')
                    and '\t' in line and line.split('\t')[0].isdigit()
                )
                total_tokens += tokens
                checkpoint['completed'].append(bundle_name)
                save_checkpoint(checkpoint, checkpoint_file)
                print(f"    Success — {tokens:,} tokens — {elapsed:.1f}s")
                completed += 1
                break
            else:
                print(f"    Failed: {error}")
                if attempt < MAX_RETRIES:
                    print(f"    Retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)

        if not success:
            checkpoint['failed'].append({
                'bundle':    bundle_name,
                'error':     error,
                'timestamp': datetime.now().isoformat()
            })
            save_checkpoint(checkpoint, checkpoint_file)
            failed += 1
            print(f"    Failed after {MAX_RETRIES} attempts")

        if bundle['id'] < num_bundles - 1:
            time.sleep(2)

    # Merge bundles
    if completed > 0:
        print(f"\n  Merging {completed} bundles into {merged_file}...")
        with open(merged_file, 'w', encoding='utf-8') as outfile:
            for bundle in bundles:
                bundle_file = os.path.join(output_dir, f"bundle_{bundle['id']:03d}.conllu")
                if os.path.exists(bundle_file):
                    with open(bundle_file, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
        size_mb = os.path.getsize(merged_file) / (1024 * 1024)
        print(f"  Merged: {merged_file} ({size_mb:.1f} MB)")

    duration = (datetime.now() - start_time).total_seconds()
    print(f"\n  Summary — {language.upper()} UDPipe:")
    print(f"    Duration:  {duration/3600:.2f}h ({duration/60:.1f} min)")
    print(f"    Completed: {completed}/{num_bundles} bundles")
    print(f"    Failed:    {failed}/{num_bundles} bundles")
    print(f"    Tokens:    {total_tokens:,}")
    if failed > 0:
        print(f"    WARNING: rerun to retry failed bundles (completed ones will be skipped)")


# ============================================================================
# STAGE 2B — STANZA ANNOTATION
# ============================================================================

def annotate_stanza(language, config):
    """
    Annotate the unified corpus for one language using Stanza 1.11.0.
    Uses default tokenizer, POS tagger, lemmatizer, and dependency parser.
    Outputs a single CoNLL-U file.
    """
    print(f"\n{'='*70}")
    print(f"STANZA ANNOTATION — {language.upper()}")
    print(f"{'='*70}\n")

    try:
        import stanza
    except ImportError:
        print("  ERROR: stanza is not installed.")
        print("  Install with: pip install stanza==1.11.0")
        return

    input_file  = config['unified_file']
    merged_file = config['merged_conllu_stanza']
    lang_code   = config['stanza_lang']

    if not os.path.exists(input_file):
        print(f"  ERROR: Unified corpus not found — {input_file}")
        print(f"  Run preprocessing first: --stage preprocess --language {language}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        sentences = [line.strip() for line in f if line.strip()]

    print(f"  Corpus:     {input_file}")
    print(f"  Sentences:  {len(sentences):,}")
    print(f"  Lang code:  {lang_code}")
    print(f"  Stanza version: 1.11.0 (default pipeline)\n")

    # Download model if needed, then load with default settings
    stanza.download(lang_code, verbose=False)
    nlp = stanza.Pipeline(
        lang=lang_code,
        processors='tokenize,pos,lemma,depparse',
        tokenize_pretokenized=True,
        verbose=False
    )

    print(f"  Annotating {len(sentences):,} sentences...")
    start_time = datetime.now()

    # Process in batches and write CoNLL-U incrementally
    batch_size   = 1000
    total_tokens = 0

    with open(merged_file, 'w', encoding='utf-8') as outfile:
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i:i + batch_size]
            doc   = nlp('\n'.join(batch))

            for sent in doc.sentences:
                outfile.write(sent.to_conll() + '\n')
                total_tokens += len(sent.words)

            processed = min(i + batch_size, len(sentences))
            pct       = processed / len(sentences) * 100
            print(f"  Progress: {processed:,}/{len(sentences):,} sentences ({pct:.1f}%)")

    size_mb  = os.path.getsize(merged_file) / (1024 * 1024)
    duration = (datetime.now() - start_time).total_seconds()

    print(f"\n  Output: {merged_file} ({size_mb:.1f} MB)")
    print(f"\n  Summary — {language.upper()} Stanza:")
    print(f"    Duration: {duration/3600:.2f}h ({duration/60:.1f} min)")
    print(f"    Tokens:   {total_tokens:,}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Corpus preprocessing and annotation pipeline (UDPipe + Stanza)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--stage',
        choices=['preprocess', 'annotate', 'all'],
        default='all',
        help='Which stage to run (default: all)'
    )
    parser.add_argument(
        '--language',
        choices=['english', 'czech', 'greek', 'all'],
        default='all',
        help='Which language to process (default: all)'
    )
    parser.add_argument(
        '--parser',
        choices=['udpipe', 'stanza', 'both'],
        default='both',
        help='Which annotation tool to use (default: both)'
    )
    parser.add_argument(
        '--bundle-size',
        type=int,
        default=BUNDLE_SIZE,
        help=f'Sentences per UDPipe API bundle (default: {BUNDLE_SIZE})'
    )

    args = parser.parse_args()

    languages = (
        list(LANGUAGE_CONFIGS.keys())
        if args.language == 'all'
        else [args.language]
    )

    print("=" * 70)
    print("CORPUS PREPROCESSING AND ANNOTATION PIPELINE")
    print("=" * 70)
    print(f"Stage:    {args.stage}")
    print(f"Language: {', '.join(languages)}")
    if args.stage in ('annotate', 'all'):
        print(f"Parser:   {args.parser}")
    print(f"Started:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    for language in languages:
        config = LANGUAGE_CONFIGS[language]

        if args.stage in ('preprocess', 'all'):
            preprocess_language(language, config)

        if args.stage in ('annotate', 'all'):
            if args.parser in ('udpipe', 'both'):
                annotate_udpipe(language, config, bundle_size=args.bundle_size)
            if args.parser in ('stanza', 'both'):
                annotate_stanza(language, config)

    print(f"\n{'='*70}")
    print(f"Done — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
