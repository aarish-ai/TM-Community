import os
import glob

def test_no_hardcoded_openrouter_models():
    # We want to ensure no files contain the old qwen string or hardcode the new nemotron string directly in logic
    # They should all reference the config variable instead.
    search_dir = os.path.join(os.path.dirname(__file__), '..', 'truth_mirror')
    
    python_files = glob.glob(os.path.join(search_dir, '**', '*.py'), recursive=True)
    bad_strings = [
        '"qwen/qwen3-next-80b-a3b-instruct:free"',
        '"nvidia/nemotron-3-nano-30b-a3b:free"',
        "'qwen/qwen3-next-80b-a3b-instruct:free'",
        "'nvidia/nemotron-3-nano-30b-a3b:free'"
    ]
    
    for filepath in python_files:
        if 'model_config.py' in filepath:
            continue
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                for bad in bad_strings:
                    assert bad not in content, f"Hardcoded model string {bad} found in {filepath}"
