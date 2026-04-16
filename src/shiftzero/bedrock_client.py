"""AWS Bedrock Claude client wrapper"""

import json
import boto3
from typing import List, Dict, Any
from .config import get_settings


class BedrockClaudeClient:
    """Client for interacting with Claude via AWS Bedrock"""

    def __init__(self):
        self.settings = get_settings()

        # Initialize Bedrock runtime client
        session_kwargs = {
            'region_name': self.settings.aws_region
        }

        if self.settings.aws_profile:
            session = boto3.Session(profile_name=self.settings.aws_profile)
            self.client = session.client('bedrock-runtime')
        else:
            if self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
                session_kwargs['aws_access_key_id'] = self.settings.aws_access_key_id
                session_kwargs['aws_secret_access_key'] = self.settings.aws_secret_access_key
                if self.settings.aws_session_token:
                    session_kwargs['aws_session_token'] = self.settings.aws_session_token

            self.client = boto3.client('bedrock-runtime', **session_kwargs)

        self.model_id = self.settings.bedrock_model_id

    def invoke(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        tools: List[Dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Invoke Claude via Bedrock Converse API

        Args:
            messages: Conversation history in Claude format
            system: System prompt
            tools: Tool definitions (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Response from Claude
        """
        request_params = {
            'modelId': self.model_id,
            'messages': messages,
            'system': [{'text': system}],
            'inferenceConfig': {
                'maxTokens': max_tokens,
                'temperature': temperature
            }
        }

        if tools:
            request_params['toolConfig'] = {'tools': tools}

        try:
            response = self.client.converse(**request_params)
            return response
        except Exception as e:
            raise RuntimeError(f"Bedrock invocation failed: {e}")

    def parse_response(self, response: Dict[str, Any]) -> tuple[str | None, List[Dict[str, Any]] | None]:
        """
        Parse Bedrock response into text and tool calls

        Returns:
            Tuple of (text_content, tool_calls)
        """
        output = response.get('output', {})
        message = output.get('message', {})
        content = message.get('content', [])
        stop_reason = response.get('stopReason')

        text_content = None
        tool_calls = []

        for block in content:
            if 'text' in block:
                text_content = block['text']
            elif 'toolUse' in block:
                tool_calls.append({
                    'id': block['toolUse']['toolUseId'],
                    'name': block['toolUse']['name'],
                    'input': block['toolUse']['input']
                })

        return text_content, tool_calls if tool_calls else None
