import pytest
from uuid import UUID


@pytest.mark.asyncio
async def test_scenario_1_simple_math_question(client):
    """
    Сценарий 1: Линейный — простой вопрос
    1. Пользователь: «Сколько будет 2 + 2?»
    2. Ожидание: ответ модели содержит «4» (или эквивалент)
    3. Проверка: сообщения сохранены в БД, история доступна по session_id
    """
    
    request_data = {
        "message": "Сколько будет 2 + 2?"
    }
    
    response = await client.post("/chat", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "session_id" in data
    assert "user_message" in data
    assert "assistant_message" in data
    
    session_id = data["session_id"]
    user_message = data["user_message"]
    assistant_message = data["assistant_message"]
    
    assert user_message["content"] == "Сколько будет 2 + 2?"
    assert user_message["role"] == "user"
    assert UUID(user_message["id"])
    
    assert "4" in assistant_message["content"]
    assert assistant_message["role"] == "assistant"
    assert UUID(assistant_message["id"])
    
    assert user_message["session_id"] == session_id
    assert assistant_message["session_id"] == session_id
    
    history_response = await client.get(f"/chat/{session_id}")
    
    assert history_response.status_code == 200
    history_data = history_response.json()
    
    assert history_data["session_id"] == session_id
    assert len(history_data["messages"]) == 2
    
    messages = history_data["messages"]
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[0]["content"] == "Сколько будет 2 + 2?"
    assert "4" in messages[1]["content"]