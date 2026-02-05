import pytest
from unittest.mock import AsyncMock, patch
from services.review_engine.service import PRAnalysisEngine
from services.integrations.github_publisher import publisher, GitHubPublisher

@pytest.fixture
def mock_publisher():
    with patch.object(publisher, 'post_reply', new_callable=AsyncMock) as mock_post:
        yield mock_post

@pytest.fixture
def mock_deepseek():
    # Patch the method on the LoaKrutrimClient class or just mock the engine method
    with patch('services.shared.llm_clients.httpx.Client.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "This is a security risk because X."}}],
            "usage": {}
        }
        yield mock_post

@pytest.fixture
def mock_settings():
    with patch('services.shared.llm_utils.get_settings') as mock_conf:
        # Create a mock settings object with necessary nested structure
        mock_conf.return_value.ai_models.providers = {
            "ola_krutrim": {"api_key": "test-key", "endpoint": "http://test"}
        }
        yield mock_conf

@pytest.mark.asyncio
async def test_handle_conversation(mock_deepseek, mock_settings):
    # engine uses deepseek-r1 which maps to ola_krutrim provider
    engine = PRAnalysisEngine(deepseek_model="deepseek-r1")
    
    # Mock get_review to return a fake review
    with patch.object(engine, 'get_review', new_callable=AsyncMock) as mock_get_review:
        mock_get_review.return_value = AsyncMock(findings=[], pr_number=123, repository="test/repo")
        
        answer = await engine.handle_conversation("test_pr", "Why is this bad?")
        
        assert "This is a security risk" in answer

@pytest.mark.asyncio
async def test_publisher_post_reply():
    # Force enable publisher instance
    with patch.object(publisher, '_enabled', True):
        with patch.object(GitHubPublisher, '_post', new_callable=AsyncMock) as mock_internal_post:
            await publisher.post_reply("owner", "repo", 1, 101, "Test reply")
            
            mock_internal_post.assert_called_once()
            args, kwargs = mock_internal_post.call_args
            assert args[0].endswith("/comments/101/replies")
            assert kwargs['json']['body'] == "Test reply"
