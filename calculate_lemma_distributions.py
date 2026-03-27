#!/usr/bin/env python3
"""
Lemma-Level Plural Ratio Distribution Analysis

Calculates plural ratio distributions for noun lemmas and generates LaTeX tables
showing distribution across ratio categories (=0, 0<r<=0.1, 0.1<r<0.9, 0.9<=r<1, =1).

#please update paths and file names
Usage:
    python calculate_lemma_distributions.py \
        --czech-stanza path/to/czech_stanza.conllu \
        --czech-udpipe path/to/czech_udpipe.conllu \
        --english-stanza path/to/english_stanza.conllu \
        --english-udpipe path/to/english_udpipe.conllu \
        --greek-stanza path/to/greek_stanza.conllu \
        --greek-udpipe path/to/greek_udpipe.conllu \
        --output results/lemma_distribution_table.tex

Output:
    - LaTeX table with lemma counts per ratio category
    - Statistics for both "All lemmas" and ">=10 occurrences"
    - Percentages summing to 100% within each section
"""

import argparse
import sys
from collections import defaultdict


def extract_lemma_stats_from_conllu(conllu_file, language):
    """
    Extract lemma statistics directly from a CoNLL-U file.

    Args:
        conllu_file: Path to CoNLL-U file
        language: Language name (Czech, English, Greek)

    Returns:
        list of dicts with sing/plur/dual/ptan counts per lemma,
        or None on error.
    """

    lemma_counts = defaultdict(lambda: {'sing': 0, 'plur': 0, 'ptan': 0, 'dual': 0})

    try:
        with open(conllu_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or line == '':
                    continue
                parts = line.split('\t')
                if len(parts) < 10:
                    continue

                token_id = parts[0]
                lemma    = parts[2]
                upos     = parts[3]
                feats    = parts[5]

                if '-' in token_id or '.' in token_id:
                    continue
                if upos != 'NOUN':
                    continue
                if feats == '_':
                    continue

                feat_dict = {}
                for feat in feats.split('|'):
                    if '=' in feat:
                        k, v = feat.split('=', 1)
                        feat_dict[k] = v

                number_value = feat_dict.get('Number', None)
                if number_value == 'Sing':
                    lemma_counts[lemma]['sing'] += 1
                elif number_value == 'Plur':
                    lemma_counts[lemma]['plur'] += 1
                elif number_value == 'Ptan':
                    lemma_counts[lemma]['ptan'] += 1
                elif number_value == 'Dual':
                    lemma_counts[lemma]['dual'] += 1

    except FileNotFoundError:
        print(f"File not found: {conllu_file}", file=sys.stderr)
        return None

    return [
        {'lemma': lemma, 'sing': c['sing'], 'plur': c['plur'],
         'ptan': c['ptan'], 'dual': c['dual']}
        for lemma, c in lemma_counts.items()
    ]


def analyze_distribution(conllu_file, language, min_freq=0):
    """
    Analyze lemma distribution by plural ratio from a CoNLL-U file.

    Args:
        conllu_file: Path to CoNLL-U file
        language: Language name (Czech, English, Greek)
        min_freq: Minimum frequency threshold

    Returns:
        dict: Statistics for each ratio category
    """

    data = extract_lemma_stats_from_conllu(conllu_file, language)
    if data is None:
        return None

    analyzed = []

    for item in data:
        sing = item.get('sing', 0)
        plur = item.get('plur', 0)

        if language == 'Greek':
            total = sing + plur
            ratio = plur / total if total > 0 else None
        elif language == 'Czech':
            dual  = item.get('dual', 0)
            total = sing + plur + dual
            ratio = (plur + dual) / total if total > 0 else None
        elif language == 'English':
            ptan  = item.get('ptan', 0)
            total = sing + plur + ptan
            ratio = (plur + ptan) / total if total > 0 else None
        else:
            continue

        if total == 0 or ratio is None or total < min_freq:
            continue

        analyzed.append(ratio)

    total_lemmas = len(analyzed)
    eq_0         = len([r for r in analyzed if r == 0.0])
    gt_0_le_01   = len([r for r in analyzed if 0.0 < r <= 0.1])
    gt_01_lt_09  = len([r for r in analyzed if 0.1 < r < 0.9])
    ge_09_lt_1   = len([r for r in analyzed if 0.9 <= r < 1.0])
    eq_1         = len([r for r in analyzed if r == 1.0])

    return {
        'total':       total_lemmas,
        'eq_0':        eq_0,
        'gt_0_le_01':  gt_0_le_01,
        'gt_01_lt_09': gt_01_lt_09,
        'ge_09_lt_1':  ge_09_lt_1,
        'eq_1':        eq_1
    }


def generate_latex_table(results):
    """Generate LaTeX table matching the paper format exactly."""

    L = []

    # --- Table header ---
    L.append(r'\begin{table*}[ht]%[!htbp]')
    L.append(r'\centering')
    L.append(r'\setlength{\tabcolsep}{2pt}')
    L.append(r'%\small')
    L.append(r'\begin{tabular}{r@{\hskip 1.5pt}rrrrr@{\hskip 1pt}|@{\hskip 1.5pt}r@{\hskip 1.5pt}rrrrrr}')
    L.append(r'\toprule')
    L.append(r' \multicolumn{6}{c}{\textbf{All noun lemmas}} & \multicolumn{6}{c}{\textbf{Noun lemmas with $\geq$10 forms}} \\')
    L.append(r'\cmidrule(lr){1-6} \cmidrule(lr){7-12}')
    L.append(r'\multicolumn{1}{l}{\textbf{Total}} & \multicolumn{2}{l}{\textbf{Plural ratio}}  & & &  & \multicolumn{1}{l}{\textbf{Total}} & \multicolumn{2}{l}{\textbf{Plural ratio}} & &  &  \\')
    L.append(r'\multicolumn{1}{l}{\textbf{nouns}} & \multicolumn{1}{c}{\textbf{= 0}} & \textbf{(0,0.1]} & \textbf{(0.1,0.9)} & \textbf{[0.9,1)} & \multicolumn{1}{c}{\textbf{1}} & \multicolumn{1}{l}{\textbf{nouns}} & \multicolumn{1}{c}{\textbf{= 0}} & \textbf{(0,0.1]} & \textbf{(0.1,0.9)} & \textbf{[0.9,1)} & \multicolumn{1}{c}{\textbf{1}} \\')
    L.append(r'\midrule')

    # --- Data rows: English -> Czech -> Greek ---
    for language in ['English', 'Czech', 'Greek']:
        for tool in ['Stanza', 'UDPipe']:
            key = f"{language}_{tool}"
            if key not in results:
                continue

            a  = results[key]['all']
            m  = results[key]['min10']

            def p(d, f):
                return d[f] / d['total'] * 100 if d['total'] > 0 else 0

            ap = [p(a, 'eq_0'), p(a, 'gt_0_le_01'), p(a, 'gt_01_lt_09'), p(a, 'ge_09_lt_1'), p(a, 'eq_1')]
            mp = [p(m, 'eq_0'), p(m, 'gt_0_le_01'), p(m, 'gt_01_lt_09'), p(m, 'ge_09_lt_1'), p(m, 'eq_1')]

            L.append(f"\\multicolumn{{2}}{{l}}{{\\textbf{{{language} {tool}}}}}  &&&&\\multicolumn{{1}}{{c}}{{}} &&&&&&\\\\")

            L.append(
                f"{a['total']:>7,} & {a['eq_0']:>7,} & {a['gt_0_le_01']:>5,} & {a['gt_01_lt_09']:>6,} & {a['ge_09_lt_1']:>5,} & {a['eq_1']:>6,} & "
                f"{m['total']:>6,} & {m['eq_0']:>5,} & {m['gt_0_le_01']:>5,} & {m['gt_01_lt_09']:>6,} & {m['ge_09_lt_1']:>5,} & {m['eq_1']:>5,} \\\\"
            )

            L.append(
                f"& ({ap[0]:>4.1f}\\%) & ({ap[1]:>3.1f}\\%) & ({ap[2]:>4.1f}\\%) & ({ap[3]:>3.1f}\\%) & ({ap[4]:>4.1f}\\%) & "
                f"       & ({mp[0]:>4.1f}\\%) & ({mp[1]:>4.1f}\\%) & ({mp[2]:>4.1f}\\%) & ({mp[3]:>3.1f}\\%) & ({mp[4]:>3.1f}\\%) \\\\"
            )

            if tool == 'UDPipe' and language != 'Greek':
                L.append(r'\midrule')

    # --- Footer with full caption ---
    L.append(r'\bottomrule')
    L.append(r'\end{tabular}')
    L.append(
        r'\caption{Lemma-level distribution of \texttt{Number} values for all nouns (left) vs. nouns with $\geq$10 forms (right).' + '\n'
        r'Lemma counts by plural ratio: ' + '\n'
        r'0 (only singular); ' + '\n'
        r'(0,0.1] (mostly singular); ' + '\n'
        r'(0.1,0.9) (both singular and plural); ' + '\n'
        r'[0.9,1) (mostly plural); ' + '\n'
        r'1 (only plural). ' + '\n'
        r'%For Czech, Dual counted as plural; for English, Ptan counted as plural. ' + '\n'
        r'Percentages sum to 100\% per total count of lemmas.}'
    )
    L.append(r'\label{tab:lemma-number-distribution}')
    L.append(r'\end{table*}')

    return "\n".join(L)


def main():
    parser = argparse.ArgumentParser(
        description='Calculate lemma plural ratio distributions from CoNLL-U files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--czech-stanza',   required=True, help='Czech Stanza CoNLL-U file')
    parser.add_argument('--czech-udpipe',   required=True, help='Czech UDPipe CoNLL-U file')
    parser.add_argument('--english-stanza', required=True, help='English Stanza CoNLL-U file')
    parser.add_argument('--english-udpipe', required=True, help='English UDPipe CoNLL-U file')
    parser.add_argument('--greek-stanza',   required=True, help='Greek Stanza CoNLL-U file')
    parser.add_argument('--greek-udpipe',   required=True, help='Greek UDPipe CoNLL-U file')
    parser.add_argument('--output',         required=True, help='Output LaTeX file path')

    args = parser.parse_args()

    configs = {
        'English': {
            'Stanza': (args.english_stanza, 'English'),
            'UDPipe': (args.english_udpipe, 'English')
        },
        'Czech': {
            'Stanza': (args.czech_stanza, 'Czech'),
            'UDPipe': (args.czech_udpipe, 'Czech')
        },
        'Greek': {
            'Stanza': (args.greek_stanza, 'Greek'),
            'UDPipe': (args.greek_udpipe, 'Greek')
        }
    }

    results = {}
    print("Calculating lemma distributions...")

    for language, tools in configs.items():
        for tool_name, (conllu_file, lang_key) in tools.items():
            print(f"  Processing {language} {tool_name}...")
            all_stats   = analyze_distribution(conllu_file, lang_key, min_freq=0)
            min10_stats = analyze_distribution(conllu_file, lang_key, min_freq=10)
            if all_stats and min10_stats:
                results[f'{language}_{tool_name}'] = {
                    'all':   all_stats,
                    'min10': min10_stats
                }

    latex_table = generate_latex_table(results)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(latex_table)

    print(f"\nLaTeX table saved to: {args.output}")


if __name__ == '__main__':
    main()
