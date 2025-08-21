import pandas as pd
import spacy
from multiprocessing import cpu_count
from pandarallel import pandarallel
from collections import Counter


# 🌟 Module-level setup (runs once on import)

# Load the pre-trained spaCy model
print("Loading SpaCy model: en_core_web_trf - English transformer pipeline (roberta-base)...")
nlp = spacy.load("en_core_web_trf", disable=['tagger', 'parser', 'lemmatizer'])

# Check if the model is on the GPU
print(nlp.meta['name'])  # This will print the model name
print("Using GPU: ", spacy.prefer_gpu())

pandarallel.initialize(progress_bar=True, nb_workers=cpu_count()-1)


def clean_text(markdown_content: str) -> str:
    """Removes punctuation, numbers, non-ASCII symbols, and stopwords using spaCy."""
    doc = nlp(markdown_content)

    cleaned_tokens = [
        token.text  # Use lemma instead of raw token (better for NLP tasks)
        for token in doc
        if not token.is_punct  # Remove punctuation
        and not token.is_stop  # Remove stopwords
        and not token.is_digit  # Remove numbers
        and token.is_ascii  # Keep only ASCII characters
    ]
    
    return " ".join(cleaned_tokens)


def extract_entities_labels_tuple(cleaned_text: str) -> (list, list):
    """Extracts named entities and returns a tuple of (entity_texts, entity_labels)."""
    doc = nlp(cleaned_text)
    
    entity_texts = [ent.text for ent in doc.ents]
    entity_labels = [ent.label_ for ent in doc.ents]
    
    return entity_texts, entity_labels  # Return tuple of lists


def build_entities_label_count_df(named_entities: list, labels: list, label_filter: str | tuple = None) -> pd.DataFrame:
    # Create a Counter for the occurrences of items in the master named_entities list
    ne_count = Counter(named_entities)

    # Precompute a dictionary for faster lookup
    entity_to_label = dict(zip(named_entities, labels))
    
    if label_filter == None:
        # Create the list using dictionary lookup (O(1) per item)
        unique_items = [(item, entity_to_label.get(item, None), ne_count[item]) for item in ne_count]
    elif isinstance(label_filter, str):
        # Create the list using dictionary lookup (O(1) per item), keeping only `label_filter` label
        unique_items = [
            (item, entity_to_label.get(item, None), ne_count[item])
            for item in ne_count
            if entity_to_label.get(item, None) == label_filter
        ]
    elif isinstance(label_filter, list | tuple):
        # Create the list using dictionary lookup (O(1) per item), keeping only items in `label_filter` labels
        unique_items = [
            (item, entity_to_label.get(item, None), ne_count[item])
            for item in ne_count
            if entity_to_label.get(item, None) in label_filter
        ]
        

    entities_df = pd.DataFrame(unique_items)
    entities_df.columns = ["Entities", "Labels", "Count"]
    entities_df.sort_values(by="Count", ascending=False, axis=0, inplace=True)
    
    return entities_df


def extract_entities_label_count_df(
    markdown_content: str, 
    label_filter: str | tuple | None = None
) -> pd.DataFrame:
    """
    Extract named entities and their labels from markdown content, returning a count DataFrame.
    
    Parameters:
    - markdown_content: The markdown text to process.
    - label_filter: Optional label or tuple of labels to filter entities by.
    
    Returns:
    - DataFrame with counts of named entities (filtered if label_filter provided).
    """
    list_of_named_entities, list_of_labels = extract_entities_labels_tuple(clean_text(markdown_content))
    
    return build_entities_label_count_df(list_of_named_entities, list_of_labels, label_filter)


def filter_entities_label_count_by_label(markdown_content: str, label_filter: str | tuple) -> list:
    entities_label_count_df = extract_entities_label_count_df(markdown_content)
    
    if isinstance(label_filter, str):
        return list(entities_label_count_df[entities_label_count_df['Labels'] == label_filter]['Entities'])
    elif isinstance(label_filter, tuple):
        return list(entities_label_count_df[entities_label_count_df['Labels'].isin(label_filter)]['Entities'])
    

def extract_customer_dba_name_spacy(markdown_content: str) -> list:
    return filter_entities_label_count_by_label(markdown_content, 'ORG')