#!/usr/bin/env python3
"""
Generate Singularia/Pluralia Tantum Candidate Distribution Plots

Creates visualization plots showing the distribution of lemmas by plural ratio,
with singularia tantum and pluralia tantum candidates highlighted.
Reads data directly from CoNLL-U files.

Please udpate file paths and names
Usage:
    python generate_candidate_plots.py \
        --candidates path/to/candidate_lists.json \
        --czech-stanza path/to/czech_stanza.conllu \
        --czech-udpipe path/to/czech_udpipe.conllu \
        --english-stanza path/to/english_stanza.conllu \
        --english-udpipe path/to/english_udpipe.conllu \
        --greek-stanza path/to/greek_stanza.conllu \
        --greek-udpipe path/to/greek_udpipe.conllu \
        --output-dir plots/

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
    - 6 PNG files (3 languages × 2 tools)
    - High-resolution plots with highlighted candidates
"""

import argparse
import json
import sys
import os
from collections import defaultdict

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("ERROR: matplotlib and numpy are required. Install with: pip install matplotlib numpy", file=sys.stderr)
    sys.exit(1)


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
            'sing': sing,
            'plur': plur,
            'ptan': ptan,
            'dual': dual,
            'total': total,
            'ratio': ratio
        }
    
    return lemma_dict


def find_candidates(lemma_dict, sing_list, plur_list, min_freq=10):
    """Find candidates with their ratios."""
    
    # Get all ratios for background histogram
    ratios = [item['ratio'] for item in lemma_dict.values() if item['total'] >= min_freq]
    
    # Find matching candidates
    sing_found = []
    plur_found = []
    
    for c in sing_list:
        if c in lemma_dict and lemma_dict[c]['total'] >= min_freq:
            sing_found.append({'candidate': c, **lemma_dict[c]})
    
    for c in plur_list:
        if c in lemma_dict and lemma_dict[c]['total'] >= min_freq:
            plur_found.append({'candidate': c, **lemma_dict[c]})
    
    return ratios, sing_found, plur_found


def create_plot(conllu_file, language, tool_name, sing_list, plur_list, output_dir, min_freq=10):
    """Create visualization plot."""
    
    # Set random seed for reproducibility
    np.random.seed(hash(f"{language}_{tool_name}") % (2**32))
    
    print(f"  Creating {language} - {tool_name}...")
    
    # Extract lemma stats from CoNLL-U
    lemma_dict = extract_lemma_stats_from_conllu(conllu_file, language)
    if lemma_dict is None:
        return False
    
    # Find candidates
    ratios, s_found, p_found = find_candidates(lemma_dict, sing_list, plur_list, min_freq)
    
    print(f"    Singularia: {len(s_found)}/{len(sing_list)}")
    print(f"    Pluralia: {len(p_found)}/{len(plur_list)}")
    
    # Create plot
    fig, ax = plt.subplots(1, 1, figsize=(7.5, 6.5))
    
    # Histogram
    bins = np.linspace(0, 1, 51)
    counts, bin_edges, patches = ax.hist(ratios, bins=bins, 
                                          edgecolor='white', color='lightgray', 
                                          linewidth=0.5, alpha=0.7)
    
    def get_y_position_in_bin(ratio_value):
        """Place dot within histogram bar in LOG space."""
        bin_idx = np.digitize(ratio_value, bin_edges) - 1
        bin_idx = max(0, min(bin_idx, len(counts) - 1))
        bin_height = counts[bin_idx]
        
        if bin_height < 2:
            return 1
        
        log_min = 0
        log_max = np.log10(bin_height)
        return 10 ** np.random.uniform(log_min, log_max)
    
    # Singularia dots
    if s_found:
        random_sizes_sing = np.random.uniform(30, 80, len(s_found))
        
        ax.scatter(
            [d['ratio'] for d in s_found],
            [get_y_position_in_bin(d['ratio']) for d in s_found],
            s=random_sizes_sing,  # Random sizes - dot size does not encode information
            c='crimson', alpha=0.7, edgecolors='darkred',
            linewidth=0.5, marker='o',
            label=f'Singularia tantum (n={len(s_found)})',
            zorder=5
        )
    
    # Pluralia dots
    if p_found:
        random_sizes_plur = np.random.uniform(30, 80, len(p_found))
        
        ax.scatter(
            [d['ratio'] for d in p_found],
            [get_y_position_in_bin(d['ratio']) for d in p_found],
            s=random_sizes_plur,
            c='dodgerblue', alpha=0.7, edgecolors='darkblue',
            linewidth=0.5, marker='o',
            label=f'Pluralia tantum (n={len(p_found)})',
            zorder=5
        )
    
    # Format with larger fonts
    ax.set_yscale('log')
    ax.set_xlabel('Ratio of Plural Forms', fontsize=14, fontweight='bold')
    ax.set_ylabel('Number of Distinct Lemmas (log scale)', fontsize=14, fontweight='bold')
    ax.set_title(f'{language} - {tool_name}\n'
                 f'Lemmas with ≥{min_freq} occurrences (n={len(ratios):,} distinct lemmas)',
                 fontsize=15, fontweight='bold')
    ax.grid(True, alpha=0.3, which='both')
    ax.set_xlim(-0.02, 1.02)
    
    ax.tick_params(axis='both', which='major', labelsize=12)
    ax.legend(loc='upper center', fontsize=12, framealpha=0.95, 
              edgecolor='black', fancybox=False)
    
    plt.tight_layout()
    
    # Save
    out = os.path.join(output_dir, f'{language.lower()}_{tool_name.lower()}_sp_tantum.png')
    plt.savefig(out, dpi=300, bbox_inches='tight')
    print(f"Saved: {out}")
    plt.close()
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Generate singularia/pluralia tantum distribution plots',
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
    parser.add_argument('--output-dir', required=True, help='Output directory for plots')
    parser.add_argument('--min-freq', type=int, default=10, help='Minimum frequency threshold (default: 10)')
    
    args = parser.parse_args()
    
    # Load candidate lists
    candidates = load_candidate_lists(args.candidates)
    if candidates is None:
        sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate plots
    print("\nGenerating plots...")
    
    configs = [
        ('Czech', 'Stanza', args.czech_stanza, candidates.get('czech', {})),
        ('Czech', 'UDPipe', args.czech_udpipe, candidates.get('czech', {})),
        ('English', 'Stanza', args.english_stanza, candidates.get('english', {})),
        ('English', 'UDPipe', args.english_udpipe, candidates.get('english', {})),
        ('Greek', 'Stanza', args.greek_stanza, candidates.get('greek', {})),
        ('Greek', 'UDPipe', args.greek_udpipe, candidates.get('greek', {})),
    ]
    
    success_count = 0
    for language, tool, conllu_file, cand_dict in configs:
        sing_list = cand_dict.get('singularia', [])
        plur_list = cand_dict.get('pluralia', [])
        
        if create_plot(conllu_file, language, tool, sing_list, plur_list, args.output_dir, args.min_freq):
            success_count += 1
    
    print(f"\n generated {success_count}/6 plots in {args.output_dir}")


if __name__ == '__main__':
    main()
