def test_gemini_client_has_60s_timeout():
    from truth_mirror.llm_client import LLMClient
    from unittest.mock import patch
    
    with patch('truth_mirror.key_rotator.get_current_key', return_value='test_key'), \
         patch('truth_mirror.llm_client.google_genai.Client') as mock_client:
        client = LLMClient()
        # Verify the underlying google.genai.Client was initialized with http_options={'timeout': 60000}
        mock_client.assert_called_once_with(api_key='test_key', http_options={'timeout': 60000})

def test_fallback_chain_default_openrouter_model():
    from truth_mirror.llm_fallback import LLMFallbackChain
    from unittest.mock import patch
    import os
    
    chain = LLMFallbackChain(sequence=["openrouter"], models={}, tracker_module="test")
    
    with patch('truth_mirror.llm_fallback.requests.post') as mock_post, \
         patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"}):
        
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "{}"}}]
        }
        
        chain.execute("test prompt")
        
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs['json']
        
        expected_models = [
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "google/gemma-4-26b-a4b-it:free",
            "nvidia/nemotron-3.5-lightning:free"
        ]
        assert payload['models'] == expected_models
        assert "response_format" not in payload
        assert "Return ONLY a valid JSON object" in payload['messages'][0]['content']

def test_groq_fallback_no_json_mode_and_prompt_appended():
    from truth_mirror.llm_fallback import LLMFallbackChain
    from unittest.mock import patch
    
    chain = LLMFallbackChain(sequence=["groq"], models={"groq": "test-model"}, tracker_module="test")
    
    with patch('truth_mirror.llm_fallback.call_groq_with_key_rotation') as mock_call:
        mock_call.return_value = ("{}", "success")
        
        chain.execute("test prompt")
        
        mock_call.assert_called_once()
        payload = mock_call.call_args.kwargs['payload']
        
        # response_format should NOT be present
        assert "response_format" not in payload, "response_format should not be in payload for Groq models"
        
        # prompt should have explicit JSON instructions appended
        messages = payload["messages"]
        assert len(messages) == 1
        assert "Return ONLY a valid JSON object" in messages[0]["content"]
