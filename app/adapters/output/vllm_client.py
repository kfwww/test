import httpx
from typing import Optional
from app.core.ports.output.llm_client import LLMClient
from app.core.ports.dto import MessageDTO
from infrastructure.config.settings import settings


class VLLMClient(LLMClient):
    """Адаптер для работы с vLLM с пулом соединений"""
    
    def __init__(self, base_url: str | None = None, model_name: str | None = None):
        self.base_url = base_url or settings.VLLM_URL
        self.model_name = model_name or settings.VLLM_MODEL
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Ленивое создание клиента с пулом"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=30,
                    keepalive_expiry=30.0
                ),
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=300.0,
                    write=10.0,
                    pool=5.0
                )
            )
        return self._client
    
    async def generate_response(
        self, 
        prompt: str, 
        history: list[MessageDTO] | None = None
    ) -> str:
        """Генерировать ответ от LLM"""
        try:
            messages = []

            if history:
                recent_history = history[-10:]
                messages.extend([msg.to_dict_for_llm() for msg in recent_history])
            
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2500,
                "stream": False
            }
            
            client = await self._get_client()
            
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise Exception(
                    f"vLLM returned {response.status_code}: {response.text[:500]}"
                )

            data = response.json()

            if "choices" not in data or len(data["choices"]) == 0:
                raise Exception(f"No choices in response: {data}")
            
            return data["choices"][0]["message"]["content"]
        
        except httpx.TimeoutException:
            raise Exception("LLM request timed out after 300s")
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get response from LLM: {str(e)}")
    
    async def is_available(self) -> bool:
        """Проверить доступность vLLM"""
        try:
            health_url = f"http://{settings.VLLM_HOST}:{settings.VLLM_PORT}/health"
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as tmp_client:
                response = await tmp_client.get(health_url)
                return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Закрыть HTTP клиент"""
        if self._client:
            await self._client.aclose()
            self._client = None