#!/usr/bin/env python3
"""
LLM API Test Suite
Run with: python tests.py
"""

import os
import sys
import json
import requests
from typing import Dict, Any, List, Tuple

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


class TestRunner:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_key = None
        self.model_name = None
        self.headers = None
        self.test_results: List[Tuple[str, bool, str]] = []
    
    def setup(self):
        """Prompt for API key and model name"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}=== LLM API Test Suite ==={Colors.END}\n")
        
        # Get API key
        self.api_key = input(f"{Colors.YELLOW}Enter your API key: {Colors.END}").strip()
        if not self.api_key:
            print(f"{Colors.RED}Error: API key is required{Colors.END}")
            sys.exit(1)
        
        # Get model name
        self.model_name = input(f"{Colors.YELLOW}Enter model name: {Colors.END}").strip()
        if not self.model_name:
            print(f"{Colors.RED}Error: Model name is required{Colors.END}")
            sys.exit(1)
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        print(f"\n{Colors.GREEN}Configuration:{Colors.END}")
        print(f"  Base URL: {self.base_url}")
        print(f"  API Key: {self.api_key[:20]}...")
        print(f"  Model: {self.model_name}\n")
    
    def run_test(self, name: str, test_func) -> bool:
        """Run a single test and record results"""
        try:
            print(f"{Colors.BLUE}Running: {name}...{Colors.END}", end=" ")
            result = test_func()
            if result:
                print(f"{Colors.GREEN}✓ PASSED{Colors.END}")
                self.test_results.append((name, True, ""))
                return True
            else:
                print(f"{Colors.RED}✗ FAILED{Colors.END}")
                self.test_results.append((name, False, "Test returned False"))
                return False
        except AssertionError as e:
            print(f"{Colors.RED}✗ FAILED{Colors.END}")
            error_msg = str(e)
            self.test_results.append((name, False, error_msg))
            return False
        except Exception as e:
            print(f"{Colors.RED}✗ ERROR{Colors.END}")
            error_msg = str(e)
            self.test_results.append((name, False, error_msg))
            return False
    
    def test_list_models(self) -> bool:
        """Test listing available models"""
        response = requests.get(f"{self.base_url}/v1/models", headers=self.headers, timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'object' in data and data['object'] == 'list'
        assert 'data' in data and isinstance(data['data'], list)
        print(f"({len(data['data'])} models found)", end=" ")
        return True
    
    def test_chat_completion_non_streaming(self) -> bool:
        """Test non-streaming chat completion"""
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": "Say hello in one word."}],
            "stream": False,
            "max_tokens": 10
        }
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        if response.status_code != 200:
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error'].get('message', str(error_data))
                else:
                    error_msg = str(error_data)
            except:
                error_msg = response.text[:200]
            raise AssertionError(f"Expected 200, got {response.status_code}: {error_msg}")
        data = response.json()
        assert 'choices' in data and len(data['choices']) > 0
        assert 'message' in data['choices'][0] and 'content' in data['choices'][0]['message']
        content = data['choices'][0]['message']['content']
        print(f"(response: {content[:30]}...)", end=" ")
        return True
    
    def test_chat_completion_streaming(self) -> bool:
        """Test streaming chat completion"""
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": "Count from 1 to 3."}],
            "stream": True,
            "max_tokens": 50
        }
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json=payload,
            stream=True,
            timeout=60
        )
        if response.status_code != 200:
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error'].get('message', str(error_data))
                else:
                    error_msg = str(error_data)
            except:
                error_msg = response.text[:200]
            raise AssertionError(f"Expected 200, got {response.status_code}: {error_msg}")
        assert response.headers.get('content-type') == 'text/event-stream'
        
        chunks = []
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        chunk_data = json.loads(data_str)
                        chunks.append(chunk_data)
                    except json.JSONDecodeError:
                        pass
        
        assert len(chunks) > 0, "No chunks received"
        print(f"({len(chunks)} chunks)", end=" ")
        return True
    
    def test_system_prompt(self) -> bool:
        """Test chat completion with system prompt"""
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2?"}
            ],
            "stream": False,
            "max_tokens": 50
        }
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        if response.status_code != 200:
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error'].get('message', str(error_data))
            except:
                error_msg = response.text[:200]
            raise AssertionError(f"Expected 200, got {response.status_code}: {error_msg}")
        data = response.json()
        assert len(data['choices'][0]['message']['content']) > 0
        return True
    
    def test_multi_turn(self) -> bool:
        """Test multi-turn conversation"""
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": "My name is Alice."},
                {"role": "assistant", "content": "Hello Alice!"},
                {"role": "user", "content": "What is my name?"}
            ],
            "stream": False,
            "max_tokens": 50
        }
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        if response.status_code != 200:
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error'].get('message', str(error_data))
            except:
                error_msg = response.text[:200]
            raise AssertionError(f"Expected 200, got {response.status_code}: {error_msg}")
        data = response.json()
        response_text = data['choices'][0]['message']['content'].lower()
        assert 'alice' in response_text, f"Expected 'alice' in response"
        return True
    
    def test_custom_parameters(self) -> bool:
        """Test custom temperature and top_p"""
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": "Say something."}],
            "stream": False,
            "temperature": 0.9,
            "top_p": 0.95,
            "max_tokens": 30
        }
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        if response.status_code != 200:
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error'].get('message', str(error_data))
            except:
                error_msg = response.text[:200]
            raise AssertionError(f"Expected 200, got {response.status_code}: {error_msg}")
        return True
    
    def test_missing_api_key(self) -> bool:
        """Test error handling for missing API key"""
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers={'Content-Type': 'application/json'},
            json={"model": self.model_name, "messages": [{"role": "user", "content": "Hello"}]},
            timeout=10
        )
        assert response.status_code == 401
        data = response.json()
        assert 'error' in data and data['error']['type'] == 'authentication_error'
        return True
    
    def test_invalid_model(self) -> bool:
        """Test error handling for invalid model"""
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json={
                "model": "non-existent-model-12345",
                "messages": [{"role": "user", "content": "Hello"}]
            },
            timeout=10
        )
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
        return True
    
    def test_rate_limiting(self) -> bool:
        """Test rate limiting by sending rapid requests"""
        print(f"\n  {Colors.YELLOW}Sending 5 rapid requests...{Colors.END}")
        success_count = 0
        rate_limited_count = 0
        
        for i in range(1, 6):
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": f"Request {i}"}],
                "stream": False,
                "max_tokens": 5
            }
            try:
                response = requests.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=10
                )
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    rate_limited_count += 1
            except:
                pass
        
        print(f"  Success: {success_count}/5, Rate Limited: {rate_limited_count}/5", end=" ")
        # Test passes if at least some requests succeeded
        return success_count > 0
    
    def run_all_tests(self):
        """Run all tests"""
        print(f"\n{Colors.BOLD}Running tests...{Colors.END}\n")
        
        tests = [
            ("List Models", self.test_list_models),
            ("Chat Completion (Non-Streaming)", self.test_chat_completion_non_streaming),
            ("Chat Completion (Streaming)", self.test_chat_completion_streaming),
            ("System Prompt", self.test_system_prompt),
            ("Multi-Turn Conversation", self.test_multi_turn),
            ("Custom Parameters", self.test_custom_parameters),
            ("Missing API Key Error", self.test_missing_api_key),
            ("Invalid Model Error", self.test_invalid_model),
            ("Rate Limiting", self.test_rate_limiting),
        ]
        
        for name, test_func in tests:
            self.run_test(name, test_func)
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{Colors.BOLD}{'='*50}{Colors.END}")
        print(f"{Colors.BOLD}Test Summary{Colors.END}")
        print(f"{'='*50}\n")
        
        passed = sum(1 for _, result, _ in self.test_results if result)
        failed = len(self.test_results) - passed
        total = len(self.test_results)
        
        for name, result, error in self.test_results:
            status = f"{Colors.GREEN}✓ PASSED{Colors.END}" if result else f"{Colors.RED}✗ FAILED{Colors.END}"
            print(f"  {status} - {name}")
            if not result and error:
                print(f"      {Colors.RED}Error: {error}{Colors.END}")
        
        print(f"\n{Colors.BOLD}Total: {total} | {Colors.GREEN}Passed: {passed}{Colors.END} | {Colors.RED}Failed: {failed}{Colors.END}\n")
        
        if failed == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}All tests passed! ✓{Colors.END}\n")
            return 0
        else:
            print(f"{Colors.RED}{Colors.BOLD}Some tests failed. ✗{Colors.END}\n")
            return 1


def main():
    """Main entry point"""
    # Check if server is reachable
    base_url = os.environ.get('LLM_BASE_URL', 'http://localhost:8000')
    
    try:
        response = requests.get(f"{base_url}/admin/", timeout=5)
    except requests.exceptions.RequestException:
        print(f"{Colors.RED}Error: Cannot connect to {base_url}")
        print(f"Make sure the Django server is running: python manage.py runserver{Colors.END}")
        sys.exit(1)
    
    runner = TestRunner(base_url)
    runner.setup()
    runner.run_all_tests()
    exit_code = runner.print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

