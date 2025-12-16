"""
Fuzzy Matcher Module

Implements fuzzy string matching to find similar model names.
Uses intelligent token-based matching with version number awareness.
"""

import os
import re
from typing import List, Dict, Tuple, Set
from difflib import SequenceMatcher


def normalize_filename(filename: str) -> str:
    """
    Normalize a filename for comparison.
    
    Removes file extension, converts to lowercase, and normalizes
    separators (underscores, hyphens, spaces).
    
    Args:
        filename: Filename to normalize
        
    Returns:
        Normalized string for comparison
    """
    # Remove file extension
    base = os.path.splitext(filename)[0]
    
    # Convert to lowercase
    base = base.lower()
    
    # Normalize separators: replace underscores, hyphens, and spaces with a single space
    base = re.sub(r'[_\-\s]+', ' ', base)
    
    # Strip whitespace
    base = base.strip()
    
    return base


def tokenize_model_name(filename: str) -> List[str]:
    """
    Tokenize a model filename into meaningful components.
    Normalizes version numbers and identifiers for better matching.
    
    Args:
        filename: Model filename to tokenize
        
    Returns:
        List of normalized tokens
    """
    # Remove extension
    base = os.path.splitext(filename)[0].lower()
    
    # Normalize all separators to single character for consistent splitting
    # Replace _, -, . with space
    normalized = re.sub(r'[_\-\.]+', ' ', base)
    
    # Split into tokens
    tokens = normalized.split()
    
    # Further process tokens to handle version numbers
    processed_tokens = []
    for token in tokens:
        # If token looks like a version (e.g., "2", "1", etc following model name)
        # Keep it as-is
        processed_tokens.append(token)
    
    return [t for t in processed_tokens if t]  # Remove empty strings


def calculate_token_similarity(tokens1: List[str], tokens2: List[str]) -> float:
    """
    Calculate similarity based on token overlap and order.
    Heavily weights exact token matches and version numbers.
    
    Args:
        tokens1: Tokens from target model
        tokens2: Tokens from candidate model
        
    Returns:
        Similarity score from 0.0 to 1.0
    """
    if not tokens1 or not tokens2:
        return 0.0
    
    # Convert to sets for intersection
    set1 = set(tokens1)
    set2 = set(tokens2)
    
    # Calculate Jaccard similarity (intersection over union)
    intersection = set1 & set2
    union = set1 | set2
    
    if not union:
        return 0.0
    
    jaccard = len(intersection) / len(union)
    
    # Bonus for preserving order of key tokens
    order_score = 0.0
    if len(tokens1) > 1 and len(tokens2) > 1:
        # Check if first few tokens match in order
        max_check = min(3, len(tokens1), len(tokens2))
        matching_order = sum(1 for i in range(max_check) if tokens1[i] == tokens2[i])
        order_score = matching_order / max_check * 0.2  # Up to 20% bonus
    
    # Combine scores
    return min(jaccard + order_score, 1.0)


def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity score between two strings (0.0 to 1.0).
    
    Uses SequenceMatcher to compute a ratio.
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        Similarity score from 0.0 (completely different) to 1.0 (identical)
    """
    return SequenceMatcher(None, str1, str2).ratio()


def calculate_similarity_with_normalization(str1: str, str2: str) -> float:
    """
    Calculate similarity score with intelligent token-based matching.
    
    Uses tokenization to preserve version numbers and important identifiers.
    
    Args:
        str1: First string (typically target model filename)
        str2: Second string (typically candidate model filename)
        
    Returns:
        Similarity score from 0.0 to 1.0
    """
    # First check exact match after simple normalization
    norm1 = normalize_filename(str1)
    norm2 = normalize_filename(str2)
    
    if norm1 == norm2:
        return 1.0
    
    # Tokenize both filenames
    tokens1 = tokenize_model_name(str1)
    tokens2 = tokenize_model_name(str2)
    
    # Calculate token-based similarity
    token_sim = calculate_token_similarity(tokens1, tokens2)
    
    # Also calculate character-based similarity as a backup
    char_sim = calculate_similarity(norm1, norm2)
    
    # Weight token similarity more heavily (70/30 split)
    # Token matching is better for semantic similarity
    final_sim = (token_sim * 0.7) + (char_sim * 0.3)
    
    return final_sim


def find_matches(
    target_model: str,
    candidate_models: List[Dict[str, str]],
    threshold: float = 0.0,
    max_results: int = 10
) -> List[Dict[str, any]]:
    """
    Find similar models using fuzzy matching.
    
    Args:
        target_model: The target model filename/path to match
        candidate_models: List of candidate model dictionaries with 'filename' or 'path' key
        threshold: Minimum similarity score (0.0 to 1.0) to include in results
        max_results: Maximum number of results to return
        
    Returns:
        List of match dictionaries sorted by similarity (highest first):
        {
            'model': original model dict from candidates,
            'filename': model filename,
            'similarity': similarity score (0.0 to 1.0),
            'confidence': confidence percentage (0 to 100)
        }
    """
    matches = []
    
    # Extract just the filename from target_model (remove any subfolder paths)
    # target_model might be just a filename or might include subfolder paths
    target_filename = os.path.basename(target_model)
    
    # Normalize target filename once for exact match comparisons
    target_norm = normalize_filename(target_filename)
    
    for candidate in candidate_models:
        # Get filename from candidate (prefer 'filename' key, fallback to extracting from 'path' or 'relative_path')
        candidate_filename = candidate.get('filename')
        
        # If no filename key, try to extract from path or relative_path
        if not candidate_filename:
            candidate_path = candidate.get('path', '') or candidate.get('relative_path', '')
            if candidate_path:
                candidate_filename = os.path.basename(candidate_path)
        
        if not candidate_filename:
            continue
        
        # Calculate similarity comparing just filenames (not paths)
        # This ensures we're comparing apples to apples
        
        # First check for exact match (after normalization) - should be 100%
        # Only exact matches should get 100% confidence
        candidate_norm = normalize_filename(candidate_filename)
        
        if target_norm == candidate_norm:
            # Exact match after normalization = 100% confidence
            similarity = 1.0
        else:
            # Calculate similarity using SequenceMatcher
            # This gives a ratio between 0.0 and 1.0 based on longest common subsequence
            similarity = calculate_similarity_with_normalization(target_filename, candidate_filename)
            
            # Also try comparing without extensions for better matching
            target_base = os.path.splitext(target_filename)[0]
            candidate_base = os.path.splitext(candidate_filename)[0]
            similarity_no_ext = calculate_similarity_with_normalization(target_base, candidate_base)
            
            # Use the higher of the two similarity scores
            # But ensure we never get 1.0 unless it's an exact normalized match
            similarity = max(similarity, similarity_no_ext)
            
            # Cap similarity at 0.999 for non-exact matches to prevent false 100% scores
            # SequenceMatcher can sometimes give 1.0 for very similar but not identical strings
            # due to normalization artifacts
            if similarity >= 0.999 and target_norm != candidate_norm:
                similarity = 0.999
        
        # Only include if above threshold
        if similarity >= threshold:
            matches.append({
                'model': candidate,
                'filename': candidate_filename,
                'similarity': similarity,
                'confidence': round(similarity * 100, 1)  # Convert to percentage
            })
    
    # Sort by similarity (highest first)
    matches.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Limit to max_results
    matches = matches[:max_results]
    
    return matches

