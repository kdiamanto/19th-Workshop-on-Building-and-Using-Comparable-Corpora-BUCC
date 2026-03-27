#!/usr/bin/env python3
"""
Calculate Validation Statistics for Singularia/Pluralia Tantum Candidates

Analyzes how many grammar-derived candidates are attested in the corpus and
how many are confirmed (have ratio=0.0 or ratio=1.0). Reads data directly
from CoNLL-U files and generates LaTeX validation tables.

#please update paths and file names
Usage:
    python calculate_validation_statistics.py \
        --candidates path/to/candidate_lists.json \
        --czech-stanza path/to/czech_stanza.conllu \
        --czech-udpipe path/to/czech_udpipe.conllu \
        --english-stanza path/to/english_stanza.conllu \
        --english-udpipe path/to/english_udpipe.conllu \
        --greek-stanza path/to/greek_stanza.conllu \
        --greek-udpipe path/to/greek_udpipe.conllu \
        --output results/validation_tables.tex

Candidate lists JSON format:
    {
      "czech": {
        "singularia": ["lemma1", "lemma2", ...],
        "pluralia": ["lemma1", "lemma2", ...]
      },
      "english": {...},
      "greek": {...}
    }

Output:
    - LaTeX table with Candidates / Attested / Confirmed statistics
    - Separate analysis for All and ≥10 thresholds
"""

import argparse
import json
import sys
from collections import defaultdict


def load_candidate_lists(json_file):
    """Load candidate lists from JSON file."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {json_file}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        return None


def extract_lemma_stats_from_conllu(conllu_file, language):
    """
    Extract lemma statistics directly from CoNLL-U file.
    
    Returns:
        dict: lemma -> {sing, plur, ptan, dual, total, ratio}
    """
    
    lemma_counts = defaultdict(lambda: {
        'sing': 0,
        'plur': 0,
        'ptan': 0,
        'dual': 0
    })
    
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
                lemma = parts[2]
                upos = parts[3]
                feats = parts[5]
                
                # Skip multiword tokens
                if '-' in token_id or '.' in token_id:
                    continue
                
                # Only NOUN
                if upos != 'NOUN':
                    continue
                
                # Extract Number feature
                if feats != '_':
                    feat_dict = {}
                    for feat in feats.split('|'):
                        if '=' in feat:
                            key, value = feat.split('=', 1)
                            feat_dict[key] = value
                    
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
        print(f"ERROR: File not found: {conllu_file}", file=sys.stderr)
        return None
    
    # Calculate totals and ratios
    lemma_dict = {}
    for lemma, counts in lemma_counts.items():
        sing = counts['sing']
        plur = counts['plur']
        ptan = counts['ptan']
        dual = counts['dual']
        
        if language == 'Greek':
            total = sing + plur
            ratio = plur / total if total > 0 else 0
        elif language == 'Czech':
            total = sing + plur + dual
            ratio = (plur + dual) / total if total > 0 else 0
        elif language == 'English':
            total = sing + plur + ptan
            ratio = (plur + ptan) / total if total > 0 else 0
        else:
            continue
        
        lemma_dict[lemma] = {
            'total': total,
            'ratio': ratio
        }
    
    return lemma_dict


def analyze_candidates(lemma_dict, candidate_list, target_ratio, min_freq=1):
    """
    Analyze candidate validation statistics.
    
    Args:
        lemma_dict: Dictionary of lemma statistics
        candidate_list: List of candidate lemmas
        target_ratio: 0.0 for singularia, 1.0 for pluralia
        min_freq: Minimum frequency threshold
    
    Returns:
        tuple: (total_candidates, attested, confirmed)
    """
    
    total_candidates = len(candidate_list)
    attested = 0
    confirmed = 0
    
    for lemma in candidate_list:
        if lemma in lemma_dict:
            total = lemma_dict[lemma]['total']
            ratio = lemma_dict[lemma]['ratio']
            
            if total >= min_freq:
                attested += 1
                if ratio == target_ratio:
                    confirmed += 1
    
    return total_candidates, attested, confirmed


def generate_latex_table(results):
    """Generate LaTeX validation table."""
    
    lines = []
    lines.append("\\begin{table*}[ht]")
    lines.append("\\centering")
    lines.append("\\begin{tabular}{llrrr|rrr|rrr}")
    lines.append("\\toprule")
    lines.append(" & & \\multicolumn{2}{c}{\\textbf{English}} & & \\multicolumn{2}{c}{\\textbf{Czech}} & & \\multicolumn{2}{c}{\\textbf{Greek}} \\\\")
    lines.append("\\cmidrule(lr){3-4} \\cmidrule(lr){5-6} \\cmidrule(lr){7-8}")
    lines.append("\\textbf{Tool} & \\textbf{Lemmas} & \\multicolumn{6}{c}{Candidates / Attested / Confirmed} \\\\")
    lines.append("\\midrule")
    
    # Stanza All
    en_s = results['English_Stanza']
    cz_s = results['Czech_Stanza']
    gr_s = results['Greek_Stanza']
    
    lines.append(f"Stanza   & All & "
                f"{en_s['sing_all'][0]} / {en_s['sing_all'][1]} / {en_s['sing_all'][2]:>3}   &   "
                f"{en_s['plur_all'][0]} / {en_s['plur_all'][1]} / {en_s['plur_all'][2]:>2} & "
                f"{cz_s['sing_all'][0]} / {cz_s['sing_all'][1]} / {cz_s['sing_all'][2]:>3}     &   "
                f"{cz_s['plur_all'][0]} / {cz_s['plur_all'][1]} / {cz_s['plur_all'][2]:>3} &"
                f"{gr_s['sing_all'][0]} / {gr_s['sing_all'][1]} / {gr_s['sing_all'][2]:>2}    &   "
                f"{gr_s['plur_all'][0]} / {gr_s['plur_all'][1]} / {gr_s['plur_all'][2]:>2} \\\\")
    
    # Stanza ≥10
    lines.append(f"         & $\\geq$10  & "
                f"{en_s['sing_min10'][0]} / {en_s['sing_min10'][1]} / {en_s['sing_min10'][2]:>3}   &   "
                f"{en_s['plur_min10'][0]} / {en_s['plur_min10'][1]} / {en_s['plur_min10'][2]:>3} & "
                f"{cz_s['sing_min10'][0]} / {cz_s['sing_min10'][1]} / {cz_s['sing_min10'][2]:>3}     &   "
                f"{cz_s['plur_min10'][0]} / {cz_s['plur_min10'][1]} / {cz_s['plur_min10'][2]:>3} &"
                f"{gr_s['sing_min10'][0]} / {gr_s['sing_min10'][1]} / {gr_s['sing_min10'][2]:>2}    &   "
                f"{gr_s['plur_min10'][0]} / {gr_s['plur_min10'][1]} / {gr_s['plur_min10'][2]:>2} \\\\")
    
    lines.append("\\midrule")
    
    # UDPipe All
    en_u = results['English_UDPipe']
    cz_u = results['Czech_UDPipe']
    gr_u = results['Greek_UDPipe']
    
    lines.append(f"UDPipe   & All  & "
                f"{en_u['sing_all'][0]} / {en_u['sing_all'][1]} / {en_u['sing_all'][2]:>3}   &   "
                f"{en_u['plur_all'][0]} / {en_u['plur_all'][1]} / {en_u['plur_all'][2]:>3} & "
                f"{cz_u['sing_all'][0]} / {cz_u['sing_all'][1]} / {cz_u['sing_all'][2]:>2}     &   "
                f"{cz_u['plur_all'][0]} / {cz_u['plur_all'][1]} / {cz_u['plur_all'][2]:>2} &"
                f"{gr_u['sing_all'][0]} / {gr_u['sing_all'][1]} / {gr_u['sing_all'][2]:>3}    &   "
                f"{gr_u['plur_all'][0]} / {gr_u['plur_all'][1]} / {gr_u['plur_all'][2]:>2} \\\\")
    
    # UDPipe ≥10
    lines.append(f"         & $\\geq$10  & "
                f"{en_u['sing_min10'][0]} / {en_u['sing_min10'][1]} / {en_u['sing_min10'][2]:>3}   &   "
                f"{en_u['plur_min10'][0]} / {en_u['plur_min10'][1]} / {en_u['plur_min10'][2]:>3} & "
                f"{cz_u['sing_min10'][0]} / {cz_u['sing_min10'][1]} / {cz_u['sing_min10'][2]:>2}     &   "
                f"{cz_u['plur_min10'][0]} / {cz_u['plur_min10'][1]} / {cz_u['plur_min10'][2]:>2} &"
                f"{gr_u['sing_min10'][0]} / {gr_u['sing_min10'][1]} / {gr_u['sing_min10'][2]:>3}    &   "
                f"{gr_u['plur_min10'][0]} / {gr_u['plur_min10'][1]} / {gr_u['plur_min10'][2]:>2} \\\\")
    
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\caption{Attestation of grammar-derived singularia tantum and pluralia tantum candidates in the datasets. ")
    lines.append("For each language, the table shows: total candidates / attested in corpus / confirmed with pure ratio (0.0 or 1.0). ")
    lines.append("Statistics shown for both full dataset (All) and lemmas with $\\geq$10 occurrences.}")
    lines.append("\\label{tab:validation-stats}")
    lines.append("\\end{table*}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Calculate validation statistics for singularia/pluralia tantum candidates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--candidates', required=True, help='Candidate lists JSON file')
    parser.add_argument('--czech-stanza', required=True, help='Czech Stanza CoNLL-U file')
    parser.add_argument('--czech-udpipe', required=True, help='Czech UDPipe CoNLL-U file')
    parser.add_argument('--english-stanza', required=True, help='English Stanza CoNLL-U file')
    parser.add_argument('--english-udpipe', required=True, help='English UDPipe CoNLL-U file')
    parser.add_argument('--greek-stanza', required=True, help='Greek Stanza CoNLL-U file')
    parser.add_argument('--greek-udpipe', required=True, help='Greek UDPipe CoNLL-U file')
    parser.add_argument('--output', required=True, help='Output LaTeX file path')
    
    args = parser.parse_args()
    
    # Load candidate lists
    candidates = load_candidate_lists(args.candidates)
    if candidates is None:
        sys.exit(1)
    
    print("Calculating validation statistics...")
    
    # Process all files
    results = {}
    
    configs = [
        ('English', 'Stanza', args.english_stanza),
        ('English', 'UDPipe', args.english_udpipe),
        ('Czech', 'Stanza', args.czech_stanza),
        ('Czech', 'UDPipe', args.czech_udpipe),
        ('Greek', 'Stanza', args.greek_stanza),
        ('Greek', 'UDPipe', args.greek_udpipe),
    ]
    
    for language, tool, conllu_file in configs:
        print(f"  Processing {language} {tool}...")
        
        # Extract lemma stats from CoNLL-U
        lemma_dict = extract_lemma_stats_from_conllu(conllu_file, language)
        if lemma_dict is None:
            sys.exit(1)
        
        # Get candidate lists for this language
        lang_key = language.lower()
        sing_list = candidates.get(lang_key, {}).get('singularia', [])
        plur_list = candidates.get(lang_key, {}).get('pluralia', [])
        
        # Analyze with both thresholds
        sing_all = analyze_candidates(lemma_dict, sing_list, 0.0, min_freq=1)
        sing_min10 = analyze_candidates(lemma_dict, sing_list, 0.0, min_freq=10)
        plur_all = analyze_candidates(lemma_dict, plur_list, 1.0, min_freq=1)
        plur_min10 = analyze_candidates(lemma_dict, plur_list, 1.0, min_freq=10)
        
        results[f'{language}_{tool}'] = {
            'sing_all': sing_all,
            'sing_min10': sing_min10,
            'plur_all': plur_all,
            'plur_min10': plur_min10
        }
        
        print(f"    Singularia: {sing_all[1]}/{sing_all[0]} attested (All), {sing_min10[1]}/{sing_min10[0]} (≥10)")
        print(f"    Pluralia: {plur_all[1]}/{plur_all[0]} attested (All), {plur_min10[1]}/{plur_min10[0]} (≥10)")
    
    # Generate LaTeX table
    latex_table = generate_latex_table(results)
    
    # Save to file
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(latex_table)
    
    print(f"\n LaTeX table saved to: {args.output}")


if __name__ == '__main__':
    main()
