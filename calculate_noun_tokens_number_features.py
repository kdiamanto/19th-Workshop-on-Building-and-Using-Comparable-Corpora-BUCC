#!/usr/bin/env python3
"""
Noun Token Analysis and Number Feature Distribution

Analyzes CoNLL-U files to count noun tokens and their Number feature distribution
across different annotation tools (Stanza, UDPipe) and languages (Czech, English, Greek).

#please update paths and file names
Usage:
    python analyze_noun_tokens_and_features.py \
        --czech-stanza path/to/czech_corpus_stanza.conllu \
        --czech-udpipe path/to/czech_corpus_udpipe.conllu \
        --english-stanza path/to/english_corpus_stanza.conllu \
        --english-udpipe path/to/english_corpus_udpipe.conllu \
        --greek-stanza path/to/greek_corpus_stanza.conllu \
        --greek-udpipe path/to/greek_corpus_udpipe.conllu \
        --output results/noun_token_analysis.txt

Output:
    - Total noun token counts per language/tool
    - Number feature distribution (Sing, Plur, Ptan, Dual, Missing)
    - Percentages and statistical summaries
"""

import argparse
import sys
from collections import defaultdict


def analyze_noun_tokens(conllu_file, language, tool_name):
    """
    Count noun tokens and analyze Number feature distribution.
    
    Args:
        conllu_file: Path to CoNLL-U file
        language: Language name (Czech, English, Greek)
        tool_name: Tool name (Stanza, UDPipe)
    
    Returns:
        dict: Statistics including total counts and Number distribution
    """
    
    number_counts = {
        'Sing': 0,
        'Plur': 0,
        'Ptan': 0,
        'Dual': 0,
        'Missing': 0
    }
    
    total_nouns = 0
    
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
                upos = parts[3]
                feats = parts[5]
                
                # Skip multiword tokens
                if '-' in token_id or '.' in token_id:
                    continue
                
                # Only NOUN
                if upos != 'NOUN':
                    continue
                
                total_nouns += 1
                
                # Extract Number feature
                if feats != '_':
                    feat_dict = {}
                    for feat in feats.split('|'):
                        if '=' in feat:
                            key, value = feat.split('=', 1)
                            feat_dict[key] = value
                    
                    number_value = feat_dict.get('Number', None)
                    
                    if number_value in ['Sing', 'Plur', 'Ptan', 'Dual']:
                        number_counts[number_value] += 1
                    else:
                        number_counts['Missing'] += 1
                else:
                    number_counts['Missing'] += 1
    
    except FileNotFoundError:
        print(f"ERROR: File not found: {conllu_file}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR processing {conllu_file}: {e}", file=sys.stderr)
        return None
    
    return {
        'language': language,
        'tool': tool_name,
        'total': total_nouns,
        'counts': number_counts
    }


def format_results(results_list):
    """Format analysis results as text report."""
    
    lines = []
    lines.append("="*80)
    lines.append("NOUN TOKEN ANALYSIS AND NUMBER FEATURE DISTRIBUTION")
    lines.append("="*80)
    lines.append("")
    
    for result in results_list:
        if result is None:
            continue
        
        lines.append(f"{result['language']} - {result['tool']}")
        lines.append("-"*80)
        lines.append(f"Total NOUN tokens: {result['total']:,}")
        lines.append("")
        lines.append("Number feature distribution:")
        
        for num_type in ['Sing', 'Plur', 'Ptan', 'Dual', 'Missing']:
            count = result['counts'][num_type]
            if count > 0:
                pct = count / result['total'] * 100 if result['total'] > 0 else 0
                lines.append(f"  {num_type:<10} {count:>12,}  ({pct:>5.2f}%)")
        
        lines.append("")
        lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze noun tokens and Number features in CoNLL-U files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--czech-stanza', required=True, help='Czech Stanza CoNLL-U file')
    parser.add_argument('--czech-udpipe', required=True, help='Czech UDPipe CoNLL-U file')
    parser.add_argument('--english-stanza', required=True, help='English Stanza CoNLL-U file')
    parser.add_argument('--english-udpipe', required=True, help='English UDPipe CoNLL-U file')
    parser.add_argument('--greek-stanza', required=True, help='Greek Stanza CoNLL-U file')
    parser.add_argument('--greek-udpipe', required=True, help='Greek UDPipe CoNLL-U file')
    parser.add_argument('--output', required=True, help='Output file path')
    
    args = parser.parse_args()
    
    # Analyze all files
    results = []
    
    configs = [
        (args.czech_stanza, 'Czech', 'Stanza'),
        (args.czech_udpipe, 'Czech', 'UDPipe'),
        (args.english_stanza, 'English', 'Stanza'),
        (args.english_udpipe, 'English', 'UDPipe'),
        (args.greek_stanza, 'Greek', 'Stanza'),
        (args.greek_udpipe, 'Greek', 'UDPipe'),
    ]
    
    print("Analyzing noun tokens and Number features...")
    for conllu_file, language, tool in configs:
        print(f"  Processing {language} {tool}...")
        result = analyze_noun_tokens(conllu_file, language, tool)
        results.append(result)
    
    # Generate report
    report = format_results(results)
    
    # Save to file
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n Results saved to: {args.output}")
    
    # Also print to console
    print("\n" + report)


if __name__ == '__main__':
    main()
